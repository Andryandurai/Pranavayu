/* VayuSim: retained API fields only. Particles are display cues, not trajectories. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const cities = JSON.parse($("vayu-cities").textContent);
  const initial = JSON.parse($("vayu-initial").textContent);
  const cache = new Map();
  const palette = [
    "#00b050",
    "#92d050",
    "#ffff00",
    "#ff9900",
    "#ff0000",
    "#c00000",
  ];
  const boundaries = [30, 60, 90, 120, 250];
  const color = (value) =>
    palette[
      boundaries.findIndex((b) => value <= b) < 0
        ? 5
        : boundaries.findIndex((b) => value <= b)
    ];
  const format = (value, digits = 2) =>
    value == null
      ? "Unavailable"
      : Number(value).toLocaleString("en-IN", {
          maximumFractionDigits: digits,
        });
  const statusText = (run) =>
    run.validation_status === "unvalidated_branch"
      ? "unvalidated branch"
      : "formula check only";
  const say = (text) => {
    $("status").textContent = text;
  };
  const csrf = () => document.querySelector("[name=csrfmiddlewaretoken]").value;
  async function api(url, body) {
    const response = await fetch(
      url,
      body === undefined
        ? {}
        : {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": csrf(),
            },
            body: JSON.stringify(body),
          },
    );
    const data = await response.json();
    if (!response.ok)
      throw new Error(
        typeof data.detail === "string" ? data.detail : JSON.stringify(data),
      );
    return data;
  }
  let map = null,
    marker = null,
    presets = [],
    sourceRun = initial,
    visibleRun = initial;
  let savedInputs = initial?.inputs || null,
    baseline = null,
    day = [],
    currentField = null;
  let motion = !matchMedia("(prefers-reduced-motion: reduce)").matches,
    playTimer = null;
  let renderSerial = 0,
    lastDraw = 0,
    frameTimes = [],
    lastStations = 0;
  const particleCanvas = $("plume-canvas"),
    context = particleCanvas.getContext("2d");
  let readyResolve;
  const mapReady = new Promise((resolve) => {
    readyResolve = resolve;
  });
  const city = () =>
    cities.find((c) => c.slug === $("city").value) || cities[0];
  function place(point) {
    $("lon").value = point[0];
    $("lat").value = point[1];
    marker?.setLngLat(point);
  }
  function fallback() {
    map = null;
    $("fallback-map").hidden = false;
    $("vayu-map").hidden = true;
    particleCanvas.hidden = true;
    $("motion-toggle").hidden = true;
    readyResolve();
  }
  try {
    if (!window.maplibregl?.Map) throw new Error("Map library unavailable");
    map = new maplibregl.Map({
      container: "vayu-map",
      center: initial?.inputs.centre || cities[0]?.location,
      zoom: 11,
      attributionControl: true,
      preserveDrawingBuffer: false,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            maxzoom: 19,
            attribution:
              '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
          },
        },
        layers: [
          {
            id: "basemap",
            type: "raster",
            source: "osm",
            paint: {
              "raster-saturation": -0.85,
              "raster-brightness-max": 0.52,
            },
          },
        ],
      },
    });
    map.addControl(
      new maplibregl.NavigationControl({ showCompass: true }),
      "top-right",
    );
    const element = document.createElement("div");
    element.className = "vayu-marker";
    marker = new maplibregl.Marker({ element, draggable: true })
      .setLngLat(initial?.inputs.sources[0].location || cities[0].location)
      .addTo(map);
    marker.on("dragend", () => {
      const p = marker.getLngLat();
      place([p.lng, p.lat]);
      say("Source moved. Run scenario to compute the new field.");
    });
    map.on("click", (event) => {
      place([event.lngLat.lng, event.lngLat.lat]);
      say("Source placed. Run scenario to compute the new field.");
    });
    map.once("load", readyResolve);
    map.getCanvas().addEventListener("webglcontextlost", (e) => {
      e.preventDefault();
      fallback();
      if (visibleRun) $("fallback-image").src = visibleRun.overlay_url;
    });
    $("vayu-map").addEventListener(
      "keydown",
      (event) => {
        if (!map) return;
        if (
          ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(
            event.key,
          )
        ) {
          event.preventDefault();
          event.stopPropagation();
          map.panBy(
            [
              event.key === "ArrowRight"
                ? 20
                : event.key === "ArrowLeft"
                  ? -20
                  : 0,
              event.key === "ArrowDown"
                ? 20
                : event.key === "ArrowUp"
                  ? -20
                  : 0,
            ],
            { duration: 0 },
          );
        } else if (event.key === "Enter") {
          event.preventDefault();
          const p = map.getCenter();
          place([p.lng, p.lat]);
          say("Source placed at keyboard crosshair. Run scenario to compute.");
        }
      },
      true,
    );
  } catch (error) {
    console.warn("VayuSim static fallback:", error.message);
    fallback();
  }
  function row(parent, name, value) {
    const div = document.createElement("div");
    div.className = "stat-row";
    const label = document.createElement("span"),
      strong = document.createElement("strong");
    label.textContent = name;
    strong.textContent = value;
    div.append(label, strong);
    parent.append(div);
  }
  function family() {
    const preset = presets.find((p) => p.id === $("preset").value);
    if (!preset) return;
    $("preset-citation").replaceChildren(
      document.createTextNode(preset.note + " "),
    );
    for (const citation of preset.citations) {
      const link = document.createElement("a");
      link.href = citation.url;
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent =
        citation.section + (citation.pages ? " · " + citation.pages : "");
      $("preset-citation").append(link);
    }
    $("extended-fields").hidden = preset.type === "point";
    for (const [id, needed] of Object.entries({
      width: preset.type === "area",
      length: preset.type === "area",
      "end-lon": preset.type === "line",
      "end-lat": preset.type === "line",
      subdivisions: preset.type !== "point",
    })) {
      $(id).disabled = !needed;
      $(id).required = needed;
      $(id).parentElement.hidden = !needed;
    }
  }
  function weatherFields() {
    const manual = $("weather-mode").value === "manual";
    $("manual-fields").hidden = !manual;
    for (const input of $("manual-fields").querySelectorAll("input")) {
      input.disabled = !manual;
      input.required = manual && input.id !== "lid";
    }
  }
  function hydrate(inputs) {
    savedInputs = structuredClone(inputs);
    $("city").value = inputs.city;
    const source = inputs.sources[0];
    place(source.location);
    const matching = presets.find((p) => p.id === "stored-" + source.type);
    if (matching) $("preset").value = matching.id;
    for (const [id, key] of Object.entries({
      q: "emission_gs",
      height: "height_m",
      diameter: "diameter_m",
      velocity: "exit_velocity_ms",
      temperature: "exit_temperature_k",
      width: "width_m",
      length: "length_m",
      subdivisions: "subdivisions",
    }))
      $(id).value = source[key] ?? "";
    if (source.end_location) {
      $("end-lon").value = source.end_location[0];
      $("end-lat").value = source.end_location[1];
    }
    const moment = new Date(new Date(inputs.datetime).getTime() + 330 * 60000);
    $("date-hour").value = moment.toISOString().slice(0, 16);
    $("weather-mode").value = inputs.weather_mode;
    if (inputs.weather) {
      for (const [id, key] of Object.entries({
        wind: "wind_speed_ms",
        direction: "wind_direction_deg",
        ambient: "temperature_k",
        solar: "solar_radiation_wm2",
        cloud: "cloud_fraction",
        lid: "mixing_height_m",
      }))
        $(id).value = inputs.weather[key] ?? "";
      $("daytime").value = inputs.weather.daytime ? "day" : "night";
    }
    $("thresholds").value = (inputs.thresholds || []).join(", ");
    family();
    weatherFields();
  }
  function payload() {
    const num = (id) => Number($(id).value);
    const preset = presets.find((p) => p.id === $("preset").value);
    const source = {
      type: preset.type,
      location: [num("lon"), num("lat")],
      emission_gs: num("q"),
      height_m: num("height"),
      diameter_m: num("diameter"),
      exit_velocity_ms: num("velocity"),
      exit_temperature_k: num("temperature"),
      assumptions: "User-specified scenario; not measured emissions",
    };
    if (source.type !== "point") source.subdivisions = num("subdivisions");
    if (source.type === "area") {
      source.width_m = num("width");
      source.length_m = num("length");
    }
    if (source.type === "line")
      source.end_location = [num("end-lon"), num("end-lat")];
    const body = {
      ...(savedInputs?.city === city().slug ? savedInputs : {}),
      name: "VayuSim source scenario",
      city: city().slug,
      centre:
        savedInputs?.city === city().slug
          ? savedInputs.centre
          : city().location,
      sources: [
        source,
        ...(savedInputs?.city === city().slug
          ? savedInputs.sources.slice(1)
          : []),
      ],
      weather_mode: $("weather-mode").value,
      datetime:
        $("date-hour").value +
        ($("date-hour").value.length === 16 ? ":00" : "") +
        "+05:30",
      thresholds: $("thresholds").value.trim()
        ? $("thresholds")
            .value.split(",")
            .map((v) => {
              if (!v.trim())
                throw new Error("Enter comma-separated finite thresholds");
              return Number(v);
            })
        : [],
    };
    if (body.weather_mode === "real") delete body.weather;
    else {
      body.weather = {
        wind_speed_ms: num("wind"),
        wind_direction_deg: num("direction"),
        temperature_k: num("ambient"),
        solar_radiation_wm2: num("solar"),
        cloud_fraction: num("cloud"),
        daytime: $("daytime").value === "day",
      };
      if ($("lid").value !== "") body.weather.mixing_height_m = num("lid");
    }
    if (body.thresholds.some((v) => !Number.isFinite(v)))
      throw new Error("Thresholds must be finite numbers");
    return body;
  }
  async function grid(run) {
    if (cache.has(run.run_id)) return cache.get(run.run_id);
    const promise = (async () => {
      const header = await api(run.grid_header_url);
      const [response, overlay] = await Promise.all([
        fetch(run.grid_url),
        fetch(run.overlay_url),
      ]);
      if (!response.ok || !overlay.ok)
        throw new Error("Grid or overlay unavailable");
      const buffer = await response.arrayBuffer();
      const count = header.shape[0] * header.shape[1];
      if (
        header.dtype !== "float32" ||
        header.byte_order !== "little" ||
        buffer.byteLength !== count * 4
      )
        throw new Error("Unsupported grid format");
      const view = new DataView(buffer),
        values = new Float32Array(count);
      for (let i = 0; i < count; i++) values[i] = view.getFloat32(i * 4, true);
      const active = [];
      for (let i = 0; i < count; i++) if (values[i] > 1) active.push(i);
      const imageUrl = URL.createObjectURL(await overlay.blob());
      return { header, values, active, imageUrl };
    })();
    cache.set(run.run_id, promise);
    if (cache.size > 52) {
      const oldest = cache.keys().next().value;
      cache
        .get(oldest)
        .then((field) => URL.revokeObjectURL(field.imageUrl))
        .catch(() => {});
      cache.delete(oldest);
    }
    try {
      return await promise;
    } catch (error) {
      cache.delete(run.run_id);
      throw error;
    }
  }
  function summary(run) {
    const s = run.summary,
      input = savedInputs;
    for (const id of [
      "scene-validation",
      "summary-validation",
      "day-validation",
    ])
      $(id).textContent = statusText(run);
    $("scene-title").textContent =
      (cities.find((c) => c.slug === input?.city)?.name ||
        run.city ||
        "Stored scenario") +
      " · Briggs " +
      run.stability_class;
    $("peak").replaceChildren(document.createTextNode(format(s.peak_ugm3)));
    const small = document.createElement("small");
    small.textContent = "µg/m³ peak increment";
    $("peak").append(small);
    $("summary-stats").replaceChildren();
    row(
      $("summary-stats"),
      "Distance to peak",
      format(s.distance_to_peak_m, 0) + " m",
    );
    row(
      $("summary-stats"),
      "Peak lon, lat",
      s.peak_location.map((v) => format(v, 5)).join(", "),
    );
    row(
      $("summary-stats"),
      "Stability / run",
      run.stability_class + " / " + run.run_id,
    );
    row(
      $("summary-stats"),
      "IST hour",
      s.weather_provenance.ist_hour_start || input?.datetime || "Unavailable",
    );
    $("population").replaceChildren();
    if (s.exposure.available) {
      for (const [threshold, value] of Object.entries(
        s.exposure.population_above,
      ))
        row(
          $("population"),
          "> " + format(threshold) + " µg/m³",
          format(value, 0) + " people",
        );
      $("support").textContent =
        "Known population support: " +
        format(100 * s.exposure.population_support_fraction, 1) +
        "% of grid area. Modelled footprint only; unknown cells excluded.";
    } else {
      $("population").textContent = "Unavailable";
      $("support").textContent = s.exposure.reason;
    }
    $("flags").replaceChildren();
    for (const flag of run.flags) {
      const li = document.createElement("li");
      li.textContent = flag;
      $("flags").append(li);
    }
    if (!run.flags.length) $("flags").textContent = "No flags returned.";
    $("source-notes").textContent = run.interpretation.sources
      .map((s) => s.label + ": " + s.assumptions)
      .join(" · ");
    $("all-limits").textContent = run.limitations.join(" · ");
    $("contour-values").textContent =
      "Contours (µg/m³): " + s.thresholds.map((v) => format(v)).join(" · ");
    const resolution = Math.hypot(s.grid.affine[0], s.grid.affine[3]);
    $("grid-detail").textContent =
      format((s.grid.shape[1] * resolution) / 1000) +
      " km field · " +
      format(resolution, 0) +
      " m cells · receptor " +
      format(s.grid.receptor_height_m) +
      " m";
    $("wind-detail").textContent =
      "Wind FROM " +
      format(s.weather.wind_direction_deg, 0) +
      "° · " +
      format(s.weather.wind_speed_ms) +
      " m/s · " +
      s.weather_provenance.mode +
      " weather";
    $("export-link").href = run.export_url;
    $("export-link").removeAttribute("aria-disabled");
    $("share-link").href = "/vayusim/?scenario=" + run.scenario_slug;
    $("grid-link").href = run.grid_header_url;
  }
  async function stations(run) {
    const serial = ++lastStations;
    try {
      const input = savedInputs;
      const data = await api(
        "/api/vayusim/stations/?" +
          new URLSearchParams({
            city: input.city,
            datetime:
              run.summary.weather_provenance.ist_hour_start || input.datetime,
          }),
      );
      if (serial !== lastStations) return;
      $("stations").replaceChildren();
      for (const station of data.stations)
        row(
          $("stations"),
          station.name + " · " + format(station.distance_km, 1) + " km",
          format(station.value_ugm3) + " µg/m³",
        );
      if (!data.stations.length)
        $("stations").textContent =
          "No same-hour nearby quality-OK readings available.";
      if (map?.getSource("stations"))
        map.getSource("stations").setData({
          type: "FeatureCollection",
          features: data.stations.map((s) => ({
            type: "Feature",
            properties: { name: s.name, value: s.value_ugm3 },
            geometry: { type: "Point", coordinates: s.location },
          })),
        });
    } catch (error) {
      $("stations").textContent = "Observations unavailable: " + error.message;
    }
  }
  async function show(run, { focus = false, updateSource = true } = {}) {
    const serial = ++renderSerial;
    ++lastStations;
    visibleRun = run;
    currentField = null;
    context.clearRect(0, 0, particleCanvas.width, particleCanvas.height);
    if (updateSource) {
      sourceRun = run;
      baseline = null;
      setMode("source");
    }
    for (const id of [
      "section-button",
      "view-source",
      "view-baseline",
      "view-difference",
    ])
      $(id).disabled = false;
    summary(run);
    $("section-values").textContent =
      "Load the stored vertical grid for this run.";
    clearSection();
    await mapReady;
    const field = await grid(run);
    if (serial !== renderSerial) return;
    currentField = field;
    if (!map) $("fallback-image").src = field.imageUrl;
    else {
      const coordinates = field.header.corners;
      if (map.getSource("plume"))
        map
          .getSource("plume")
          .updateImage({ url: field.imageUrl, coordinates });
      else {
        map.addSource("plume", {
          type: "image",
          url: field.imageUrl,
          coordinates,
        });
        map.addLayer({
          id: "plume",
          type: "raster",
          source: "plume",
          paint: { "raster-opacity": 0.8, "raster-fade-duration": 0 },
        });
      }
      const contours = field.header.contours || {
        type: "FeatureCollection",
        features: [],
      };
      if (map.getSource("contours"))
        map.getSource("contours").setData(contours);
      else {
        map.addSource("contours", { type: "geojson", data: contours });
        map.addLayer({
          id: "contours",
          type: "line",
          source: "contours",
          paint: {
            "line-color": "#f5eacb",
            "line-width": 1.2,
            "line-opacity": 0.85,
          },
        });
      }
      if (!map.getSource("stations")) {
        map.addSource("stations", {
          type: "geojson",
          data: { type: "FeatureCollection", features: [] },
        });
        map.addLayer({
          id: "stations",
          type: "circle",
          source: "stations",
          paint: {
            "circle-radius": 4,
            "circle-color": "#8cbbf1",
            "circle-stroke-width": 1,
            "circle-stroke-color": "#132535",
          },
        });
      }
      if (focus) {
        const bounds = new maplibregl.LngLatBounds();
        coordinates.forEach((p) => bounds.extend(p));
        map.fitBounds(bounds, { padding: 30, duration: 0 });
      }
      map.setLayoutProperty(
        "contours",
        "visibility",
        $("contour-toggle").checked ? "visible" : "none",
      );
    }
    stations(run);
    draw(performance.now());
    window.vayuState = {
      runId: run.run_id,
      validationStatus: run.validation_status,
      cacheSize: cache.size,
      renderTimes: frameTimes,
    };
  }
  function draw(now) {
    if (!map || !currentField) return;
    const started = performance.now();
    const width = particleCanvas.clientWidth,
      height = particleCanvas.clientHeight;
    if (particleCanvas.width !== width || particleCanvas.height !== height) {
      particleCanvas.width = width;
      particleCanvas.height = height;
    }
    context.clearRect(0, 0, width, height);
    const { header, values } = currentField,
      [rows, cols] = header.shape;
    const corners = header.corners.map((p) => map.project(p));
    const phase = motion ? Math.sin(now / 1400) * 0.22 : 0;
    let drawn = 0;
    const active =
      currentField.active ||
      Array.from(values.keys()).filter((i) => values[i] > 1);
    const stride = Math.max(1, Math.ceil(active.length / 1500));
    for (let sample = 0; sample < active.length; sample += stride) {
      const i = active[sample];
      const x = ((i % cols) + 0.5 + phase) / cols,
        y = (Math.floor(i / cols) + 0.5) / rows;
      const px =
        (1 - y) * ((1 - x) * corners[0].x + x * corners[1].x) +
        y * ((1 - x) * corners[3].x + x * corners[2].x);
      const py =
        (1 - y) * ((1 - x) * corners[0].y + x * corners[1].y) +
        y * ((1 - x) * corners[3].y + x * corners[2].y);
      context.fillStyle = color(values[i]);
      context.globalAlpha = 0.8;
      context.beginPath();
      context.arc(px, py, 1.8, 0, 2 * Math.PI);
      context.fill();
      drawn++;
    }
    context.globalAlpha = 1;
    const duration = performance.now() - started;
    frameTimes.push(duration);
    if (frameTimes.length > 300) frameTimes.shift();
    if (window.vayuState) {
      window.vayuState.drawnParticles = drawn;
      window.vayuState.renderTimes = frameTimes;
    }
  }
  function animate(now) {
    if (motion && now - lastDraw >= 100) {
      draw(now);
      lastDraw = now;
    }
    requestAnimationFrame(animate);
  }
  requestAnimationFrame(animate);
  if (map) map.on("move", () => draw(performance.now()));
  function setMode(mode) {
    if (mode === "source" && sourceRun)
      $("comparison-note").textContent = sourceRun.summary.label;
    for (const id of ["source", "baseline", "difference"]) {
      $("view-" + id).classList.toggle("active", id === mode);
      $("view-" + id).setAttribute("aria-pressed", String(id === mode));
    }
  }
  async function compare(mode) {
    if (!sourceRun || !savedInputs) return;
    try {
      if (mode === "source") {
        await show(sourceRun, { updateSource: false });
        setMode(mode);
        return;
      }
      if (!baseline) {
        say("Storing the source-removed run…");
        const input = structuredClone(savedInputs);
        input.datetime =
          sourceRun.summary.weather_provenance.ist_hour_start || input.datetime;
        input.sources = input.sources.map((s) => ({ ...s, emission_gs: 0 }));
        baseline = await api("/api/vayusim/run/", input);
        const weather = sourceRun.summary.weather;
        if (
          Object.keys(baseline.summary.weather).length !==
            Object.keys(weather).length ||
          Object.entries(weather).some(
            ([key, value]) => baseline.summary.weather[key] !== value,
          )
        ) {
          baseline = null;
          throw new Error(
            "Weather snapshot changed; source comparison unavailable",
          );
        }
      }
      const [before, after] = await Promise.all([
        grid(sourceRun),
        grid(baseline),
      ]);
      if (
        after.values.some((v) => v !== 0) ||
        before.values.length !== after.values.length
      )
        throw new Error("Source-removed grid is not a matching zero field");
      await show(mode === "baseline" ? baseline : sourceRun, {
        updateSource: false,
      });
      if (mode === "difference")
        currentField = {
          header: before.header,
          values: Float32Array.from(
            before.values,
            (v, i) => v - after.values[i],
          ),
        };
      setMode(mode);
      $("comparison-note").textContent =
        "modelled increment from these sources only · stored runs " +
        sourceRun.run_id +
        " and " +
        baseline.run_id +
        (mode === "difference" ? " · source minus source-removed grid" : "");
      say(
        "Comparison uses two stored fields. Nearby measured totals remain separate.",
      );
    } catch (error) {
      say(error.message);
    }
  }
  async function selectHour(index) {
    const run = day[index];
    $("timeline").value = index;
    $("timeline-label").textContent =
      run.datetime +
      (run.available
        ? " · " + statusText(run)
        : " · unavailable: " + run.reason);
    if (!run.available) {
      renderSerial++;
      currentField = null;
      context.clearRect(0, 0, particleCanvas.width, particleCanvas.height);
      if (map?.getLayer("plume"))
        map.setLayoutProperty("plume", "visibility", "none");
      if (map?.getLayer("contours"))
        map.setLayoutProperty("contours", "visibility", "none");
      $("fallback-image").removeAttribute("src");
      visibleRun = null;
      ++lastStations;
      sourceRun = null;
      baseline = null;
      for (const id of [
        "scene-validation",
        "summary-validation",
        "day-validation",
      ])
        $(id).textContent = "Unavailable hour";
      $("peak").textContent = "Unavailable";
      for (const id of [
        "summary-stats",
        "population",
        "flags",
        "stations",
        "source-notes",
      ])
        $(id).replaceChildren();
      $("support").textContent = "No field or exposure estimate for this hour.";
      $("scene-title").textContent = run.datetime + " · unavailable";
      $("wind-detail").textContent = "No weather field shown for this hour";
      $("grid-detail").textContent = "No grid available";
      window.vayuState = {
        runId: null,
        validationStatus: null,
        cacheSize: cache.size,
        renderTimes: frameTimes,
      };
      for (const id of ["export-link", "share-link", "grid-link"]) {
        $(id).href = "#";
        $(id).setAttribute("aria-disabled", "true");
      }
      for (const id of [
        "section-button",
        "view-source",
        "view-baseline",
        "view-difference",
      ])
        $(id).disabled = true;
      if (map?.getSource("stations"))
        map
          .getSource("stations")
          .setData({ type: "FeatureCollection", features: [] });
      clearSection();
      say("No field for this hour. No zero has been substituted.");
      return;
    }
    if (map?.getLayer("plume"))
      map.setLayoutProperty("plume", "visibility", "visible");
    await show(run);
    say("Stored hourly frame loaded · " + statusText(run));
  }
  function stopPlay() {
    clearInterval(playTimer);
    playTimer = null;
    $("play-button").textContent = "Play";
    $("play-button").setAttribute("aria-pressed", "false");
  }
  async function loadDay() {
    if (!savedInputs || savedInputs.weather_mode !== "real") {
      say("Day mode requires archived hourly weather.");
      return;
    }
    stopPlay();
    $("day-button").disabled = true;
    try {
      say("Computing or reopening the 24 stored hourly runs…");
      const input = structuredClone(savedInputs);
      input.datetime =
        $("date-hour").value +
        ($("date-hour").value.length === 16 ? ":00" : "") +
        "+05:30";
      const result = await api("/api/vayusim/day/", input);
      day = result.hours;
      $("timeline").disabled = false;
      let next = 0,
        complete = 0;
      // At most two artifact requests in flight; OSM tiles are never prefetched.
      const worker = async () => {
        while (next < day.length) {
          const item = day[next++];
          if (item.available) {
            await grid(item);
            complete++;
            say(
              "Prefetching stored fields: " +
                complete +
                " available hours cached.",
            );
          }
        }
      };
      await Promise.all([worker(), worker()]);
      $("play-button").disabled = false;
      await selectHour(
        Math.max(
          0,
          day.findIndex((h) => h.available),
        ),
      );
      say(
        "Day ready · " +
          complete +
          " available hourly fields cached. Missing hours stay missing.",
      );
      window.vayuDay = { available: complete, cacheSize: cache.size };
    } catch (error) {
      say("Day unavailable: " + error.message);
    } finally {
      $("day-button").disabled = false;
    }
  }
  function clearSection() {
    const c = $("section-canvas"),
      ctx = c.getContext("2d");
    ctx.clearRect(0, 0, c.width, c.height);
  }
  async function section() {
    if (!visibleRun) return;
    const run = visibleRun;
    $("section-button").disabled = true;
    try {
      say("Opening or storing the supplementary vertical grid…");
      let response = await fetch(run.section_url);
      let data;
      if (response.status === 404) data = await api(run.section_url, {});
      else {
        if (!response.ok) throw new Error("Vertical grid unavailable");
        data = await response.json();
      }
      if (visibleRun.run_id !== run.run_id) return;
      const canvas = $("section-canvas"),
        ctx = canvas.getContext("2d");
      canvas.width = canvas.clientWidth;
      canvas.height = 210;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const left = 42,
        top = 12,
        width = canvas.width - 54,
        height = 162;
      const rows = data.height_m.length,
        cols = data.distance_m.length;
      for (let r = 0; r < rows; r++)
        for (let c = 0; c < cols; c++) {
          const value = data.values_ugm3[r][c];
          if (value <= 1) continue;
          ctx.fillStyle = color(value);
          ctx.fillRect(
            left + (c * width) / cols,
            top + ((rows - 1 - r) * height) / rows,
            Math.ceil(width / cols),
            Math.ceil(height / rows),
          );
        }
      ctx.fillStyle =
        $("vayu").dataset.theme === "light" ? "#163d32" : "#c1d3ca";
      ctx.font = "10px Segoe UI";
      ctx.fillText(format(data.height_m.at(-1), 0) + " m", 0, 16);
      ctx.fillText("0 m", 5, top + height);
      ctx.fillText("0 m", left, 198);
      ctx.fillText(
        format(data.distance_m.at(-1), 0) + " m downwind",
        Math.max(left, canvas.width - 130),
        198,
      );
      $("section-values").textContent =
        statusText(data) +
        " · " +
        data.label +
        " · origin " +
        data.origin.map((v) => format(v, 5)).join(", ") +
        " · " +
        data.height_m.length +
        " heights × " +
        data.distance_m.length +
        " distances. All retained sources contribute; transect starts at first source.";
      say("Vertical cross-section read from the stored artifact.");
    } catch (error) {
      say(error.message);
    } finally {
      $("section-button").disabled = false;
    }
  }
  $("preset").addEventListener("change", family);
  $("weather-mode").addEventListener("change", weatherFields);
  $("city").addEventListener("change", () => {
    place(city().location);
    map?.flyTo({ center: city().location, zoom: 11, duration: 0 });
    say("City selected. Set assumptions and run to update the field.");
  });
  $("vayu-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    stopPlay();
    $("run-button").disabled = true;
    try {
      const body = payload();
      say("Computing dispersion and population footprint…");
      const run = await api("/api/vayusim/run/", body);
      savedInputs = body;
      await show(run, { focus: true });
      say(
        (run.cached ? "Identical stored run reopened" : "New run stored") +
          " · " +
          statusText(run),
      );
    } catch (error) {
      say("Scenario unavailable: " + error.message);
    } finally {
      $("run-button").disabled = false;
    }
  });
  for (const mode of ["source", "baseline", "difference"])
    $("view-" + mode).addEventListener("click", () => compare(mode));
  $("day-button").addEventListener("click", loadDay);
  $("timeline").addEventListener("input", () => {
    stopPlay();
    selectHour(Number($("timeline").value)).catch((e) => say(e.message));
  });
  $("play-button").addEventListener("click", () => {
    if (playTimer) {
      stopPlay();
      return;
    }
    $("play-button").textContent = "Pause";
    $("play-button").setAttribute("aria-pressed", "true");
    let busy = false;
    playTimer = setInterval(async () => {
      if (busy) return;
      busy = true;
      try {
        await selectHour((Number($("timeline").value) + 1) % day.length);
      } catch (e) {
        say(e.message);
        stopPlay();
      } finally {
        busy = false;
      }
    }, 1000);
  });
  $("section-button").addEventListener("click", section);
  $("contour-toggle").addEventListener("change", () => {
    if (map?.getLayer("contours"))
      map.setLayoutProperty(
        "contours",
        "visibility",
        $("contour-toggle").checked ? "visible" : "none",
      );
  });
  $("motion-toggle").textContent = motion
    ? "Pause particles"
    : "Show particles";
  $("motion-toggle").setAttribute("aria-pressed", String(motion));
  $("motion-toggle").addEventListener("click", () => {
    motion = !motion;
    $("motion-toggle").textContent = motion
      ? "Pause particles"
      : "Show particles";
    $("motion-toggle").setAttribute("aria-pressed", String(motion));
    draw(performance.now());
  });
  $("theme-toggle").addEventListener("click", () => {
    const light = $("vayu").dataset.theme !== "light";
    $("vayu").dataset.theme = light ? "light" : "dark";
    $("theme-toggle").textContent = light ? "Dark mode" : "Light mode";
    $("theme-toggle").setAttribute("aria-pressed", String(light));
    if (map?.isStyleLoaded())
      map.setPaintProperty(
        "basemap",
        "raster-brightness-max",
        light ? 1 : 0.52,
      );
  });
  (async () => {
    try {
      const data = await api("/api/vayusim/presets/");
      presets = [
        ...["point", "area", "line"].map((type) => ({
          id: "stored-" + type,
          name: "Custom / stored " + type + " source",
          type,
          citations: [],
          note: "Explicit source assumptions. No facility family or source-backed default is inferred. Select a cited family below for its scope.",
        })),
        ...data.presets,
      ];
      for (const preset of presets) {
        const o = document.createElement("option");
        o.value = preset.id;
        o.textContent = preset.name;
        $("preset").append(o);
      }
      if (initial) {
        hydrate(initial.inputs);
        await show(initial, { focus: true });
        say("Stored run " + initial.run_id + " · " + statusText(initial));
      } else {
        place(city().location);
        family();
        weatherFields();
        say("Enter explicit source parameters and choose an hour.");
      }
    } catch (error) {
      say("Could not load stored scenario: " + error.message);
    }
  })();
})();

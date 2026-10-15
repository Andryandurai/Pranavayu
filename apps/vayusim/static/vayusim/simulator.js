/* Real server-computed increments. User assumptions never become observations. */
(() => {
  const $ = (id) => document.getElementById(id);
  const cities = JSON.parse($("sim-cities").textContent);
  let presets = [],
    lastRun = null,
    sharedInputs = null;
  const selectedCity = () => cities.find((c) => c.slug === $("sim-city").value);
  const initial = selectedCity().location;
  const map = new maplibregl.Map({
    container: "sim-map",
    center: initial,
    zoom: 10,
    style: {
      version: 8,
      sources: {
        osm: {
          type: "raster",
          tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
          tileSize: 256,
          attribution:
            '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
          maxzoom: 19,
        },
      },
      layers: [{ id: "osm", type: "raster", source: "osm" }],
    },
  });
  map.addControl(new maplibregl.NavigationControl());
  const mapReady = new Promise((resolve) => map.once("load", resolve));
  const marker = new maplibregl.Marker({ color: "#0b6557", draggable: true })
    .setLngLat(initial)
    .addTo(map);
  function place(point) {
    marker.setLngLat(point);
    $("sim-lon").value = point[0].toFixed(6);
    $("sim-lat").value = point[1].toFixed(6);
  }
  place(initial);
  map.on("click", (e) => place([e.lngLat.lng, e.lngLat.lat]));
  marker.on("dragend", () => {
    const p = marker.getLngLat();
    place([p.lng, p.lat]);
  });
  $("sim-city").addEventListener("change", () => {
    const p = selectedCity().location;
    place(p);
    map.flyTo({ center: p, zoom: 10, essential: false });
  });
  function family() {
    const preset = presets.find((p) => p.id === $("sim-preset").value);
    const extended = preset?.type !== "point";
    $("extended-source").hidden = !extended;
    for (const id of [
      "sim-width",
      "sim-length",
      "sim-end-lon",
      "sim-end-lat",
      "sim-subdivisions",
    ]) {
      const needed =
        extended &&
        (id === "sim-subdivisions" ||
          (preset.type === "area"
            ? ["sim-width", "sim-length"].includes(id)
            : ["sim-end-lon", "sim-end-lat"].includes(id)));
      $(id).disabled = !needed;
      $(id).required = needed;
      $(id).parentElement.hidden = !needed;
    }
    $("preset-note").replaceChildren(
      document.createTextNode(preset?.note || ""),
    );
    if (preset?.citations[0]) {
      const a = document.createElement("a");
      a.href = preset.citations[0].url;
      a.textContent = " Source: " + preset.citations[0].section;
      a.target = "_blank";
      a.rel = "noopener";
      $("preset-note").append(a);
    }
  }
  const presetsReady = fetch("/api/vayusim/presets/")
    .then((r) => r.json())
    .then((data) => {
      presets = data.presets;
      for (const p of presets) {
        const o = document.createElement("option");
        o.value = p.id;
        o.textContent = p.name;
        $("sim-preset").append(o);
      }
      family();
    })
    .catch(() => {
      $("sim-status").textContent = "Unable to load presets. Refresh to retry.";
    });
  $("sim-preset").addEventListener("change", family);
  $("sim-mode").addEventListener("change", () => {
    const manual = $("sim-mode").value === "manual";
    $("manual-weather").hidden = !manual;
    for (const i of $("manual-weather").querySelectorAll("input")) {
      i.disabled = !manual;
      i.required = manual && i.id !== "sim-lid";
    }
  });
  for (const i of $("manual-weather").querySelectorAll("input"))
    i.disabled = true;
  const numeric = (id) => Number($(id).value);
  const number = (value, digits = 2) =>
    value === null || value === undefined
      ? "Unavailable"
      : Number(value).toLocaleString("en-IN", {
          maximumFractionDigits: digits,
        });
  function paragraph(text, parent, tag = "p") {
    const e = document.createElement(tag);
    e.textContent = text;
    parent.append(e);
    return e;
  }
  function render(data) {
    lastRun = data;
    const summary = data.summary;
    place(summary.source_assumptions[0].location);
    const cell = Math.hypot(summary.grid.affine[0], summary.grid.affine[3]);
    document.querySelector(".map-caption").textContent =
      "Click to place a source · " +
      number((summary.grid.shape[1] * cell) / 1000) +
      " km × " +
      number((summary.grid.shape[0] * cell) / 1000) +
      " km · " +
      number(cell, 0) +
      " m grid";
    $("sim-summary").replaceChildren();
    paragraph("Modelled source increment", $("sim-summary"), "h2");
    const stats = document.createElement("div");
    stats.className = "metric-grid";
    $("sim-summary").append(stats);
    for (const [label, value] of [
      ["Peak added PM2.5", number(summary.peak_ugm3) + " µg/m³"],
      ["Distance to peak", number(summary.distance_to_peak_m, 0) + " m"],
      ["Stability class", data.stability_class],
      [
        "Population above 1 µg/m³",
        summary.exposure.available
          ? number(summary.exposure.population_above["1.0"], 0)
          : "Unavailable",
      ],
    ]) {
      const div = document.createElement("div");
      div.className = "metric";
      paragraph(label, div, "span");
      paragraph(value, div, "strong");
      stats.append(div);
    }
    paragraph(summary.exposure.label, $("sim-summary"));
    paragraph(
      "Population-weighted added concentration: " +
        number(summary.exposure.population_weighted_mean_added_ugm3) +
        " µg/m³",
      $("sim-summary"),
    );
    paragraph(
      "Area above 1 µg/m³: " + number(summary.area_above_km2["1.0"]) + " km²",
      $("sim-summary"),
    );
    if (summary.exposure.available)
      paragraph(
        "Population raster support: " +
          number(100 * summary.exposure.population_support_fraction, 1) +
          "% of grid area. Unknown population area excluded.",
        $("sim-summary"),
      );
    for (const flag of data.flags)
      paragraph(flag, $("sim-summary"), "p").className = "help";
    paragraph(
      "Measured total (all sources) · same hour",
      $("sim-summary"),
      "h3",
    );
    const stations = summary.background.stations;
    if (!stations.length)
      paragraph(
        "No nearby quality-OK CPCB readings for this hour.",
        $("sim-summary"),
      );
    for (const s of stations.slice(0, 8))
      paragraph(
        s.name +
          ": " +
          number(s.value_ugm3) +
          " µg/m³ · " +
          number(s.distance_km, 1) +
          " km",
        $("sim-summary"),
      );
    const links = document.createElement("div");
    links.className = "inline-links";
    $("sim-summary").append(links);
    for (const [label, url] of [
      ["Share this scenario", "/simulator/?scenario=" + data.scenario_slug],
      ["Download grid", data.grid_url],
      ["Grid metadata", data.grid_header_url],
    ]) {
      const a = document.createElement("a");
      a.href = url;
      a.textContent = label;
      links.append(a);
    }
    const explain = document.createElement("button");
    explain.type = "button";
    explain.textContent = "Explain this result";
    explain.className = "button secondary";
    $("sim-summary").append(explain);
    explain.onclick = async () => {
      explain.disabled = true;
      const output = paragraph(
        "Finding cited evidence; local model answers can take several minutes.",
        $("sim-summary"),
      );
      try {
        const r = await fetch("/api/rag/explain/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]")
              .value,
          },
          body: JSON.stringify({
            context_type: "scenario",
            payload: {
              run_id: lastRun.run_id,
              question:
                "Explain the stored VayuSim peak, exposure and AERMOD assumptions and limitations.",
            },
          }),
        });
        const result = await r.json();
        if (!r.ok) throw new Error(JSON.stringify(result));
        output.textContent = result.answer;
        output.style.whiteSpace = "pre-wrap";
        for (const c of result.citations || []) {
          const a = document.createElement("a");
          a.href = c.url;
          a.textContent = c.label;
          links.append(a);
        }
      } catch (error) {
        output.textContent = error.message;
      } finally {
        explain.disabled = false;
      }
    };
    for (const layer of ["plume-contours", "plume-overlay"])
      if (map.getLayer(layer)) map.removeLayer(layer);
    for (const source of ["plume-contours", "plume-overlay"])
      if (map.getSource(source)) map.removeSource(source);
    map.addSource("plume-overlay", {
      type: "image",
      url: data.overlay_url,
      coordinates: summary.grid.corners,
    });
    map.addLayer({
      id: "plume-overlay",
      type: "raster",
      source: "plume-overlay",
      paint: { "raster-opacity": 0.7, "raster-fade-duration": 0 },
    });
    map.addSource("plume-contours", {
      type: "geojson",
      data: data.contours || { type: "FeatureCollection", features: [] },
    });
    map.addLayer({
      id: "plume-contours",
      type: "line",
      source: "plume-contours",
      paint: { "line-color": "#6d2343", "line-width": 1.5 },
    });
  }
  $("simulation-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    $("sim-submit").disabled = true;
    $("sim-status").textContent =
      "Computing dispersion and population exposure…";
    try {
      const preset = presets.find((p) => p.id === $("sim-preset").value);
      const source = {
        type: preset.type,
        location: [numeric("sim-lon"), numeric("sim-lat")],
        emission_gs: numeric("sim-q"),
        height_m: numeric("sim-height"),
        diameter_m: numeric("sim-diameter"),
        exit_velocity_ms: numeric("sim-velocity"),
        exit_temperature_k: numeric("sim-temperature"),
      };
      if (preset.type !== "point")
        source.subdivisions = numeric("sim-subdivisions");
      if (preset.type === "area") {
        source.width_m = numeric("sim-width");
        source.length_m = numeric("sim-length");
      }
      if (preset.type === "line")
        source.end_location = [numeric("sim-end-lon"), numeric("sim-end-lat")];
      const hour = $("sim-hour").value;
      const sameCity = sharedInputs?.city === $("sim-city").value;
      const body = {
        ...(sameCity ? sharedInputs : {}),
        city: $("sim-city").value,
        centre: sameCity ? sharedInputs.centre : selectedCity().location,
        sources: [source],
        weather_mode: $("sim-mode").value,
        datetime: hour + (hour.length === 16 ? ":00" : "") + "+05:30",
        thresholds:
          $("sim-threshold").value === "" ? [] : [numeric("sim-threshold")],
      };
      if (body.weather_mode === "real") delete body.weather;
      if (body.weather_mode === "manual") {
        body.weather = {
          wind_speed_ms: numeric("sim-wind"),
          wind_direction_deg: numeric("sim-direction"),
          temperature_k: numeric("sim-ambient"),
          solar_radiation_wm2: numeric("sim-solar"),
          cloud_fraction: numeric("sim-cloud"),
          daytime: $("sim-daytime").value === "day",
        };
        if ($("sim-lid").value !== "")
          body.weather.mixing_height_m = numeric("sim-lid");
      }
      const response = await fetch("/api/vayusim/run/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]")
            .value,
        },
        body: JSON.stringify(body),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(JSON.stringify(data));
      await mapReady;
      render(data);
      $("sim-status").textContent = data.cached
        ? "Loaded the identical stored run."
        : "Scenario complete.";
    } catch (error) {
      $("sim-status").textContent = "Could not run scenario: " + error.message;
    } finally {
      $("sim-submit").disabled = false;
    }
  });
  const slug = new URLSearchParams(location.search).get("scenario");
  if (slug)
    fetch("/api/vayusim/scenarios/" + encodeURIComponent(slug) + "/")
      .then((r) => r.json())
      .then(async (data) => {
        if (!data.runs?.length) throw new Error("Shared scenario unavailable");
        await Promise.all([mapReady, presetsReady]);
        const inputs = data.inputs,
          source = inputs.sources[0];
        sharedInputs = inputs;
        $("sim-city").value = inputs.city;
        const sharedFamily = {
          id: "shared-source",
          type: source.type,
          citations: [],
          note:
            "Saved " +
            source.type +
            " geometry with supplied parameters. No facility family or cited default is inferred.",
        };
        presets.push(sharedFamily);
        const sharedOption = document.createElement("option");
        sharedOption.value = sharedFamily.id;
        sharedOption.textContent = "Shared " + source.type + " source";
        $("sim-preset").append(sharedOption);
        $("sim-preset").value = sharedFamily.id;
        family();
        for (const [id, key] of Object.entries({
          "sim-q": "emission_gs",
          "sim-height": "height_m",
          "sim-diameter": "diameter_m",
          "sim-velocity": "exit_velocity_ms",
          "sim-temperature": "exit_temperature_k",
          "sim-width": "width_m",
          "sim-length": "length_m",
          "sim-subdivisions": "subdivisions",
        }))
          $(id).value = source[key] ?? "";
        if (source.end_location) {
          $("sim-end-lon").value = source.end_location[0];
          $("sim-end-lat").value = source.end_location[1];
        }
        $("sim-mode").value = inputs.weather_mode;
        $("sim-mode").dispatchEvent(new Event("change"));
        $("sim-hour").value = new Date(
          new Date(inputs.datetime).getTime() + 330 * 60000,
        )
          .toISOString()
          .slice(0, 16);
        $("sim-threshold").value = inputs.thresholds?.[0] ?? "";
        if (inputs.weather) {
          for (const [id, key] of Object.entries({
            "sim-wind": "wind_speed_ms",
            "sim-direction": "wind_direction_deg",
            "sim-ambient": "temperature_k",
            "sim-solar": "solar_radiation_wm2",
            "sim-cloud": "cloud_fraction",
            "sim-lid": "mixing_height_m",
          }))
            $(id).value = inputs.weather[key] ?? "";
          $("sim-daytime").value = inputs.weather.daytime ? "day" : "night";
        }
        render(data.runs[data.runs.length - 1]);
        map.flyTo({ center: inputs.centre, zoom: 10 });
        place(source.location);
        $("sim-status").textContent =
          "Loaded shared scenario. Its source assumptions are shown in the form.";
        if (inputs.sources.length > 1) {
          $("sim-submit").disabled = true;
          $("sim-status").textContent =
            "Shared scenario contains " +
            inputs.sources.length +
            " sources. All are included in this result; use the API to edit multiple sources.";
        }
      })
      .catch((error) => {
        $("sim-status").textContent = error.message;
      });
})();

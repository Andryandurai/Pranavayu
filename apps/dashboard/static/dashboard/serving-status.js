/* Explicit read-only serving check; historical dashboard figures stay unchanged. */
(() => {
  const button = document.getElementById("check-serving"),
    status = document.getElementById("serving-status"),
    city = document.getElementById("serving-city");
  if (!button || !status || !city) return;
  button.addEventListener("click", async () => {
    button.disabled = true;
    status.textContent = "Checking the served response…";
    try {
      const response = await fetch("/api/forecast/" + encodeURIComponent(city.value) + "/latest/");
      const body = await response.json();
      if (!response.ok) {
        status.textContent = body.detail || "Unable to check served forecasts.";
        status.dataset.state = "unavailable";
      } else {
        status.textContent = body.forecasts.map(row =>
          "Day +" + row.horizon + " · forecast_method: " + row.forecast_method +
          " · issue " + row.issued_for_date + " · " + row.mode
        ).join("; ");
        status.dataset.state = "available";
      }
    } catch (error) {
      status.textContent = "Unable to check served forecasts: " + error.message;
      status.dataset.state = "unavailable";
    } finally { button.disabled = false; }
  });
})();

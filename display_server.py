import csv
from pathlib import Path

from flask import Flask, jsonify, render_template_string


# Keep the web display portable when the repository is cloned elsewhere.
APP_DIR = Path(__file__).resolve().parent
LOG_FILE = APP_DIR / "logs" / "broadcast_log.csv"

app = Flask(__name__)


PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport"
        content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#101010">
  <title>Talking Plant</title>

  <style>
    :root {
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display",
                   "Segoe UI", Arial, sans-serif;
      color-scheme: dark;
      --bg: #101010;
      --card: #1a1a1a;
      --border: #303030;
      --muted: #9b9b9b;
      --text: #f5f5f5;
    }

    * {
      box-sizing: border-box;
    }

    html,
    body {
      width: 100%;
      height: 100%;
      margin: 0;
      overflow: hidden;
      background: var(--bg);
      color: var(--text);
    }

    body {
      min-height: 100svh;
    }

    .page {
      height: 100svh;
      min-height: 100svh;
      padding:
        max(10px, env(safe-area-inset-top))
        max(12px, env(safe-area-inset-right))
        max(10px, env(safe-area-inset-bottom))
        max(12px, env(safe-area-inset-left));
      display: grid;
      grid-template-rows: auto auto minmax(0, 1fr);
      gap: 9px;
      overflow: hidden;
    }

    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      min-width: 0;
    }

    h1 {
      margin: 0;
      font-size: clamp(28px, 8vw, 38px);
      line-height: 1;
      letter-spacing: -0.04em;
      white-space: nowrap;
    }

    .live {
      display: flex;
      align-items: center;
      flex: 0 0 auto;
      color: #b9b9b9;
      font-size: 14px;
    }

    .dot {
      width: 10px;
      height: 10px;
      margin-right: 7px;
      border-radius: 50%;
      background: #777;
    }

    .dot.online {
      background: #66d17a;
      box-shadow: 0 0 10px rgba(102, 209, 122, 0.35);
    }

    .metrics {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }

    .card {
      min-width: 0;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 15px;
    }

    .metric {
      min-height: 74px;
      padding: 10px 12px;
      display: flex;
      flex-direction: column;
      justify-content: center;
    }

    .metric.spectral {
      grid-column: 1 / -1;
      min-height: 64px;
    }

    .label {
      margin-bottom: 5px;
      color: var(--muted);
      font-size: 11px;
      line-height: 1;
      letter-spacing: 0.09em;
      text-transform: uppercase;
    }

    .value {
      min-width: 0;
      overflow: hidden;
      color: var(--text);
      font-size: clamp(20px, 5.4vw, 25px);
      font-weight: 700;
      line-height: 1.05;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .spectral .value {
      font-size: clamp(18px, 5vw, 23px);
    }

    .speech-card {
      min-height: 0;
      padding: 12px 14px 10px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .speech {
      flex: 1 1 auto;
      min-height: 0;
      margin-top: 2px;
      display: flex;
      align-items: center;
      overflow: hidden;
      font-size: clamp(16px, 4.3vw, 19px);
      font-weight: 500;
      line-height: 1.22;
      letter-spacing: -0.01em;
      overflow-wrap: anywhere;
    }

    .meta {
      flex: 0 0 auto;
      margin-top: 7px;
      overflow: hidden;
      color: #858585;
      font-size: 11px;
      line-height: 1.2;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    /* Compact mode for Safari when its top and bottom bars reduce the viewport. */
    @media (max-height: 760px) {
      .page {
        gap: 7px;
        padding-top: max(7px, env(safe-area-inset-top));
        padding-bottom: max(7px, env(safe-area-inset-bottom));
      }

      h1 {
        font-size: 28px;
      }

      .metric {
        min-height: 62px;
        padding: 8px 10px;
      }

      .metric.spectral {
        min-height: 55px;
      }

      .label {
        margin-bottom: 4px;
        font-size: 10px;
      }

      .value {
        font-size: 20px;
      }

      .spectral .value {
        font-size: 18px;
      }

      .speech-card {
        padding: 10px 12px 8px;
      }

      .speech {
        font-size: 15px;
        line-height: 1.18;
      }

      .meta {
        margin-top: 5px;
        font-size: 10px;
      }
    }

    @media (min-width: 700px) {
      .page {
        max-width: 760px;
        margin: 0 auto;
      }
    }
  </style>
</head>

<body>
  <main class="page">
    <header class="header">
      <h1>Talking Plant</h1>

      <div class="live">
        <span id="dot" class="dot"></span>
        <span id="connection">Waiting</span>
      </div>
    </header>

    <section class="metrics">
      <article class="card metric">
        <div class="label">Soil</div>
        <div id="soil" class="value">—</div>
      </article>

      <article class="card metric">
        <div class="label">Temperature</div>
        <div id="temperature" class="value">—</div>
      </article>

      <article class="card metric">
        <div class="label">Humidity</div>
        <div id="humidity" class="value">—</div>
      </article>

      <article class="card metric">
        <div class="label">Light</div>
        <div id="light" class="value">—</div>
      </article>

      <article class="card metric spectral">
        <div class="label">Spectral light</div>
        <div id="spectrum" class="value">—</div>
      </article>
    </section>

    <section class="card speech-card">
      <div class="label">Now speaking</div>
      <div id="speech" class="speech">
        Waiting for the next plant message…
      </div>
      <div id="meta" class="meta"></div>
    </section>
  </main>

  <script>
    function show(value, fallback = "—") {
      if (value === undefined || value === null || value === "") {
        return fallback;
      }
      return value;
    }

    function numberText(value, digits = 1) {
      const parsed = Number(value);
      if (!Number.isFinite(parsed)) {
        return show(value);
      }
      return parsed.toFixed(digits);
    }

    async function refresh() {
      try {
        const response = await fetch("/api/status", { cache: "no-store" });
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || "No data");
        }

        document.getElementById("soil").textContent =
          show(data.soil_state, show(data.soil_raw));

        document.getElementById("temperature").textContent =
          `${numberText(data.temperature_c, 1)} °C`;

        document.getElementById("humidity").textContent =
          `${numberText(data.humidity, 1)} %`;

        document.getElementById("light").textContent =
          `${numberText(data.light_lux, 0)} lux`;

        document.getElementById("spectrum").textContent =
          show(data.spectral_light_state);

        document.getElementById("speech").textContent =
          show(data.generated_text, "Waiting for the next plant message…");

        const source =
          data.text_source === "azure_llm"
            ? "Azure LLM"
            : "Preset fallback";

        const timestamp = show(data.timestamp, "");
        document.getElementById("meta").textContent =
          timestamp ? `${source} · ${timestamp}` : source;

        document.getElementById("connection").textContent = "Live";
        document.getElementById("dot").classList.add("online");
      } catch (error) {
        document.getElementById("connection").textContent = "Waiting";
        document.getElementById("dot").classList.remove("online");
      }
    }

    refresh();
    setInterval(refresh, 2000);
  </script>
</body>
</html>
"""


def read_latest_row():
    if not LOG_FILE.exists():
        return None

    with LOG_FILE.open("r", newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    return rows[-1] if rows else None


@app.get("/")
def index():
    return render_template_string(PAGE)


@app.get("/api/status")
def status():
    row = read_latest_row()

    if row is None:
        return jsonify({"error": "No broadcast data yet."}), 404

    return jsonify(row)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

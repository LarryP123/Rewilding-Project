import { metricLabels, scenarioDescriptions } from "./config.js";

const paths = {
  overview: "../data/publish/app_overview.json",
  scenarioSummary: "../data/publish/scenario_summary.json",
  appHexPoints: "../data/publish/app_hexes_points.json",
  previewGeojson: "../data/publish/app_hexes_preview.geojson",
};

const state = {
  currentScenarioId: "balanced_strategy",
  overview: null,
  scenarioSummary: [],
  appHexPoints: [],
  previewGeojson: null,
  showStableCoreOnly: false,
  showContestedOnly: false,
};

const elements = {
  scenarioButtons: document.querySelector("#scenario-buttons"),
  mapFilterButtons: document.querySelector("#map-filter-buttons"),
  overviewStats: document.querySelector("#overview-stats"),
  scenarioSummary: document.querySelector("#scenario-summary"),
  scenarioTitle: document.querySelector("#scenario-title"),
  scenarioCopy: document.querySelector("#scenario-copy"),
  previewMetrics: document.querySelector("#preview-metrics"),
  policyMap: document.querySelector("#policy-map"),
  mapTooltip: document.querySelector("#map-tooltip"),
};

const scenarioPercentileField = {
  balanced_strategy: "balanced_strategy_percentile",
  carbon_restoration: "carbon_restoration_percentile",
  flood_resilience: "flood_resilience_percentile",
  lower_conflict: "lower_conflict_percentile",
  nature_recovery: "nature_recovery_percentile",
};

async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Failed to load ${path}: ${response.status}`);
  }
  return response.json();
}

function normalizePointRows(payload) {
  if (Array.isArray(payload)) {
    return payload;
  }

  if (!payload || !Array.isArray(payload.columns) || !Array.isArray(payload.rows)) {
    return [];
  }

  const index = Object.fromEntries(payload.columns.map((name, idx) => [name, idx]));
  return payload.rows.map((row) => ({
    hex_id: row[index.h],
    x: row[index.x],
    y: row[index.y],
    best_scenario_id: row[index.b],
    rank_spread: row[index.r],
    stable_core_flag: Boolean(row[index.s]),
    contested_flag: Boolean(row[index.c]),
    balanced_strategy_percentile: row[index.bs],
    carbon_restoration_percentile: row[index.cr],
    flood_resilience_percentile: row[index.fr],
    lower_conflict_percentile: row[index.lc],
    nature_recovery_percentile: row[index.nr],
  }));
}

function formatNumber(value) {
  return new Intl.NumberFormat("en-GB").format(Number(value));
}

function formatDecimal(value, digits = 1) {
  return new Intl.NumberFormat("en-GB", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(Number(value));
}

function renderScenarioButtons() {
  const buttons = state.scenarioSummary
    .map((scenario) => {
      const isActive = scenario.scenario_id === state.currentScenarioId;
      return `
        <button
          class="scenario-button"
          data-scenario-id="${scenario.scenario_id}"
          data-active="${String(isActive)}"
        >
          ${scenario.scenario_label}
        </button>
      `;
    })
    .join("");

  elements.scenarioButtons.innerHTML = buttons;

  elements.scenarioButtons.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      state.currentScenarioId = button.dataset.scenarioId;
      render();
    });
  });
}

function getVisiblePoints() {
  if (state.showStableCoreOnly && state.showContestedOnly) {
    return state.appHexPoints.filter(
      (point) => point.stable_core_flag || point.contested_flag,
    );
  }

  if (state.showStableCoreOnly) {
    return state.appHexPoints.filter((point) => point.stable_core_flag);
  }

  if (state.showContestedOnly) {
    return state.appHexPoints.filter((point) => point.contested_flag);
  }

  return state.appHexPoints;
}

function renderMapFilterButtons() {
  const buttons = [
    {
      id: "stable",
      label: "Stable core",
      active: state.showStableCoreOnly,
    },
    {
      id: "contested",
      label: "Contested",
      active: state.showContestedOnly,
    },
  ];

  elements.mapFilterButtons.innerHTML = buttons
    .map(
      (button) => `
        <button
          class="map-filter-button"
          data-filter-id="${button.id}"
          data-active="${String(button.active)}"
        >
          ${button.label}
        </button>
      `,
    )
    .join("");

  elements.mapFilterButtons.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      const filterId = button.dataset.filterId;
      if (filterId === "stable") {
        state.showStableCoreOnly = !state.showStableCoreOnly;
      }
      if (filterId === "contested") {
        state.showContestedOnly = !state.showContestedOnly;
      }
      render();
    });
  });
}

function renderOverview() {
  const [overview] = state.overview ?? [];
  if (!overview) {
    elements.overviewStats.innerHTML = "<p>Overview unavailable.</p>";
    return;
  }

  const stats = [
    ["Hexes", formatNumber(overview.hex_count)],
    ["Stable core", formatNumber(overview.stable_core_hex_count)],
    ["Contested", formatNumber(overview.contested_hex_count)],
    ["Avg rank spread", formatNumber(Math.round(overview.avg_rank_spread))],
  ];

  elements.overviewStats.innerHTML = stats
    .map(
      ([label, value]) => `
        <div>
          <dt>${label}</dt>
          <dd>${value}</dd>
        </div>
      `,
    )
    .join("");
}

function renderScenarioSummary() {
  elements.scenarioSummary.innerHTML = state.scenarioSummary
    .map(
      (scenario) => `
        <article class="scenario-card">
          <h3>${scenario.scenario_label}</h3>
          <p>Top decile hexes: ${formatNumber(scenario.top_decile_hex_count)}</p>
          <p>Top 1% hexes: ${formatNumber(scenario.top_1_percent_hex_count)}</p>
          <p>Average score: ${formatDecimal(scenario.avg_weighted_score, 2)}</p>
        </article>
      `,
    )
    .join("");
}

function renderCurrentScenario() {
  const scenario = state.scenarioSummary.find(
    (item) => item.scenario_id === state.currentScenarioId,
  );

  if (!scenario) {
    elements.scenarioTitle.textContent = "Scenario unavailable";
    elements.scenarioCopy.textContent = "";
    return;
  }

  elements.scenarioTitle.textContent = scenario.scenario_label;
  elements.scenarioCopy.textContent =
    scenarioDescriptions[scenario.scenario_id] ?? "";
}

function renderPreviewMetrics() {
  const previewFeatureCount = getVisiblePoints().length;
  const [overview] = state.overview ?? [];
  const stats = [
    [metricLabels.stableCoreHexes, overview?.stable_core_hex_count ?? 0],
    [metricLabels.contestedHexes, overview?.contested_hex_count ?? 0],
    ["Visible points", previewFeatureCount],
  ];

  elements.previewMetrics.innerHTML = stats
    .map(
      ([label, value]) => `
        <div class="metric">
          <span class="metric-label">${label}</span>
          <span class="metric-value">${formatNumber(value)}</span>
        </div>
      `,
    )
    .join("");
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function colorForPercentile(percentile) {
  const t = Math.max(0, Math.min(1, Number(percentile) / 100));
  const low = { r: 49, g: 77, b: 58 };
  const high = { r: 211, g: 231, b: 184 };
  return `rgb(${Math.round(lerp(low.r, high.r, t))}, ${Math.round(
    lerp(low.g, high.g, t),
  )}, ${Math.round(lerp(low.b, high.b, t))})`;
}

function getMapBounds() {
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;

  for (const point of state.appHexPoints) {
    const x = Number(point.x);
    const y = Number(point.y);
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
  }

  return { minX, maxX, minY, maxY };
}

function projectPoint(point, bounds, width, height, padding) {
  const xSpan = bounds.maxX - bounds.minX || 1;
  const ySpan = bounds.maxY - bounds.minY || 1;
  const scale = Math.min(
    (width - padding * 2) / xSpan,
    (height - padding * 2) / ySpan,
  );
  const projectedX =
    (Number(point.x) - bounds.minX) * scale +
    padding +
    (width - padding * 2 - xSpan * scale) / 2;
  const projectedY =
    height -
    ((Number(point.y) - bounds.minY) * scale +
      padding +
      (height - padding * 2 - ySpan * scale) / 2);

  return { x: projectedX, y: projectedY };
}

function drawMap() {
  const canvas = elements.policyMap;
  if (!canvas || !state.appHexPoints.length) return;

  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const padding = 40;
  const visiblePoints = getVisiblePoints();
  const bounds = getMapBounds();
  const percentileField = scenarioPercentileField[state.currentScenarioId];

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#18211b";
  ctx.fillRect(0, 0, width, height);

  for (const point of state.appHexPoints) {
    point._visible = false;
  }

  for (const point of visiblePoints) {
    const projected = projectPoint(point, bounds, width, height, padding);
    point._screenX = projected.x;
    point._screenY = projected.y;
    point._visible = true;

    const percentile = Number(point[percentileField] ?? 0);
    const radius = point.stable_core_flag ? 1.9 : point.contested_flag ? 1.55 : 1.2;
    ctx.beginPath();
    ctx.arc(projected.x, projected.y, radius, 0, Math.PI * 2);
    ctx.fillStyle = colorForPercentile(percentile);
    ctx.fill();
  }
}

function attachMapHover() {
  const canvas = elements.policyMap;
  const tooltip = elements.mapTooltip;
  if (!canvas || !tooltip) return;

  canvas.onpointermove = (event) => {
    if (!state.appHexPoints.length) return;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const mouseX = (event.clientX - rect.left) * scaleX;
    const mouseY = (event.clientY - rect.top) * scaleY;
    const percentileField = scenarioPercentileField[state.currentScenarioId];

    let bestMatch = null;
    let bestDistance = Infinity;
    for (const point of state.appHexPoints) {
      if (!point._visible) continue;
      const dx = mouseX - point._screenX;
      const dy = mouseY - point._screenY;
      const distance = Math.sqrt(dx * dx + dy * dy);
      if (distance < 5 && distance < bestDistance) {
        bestDistance = distance;
        bestMatch = point;
      }
    }

    if (!bestMatch) {
      tooltip.hidden = true;
      return;
    }

    tooltip.hidden = false;
    tooltip.style.left = `${event.clientX - rect.left + 14}px`;
    tooltip.style.top = `${event.clientY - rect.top + 14}px`;
    tooltip.innerHTML = `
      <strong>${bestMatch.hex_id}</strong>
      <p>Current percentile: ${formatDecimal(bestMatch[percentileField], 1)}</p>
      <p>Best scenario: ${bestMatch.best_scenario_id.replaceAll("_", " ")}</p>
      <p>Rank spread: ${formatNumber(bestMatch.rank_spread)}</p>
      <p>Flags: ${
        bestMatch.stable_core_flag
          ? "stable core"
          : bestMatch.contested_flag
            ? "contested"
            : "none"
      }</p>
    `;
  };

  canvas.onpointerleave = () => {
    tooltip.hidden = true;
  };
}

function render() {
  renderScenarioButtons();
  renderMapFilterButtons();
  renderOverview();
  renderScenarioSummary();
  renderCurrentScenario();
  renderPreviewMetrics();
  drawMap();
}

async function init() {
  try {
    const [overview, scenarioSummary, appHexPoints, previewGeojson] = await Promise.all([
      loadJson(paths.overview),
      loadJson(paths.scenarioSummary),
      loadJson(paths.appHexPoints),
      loadJson(paths.previewGeojson),
    ]);

    state.overview = overview;
    state.scenarioSummary = scenarioSummary;
    state.appHexPoints = normalizePointRows(appHexPoints);
    state.previewGeojson = previewGeojson;
    render();
    attachMapHover();
  } catch (error) {
    console.error(error);
    elements.scenarioTitle.textContent = "Frontend scaffold is waiting for data";
    elements.scenarioCopy.textContent =
      "Serve the project over a local HTTP server so the app can fetch the publish assets.";
  }
}

init();

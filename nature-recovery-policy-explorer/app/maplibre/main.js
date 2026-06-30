const paths = {
  tileSchema: "../../data/publish/tile_schema.json",
  scenarioSummary: "../../data/publish/scenario_summary.json",
};

const scenarios = [
  ["balanced_strategy", "Balanced Strategy"],
  ["carbon_restoration", "Carbon Restoration"],
  ["flood_resilience", "Flood Resilience"],
  ["lower_conflict", "Lower Conflict"],
  ["nature_recovery", "Nature Recovery"],
];

const state = {
  currentScenarioId: "balanced_strategy",
  tileSchema: null,
  showStableOnly: false,
  showContestedOnly: false,
  map: null,
  tileLayerName: "policy_hexes",
  pmtilesUrl: null,
  tileMetadata: null,
  selectedFeature: null,
  scenarioSummary: [],
};

const ENGLAND_BOUNDS = [
  [-6.42, 49.86],
  [1.77, 55.82],
];

const elements = {
  scenarioButtons: document.querySelector("#scenario-buttons"),
  scenarioTitle: document.querySelector("#scenario-title"),
  stableToggle: document.querySelector("#stable-toggle"),
  contestedToggle: document.querySelector("#contested-toggle"),
  clearSelection: document.querySelector("#clear-selection"),
  openMethods: document.querySelector("#open-methods"),
  closeMethods: document.querySelector("#close-methods"),
  methodsModal: document.querySelector("#methods-modal"),
  scenarioSummaryPanel: document.querySelector("#scenario-summary-panel"),
  selectionPanel: document.querySelector("#selection-panel"),
  mapHoverTooltip: document.querySelector("#map-hover-tooltip"),
  mapStatus: document.querySelector("#map-status"),
};

function renderScenarioButtons() {
  elements.scenarioButtons.innerHTML = scenarios
    .map(
      ([id, label]) => `
        <button class="scenario-button" data-scenario-id="${id}" data-active="${String(
          id === state.currentScenarioId,
        )}">
          ${label}
        </button>
      `,
    )
    .join("");

  elements.scenarioButtons.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      state.currentScenarioId = button.dataset.scenarioId;
      renderScenarioButtons();
      updateScenarioTitle();
      updateMapStyle();
      renderScenarioSummaryPanel();
      renderSelectionPanel();
    });
  });
}

function updateScenarioTitle() {
  const label = scenarios.find(([id]) => id === state.currentScenarioId)?.[1];
  elements.scenarioTitle.textContent = label ?? "Scenario";
}

function activePercentileField() {
  return state.tileSchema?.scenario_fields?.[state.currentScenarioId]?.percentile;
}

function activeFilterExpression() {
  if (state.showStableOnly && state.showContestedOnly) {
    return [
      "any",
      ["==", ["get", "stable_core_flag"], true],
      ["==", ["get", "contested_flag"], true],
    ];
  }

  if (state.showStableOnly) {
    return ["==", ["get", "stable_core_flag"], true];
  }

  if (state.showContestedOnly) {
    return ["==", ["get", "contested_flag"], true];
  }

  return true;
}

function updateMapStyle() {
  if (!state.map || !state.map.getLayer("policy-fill")) {
    return;
  }

  const percentileField = activePercentileField();
  if (!percentileField) {
    return;
  }

  state.map.setPaintProperty("policy-fill", "fill-color", [
    "interpolate",
    ["linear"],
    ["to-number", ["get", percentileField]],
    0, "#314d3a",
    50, "#7faa77",
    100, "#d3e7b8",
  ]);
  state.map.setFilter("policy-fill", activeFilterExpression());
  state.map.setFilter("policy-outline", activeFilterExpression());
  if (state.map.getLayer("policy-selected")) {
    state.map.setFilter(
      "policy-selected",
      state.selectedFeature
        ? ["==", ["get", "hex_id"], state.selectedFeature.properties?.hex_id ?? ""]
        : ["==", ["get", "hex_id"], ""],
    );
  }
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

function activeScenarioLabel() {
  return scenarios.find(([id]) => id === state.currentScenarioId)?.[1] ?? "Scenario";
}

function formatScenarioId(value) {
  return String(value ?? "unknown").replaceAll("_", " ");
}

function renderScenarioSummaryPanel() {
  const summary = state.scenarioSummary.find(
    (item) => item.scenario_id === state.currentScenarioId,
  );

  if (!summary) {
    elements.scenarioSummaryPanel.innerHTML =
      '<p class="selection-empty">Scenario summary unavailable.</p>';
    return;
  }

  let filterText = "Showing all hexes.";
  if (state.showStableOnly && state.showContestedOnly) {
    filterText = "Showing stable-core and contested hexes only.";
  } else if (state.showStableOnly) {
    filterText = "Showing stable-core hexes only.";
  } else if (state.showContestedOnly) {
    filterText = "Showing contested hexes only.";
  }

  elements.scenarioSummaryPanel.innerHTML = `
    <div class="scenario-summary-grid">
      <p class="scenario-summary-copy">
        ${activeScenarioLabel()} shows how the national grid changes when this
        policy lens is treated as the priority.
      </p>
      <div class="scenario-summary-stats">
        <div class="scenario-summary-stat">
          <span>Top Decile</span>
          <strong>${formatNumber(summary.top_decile_hex_count ?? 0)}</strong>
        </div>
        <div class="scenario-summary-stat">
          <span>Top 1%</span>
          <strong>${formatNumber(summary.top_1_percent_hex_count ?? 0)}</strong>
        </div>
        <div class="scenario-summary-stat">
          <span>Stable Core</span>
          <strong>${formatNumber(summary.stable_core_hex_count ?? 0)}</strong>
        </div>
        <div class="scenario-summary-stat">
          <span>Contested</span>
          <strong>${formatNumber(summary.contested_hex_count ?? 0)}</strong>
        </div>
      </div>
      <p class="scenario-summary-copy">${filterText}</p>
    </div>
  `;
}

function renderSelectionPanel() {
  if (!state.selectedFeature) {
    elements.selectionPanel.innerHTML =
      '<p class="selection-empty">Click a hex on the map to inspect it.</p>';
    return;
  }

  const properties = state.selectedFeature.properties ?? {};
  const percentileField = activePercentileField();
  const percentile = properties[percentileField];
  const flags = [];
  if (properties.stable_core_flag) flags.push("Stable core");
  if (properties.contested_flag) flags.push("Contested");
  if (flags.length === 0) flags.push("No active flag");
  const interpretation =
    Number(percentile ?? 0) >= 90
      ? "This hex ranks relatively highly under the active scenario."
      : Number(percentile ?? 0) >= 70
        ? "This hex performs above average under the active scenario, but not among the highest-ranked cells."
        : "This hex performs less strongly under the active scenario than the highest-ranked areas.";

  elements.selectionPanel.innerHTML = `
    <div class="selection-grid">
      <div class="selection-hero">
        <strong>${properties.hex_id}</strong>
        <p>${activeScenarioLabel()} percentile: ${formatDecimal(percentile ?? 0, 1)}</p>
        <p>${interpretation}</p>
      </div>
      <div class="selection-stats">
        <div class="selection-stat">
          <span>Best Scenario</span>
          <strong>${formatScenarioId(properties.best_scenario_id)}</strong>
        </div>
        <div class="selection-stat">
          <span>Best Rank</span>
          <strong>${formatNumber(properties.best_rank ?? 0)}</strong>
        </div>
        <div class="selection-stat">
          <span>Rank Spread</span>
          <strong>${formatNumber(properties.rank_spread ?? 0)}</strong>
        </div>
        <div class="selection-stat">
          <span>Active Percentile</span>
          <strong>${formatDecimal(percentile ?? 0, 1)}</strong>
        </div>
      </div>
      <div class="selection-flags">
        ${flags.map((flag) => `<span class="selection-flag">${flag}</span>`).join("")}
      </div>
    </div>
  `;
}

function hideHoverTooltip() {
  elements.mapHoverTooltip.hidden = true;
}

function showHoverTooltip(event, feature) {
  if (!feature) {
    hideHoverTooltip();
    return;
  }

  const properties = feature.properties ?? {};
  const percentileField = activePercentileField();
  const percentile = properties[percentileField];
  elements.mapHoverTooltip.hidden = false;
  elements.mapHoverTooltip.style.left = `${event.point.x + 18}px`;
  elements.mapHoverTooltip.style.top = `${event.point.y + 18}px`;
  elements.mapHoverTooltip.innerHTML = `
    <strong>${properties.hex_id}</strong>
    <p>${activeScenarioLabel()} percentile: ${formatDecimal(percentile ?? 0, 1)}</p>
    <p>Best rank: ${formatNumber(properties.best_rank ?? 0)}</p>
  `;
}

async function loadTileSchema() {
  const response = await fetch(paths.tileSchema);
  if (!response.ok) {
    throw new Error(`Failed to load ${paths.tileSchema}`);
  }
  state.tileSchema = await response.json();
  state.tileLayerName =
    state.tileSchema?.tile_strategy?.recommended_layer_name ?? "policy_hexes";
}

async function loadScenarioSummary() {
  const response = await fetch(paths.scenarioSummary);
  if (!response.ok) {
    throw new Error(`Failed to load ${paths.scenarioSummary}`);
  }
  state.scenarioSummary = await response.json();
}

async function loadTileMetadata() {
  if (!window.pmtiles || !state.pmtilesUrl) {
    return;
  }
  const source = new pmtiles.PMTiles(state.pmtilesUrl);
  state.tileMetadata = await source.getHeader();
}

function initMap() {
  if (!window.maplibregl) {
    elements.mapStatus.textContent = "MapLibre script failed to load.";
    return;
  }

  if (!window.pmtiles) {
    elements.mapStatus.textContent = "PMTiles script failed to load.";
    return;
  }

  const protocol = new pmtiles.Protocol();
  maplibregl.addProtocol("pmtiles", protocol.tile);
  state.pmtilesUrl = new URL(
    "../../data/publish/policy_hexes.pmtiles",
    window.location.href,
  ).toString();
  const pmtilesSource = new pmtiles.PMTiles(state.pmtilesUrl);
  protocol.add(pmtilesSource);

  state.map = new maplibregl.Map({
    container: "map",
    style: {
      version: 8,
      sources: {},
      layers: [
        {
          id: "background",
          type: "background",
          paint: {
            "background-color": "#17201a",
          },
        },
      ],
    },
    center: [-2.2, 53.2],
    zoom: 5,
    attributionControl: false,
  });

  state.map.addControl(new maplibregl.NavigationControl(), "top-right");

  state.map.on("load", () => {
    elements.mapStatus.textContent =
      `Loading local PMTiles source from ${state.pmtilesUrl} …`;

    state.map.addSource("policy_hexes", {
      type: "vector",
      url: `pmtiles://${state.pmtilesUrl}`,
    });

    state.map.addLayer({
      id: "policy-fill",
      type: "fill",
      source: "policy_hexes",
      "source-layer": state.tileLayerName,
      paint: {
        "fill-color": "#7faa77",
        "fill-opacity": 0.9,
      },
      filter: true,
    });

    state.map.addLayer({
      id: "policy-outline",
      type: "line",
      source: "policy_hexes",
      "source-layer": state.tileLayerName,
      paint: {
        "line-color": "rgba(255,255,255,0.22)",
        "line-width": 0.45,
      },
      filter: true,
    });

    state.map.addLayer({
      id: "policy-selected",
      type: "line",
      source: "policy_hexes",
      "source-layer": state.tileLayerName,
      paint: {
        "line-color": "#f2e7bf",
        "line-width": 2.2,
      },
      filter: ["==", ["get", "hex_id"], ""],
    });

    state.map.fitBounds(ENGLAND_BOUNDS, { padding: 36, animate: false });

    updateMapStyle();

    state.map.on("mouseenter", "policy-fill", () => {
      state.map.getCanvas().style.cursor = "pointer";
    });

    state.map.on("mouseleave", "policy-fill", () => {
      state.map.getCanvas().style.cursor = "";
      hideHoverTooltip();
    });

    state.map.on("mousemove", "policy-fill", (event) => {
      const feature = event.features?.[0];
      showHoverTooltip(event, feature);
    });

    state.map.on("click", "policy-fill", (event) => {
      const feature = event.features?.[0];
      if (!feature) return;
      state.selectedFeature = feature;
      renderSelectionPanel();
      updateMapStyle();
    });
  });

  state.map.on("idle", () => {
    const hasFill = Boolean(state.map.getLayer("policy-fill"));
    if (hasFill) {
      elements.mapStatus.textContent =
        "Local PMTiles source loaded. Scenario recoloring and stable/contested filters are active.";
    }
  });

  state.map.on("error", (event) => {
    console.error(event.error);
    elements.mapStatus.textContent =
      `Map source error: ${event?.error?.message ?? "unknown error"}`;
  });
}

function bindToggles() {
  elements.stableToggle.addEventListener("change", () => {
    state.showStableOnly = elements.stableToggle.checked;
    updateMapStyle();
    renderScenarioSummaryPanel();
  });
  elements.contestedToggle.addEventListener("change", () => {
    state.showContestedOnly = elements.contestedToggle.checked;
    updateMapStyle();
    renderScenarioSummaryPanel();
  });
  elements.clearSelection.addEventListener("click", () => {
    state.selectedFeature = null;
    renderSelectionPanel();
    updateMapStyle();
  });
  elements.openMethods.addEventListener("click", () => {
    elements.methodsModal.showModal();
  });
  elements.closeMethods.addEventListener("click", () => {
    elements.methodsModal.close();
  });
}

async function init() {
  renderScenarioButtons();
  updateScenarioTitle();
  renderScenarioSummaryPanel();
  renderSelectionPanel();
  bindToggles();

  try {
    await loadTileSchema();
    await loadScenarioSummary();
    state.pmtilesUrl = new URL(
      "../../data/publish/policy_hexes.pmtiles",
      window.location.href,
    ).toString();
    await loadTileMetadata();
  } catch (error) {
    console.error(error);
    elements.scenarioSummaryPanel.innerHTML =
      '<p class="selection-empty">Sidebar data unavailable.</p>';
  }

  renderScenarioSummaryPanel();

  initMap();
}

init();

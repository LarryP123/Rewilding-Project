# Visual Model

This project is a screening model, not a site-selection model. The visual below shows how source layers become 1 km cell features, scenario scores, validation outputs, and the published map app.

```mermaid
flowchart LR
    subgraph Inputs["Source Data"]
        Boundary["England boundary"]
        Habitat["CORINE habitat context"]
        Birds["Verified bird observations"]
        Mammals["Verified mammal observations"]
        ALC["Agricultural Land Classification"]
        Flood["Dedicated flood layer"]
        Peat["Dedicated peat layer"]
        LNRS["Optional LNRS boundaries"]
    end

    subgraph Standardise["Standardise And Prepare"]
        CRS["Reproject to British National Grid"]
        Clean["Repair geometries and cache clean layers"]
        Grid["Build 1 km hex grid"]
    end

    subgraph Features["Per-Hex Feature Engineering"]
        HabitatFeature["Habitat share and habitat proximity"]
        BioFeature["Bird and mammal richness with record-coverage damping"]
        AgriFeature["Agricultural opportunity score"]
        FloodFeature["Flood opportunity score"]
        PeatFeature["Peat opportunity score"]
        BoundaryPenalty["Undersized boundary-cell penalty"]
    end

    subgraph Scores["Scenario Scoring"]
        Nature["Nature-first"]
        Balanced["Balanced"]
        LowConflict["Low-conflict"]
    end

    subgraph Outputs["Published Outputs"]
        HexScores["Canonical scored hex layer"]
        Shortlist["Top-candidate tables and GeoJSON"]
        Clusters["Candidate-zone summaries"]
        Validation["Scenario overlap, sensitivity, and case studies"]
        Methods["Methods note and candidate brief"]
        App["Standalone HTML explorer"]
        Release["Release checkpoint"]
    end

    Boundary --> CRS
    Habitat --> CRS
    Birds --> CRS
    Mammals --> CRS
    ALC --> CRS
    Flood --> CRS
    Peat --> CRS
    LNRS --> CRS

    CRS --> Clean
    Clean --> Grid
    Grid --> HabitatFeature
    Grid --> BioFeature
    Grid --> AgriFeature
    Grid --> FloodFeature
    Grid --> PeatFeature
    Grid --> BoundaryPenalty

    HabitatFeature --> Nature
    HabitatFeature --> Balanced
    HabitatFeature --> LowConflict
    BioFeature --> Nature
    BioFeature --> Balanced
    BioFeature --> LowConflict
    AgriFeature --> Nature
    AgriFeature --> Balanced
    AgriFeature --> LowConflict
    FloodFeature --> Nature
    FloodFeature --> Balanced
    FloodFeature --> LowConflict
    PeatFeature --> Nature
    PeatFeature --> Balanced
    PeatFeature --> LowConflict
    BoundaryPenalty --> Nature
    BoundaryPenalty --> Balanced
    BoundaryPenalty --> LowConflict

    Nature --> HexScores
    Balanced --> HexScores
    LowConflict --> HexScores

    HexScores --> Shortlist
    HexScores --> Clusters
    HexScores --> Validation
    HexScores --> Methods
    HexScores --> App
    HexScores --> Release
    LNRS -. optional policy slicing .-> Shortlist
    LNRS -. optional policy slicing .-> Clusters
```

## Score Components

The canonical score layer combines six main score families:

| Component | Meaning | Direction |
| --- | --- | --- |
| Restoration opportunity | High where cells are close to habitat but still have restoration headroom | Higher is better |
| Biodiversity observation | Bird and mammal species richness, damped by record coverage | Higher is better |
| Agricultural opportunity | Lower agricultural tradeoff based on ALC grade | Higher is lower conflict |
| Flood opportunity | Dedicated flood-source opportunity signal | Higher is more opportunity |
| Peat opportunity | Dedicated peat-source opportunity signal | Higher is more opportunity |
| Boundary penalty | Downweights clipped boundary/coastal cell fragments | Higher is less penalised |

## Scenario Logic

```mermaid
flowchart TB
    Components["Shared per-hex components"] --> Nature["Nature-first: prioritises restoration and biodiversity"]
    Components --> Balanced["Balanced: mixes ecology, flood, peat, and agricultural tradeoff"]
    Components --> LowConflict["Low-conflict: gives more weight to agricultural opportunity"]

    Nature --> Compare["Compare scenario rankings"]
    Balanced --> Compare
    LowConflict --> Compare

    Compare --> Core["Stable core candidates"]
    Compare --> Variants["Objective-specific candidate variants"]
```

The model is most useful when read as a **core-plus-variants decision aid**:

- The stable core contains cells that remain strong across all three scenarios.
- Nature-first variants show places that rise when ecological opportunity matters most.
- Low-conflict variants show places that rise when lower agricultural tradeoff matters most.

## Current Canonical Release

- Release: `canonical_v6`
- Scored layer: `data/interim/mvp_official_boundary_1km_v6/hex_scores.parquet`
- Release checkpoint: `outputs/release/canonical_v6.json`
- Explorer app: `outputs/app/rewilding_opportunity_explorer.html`


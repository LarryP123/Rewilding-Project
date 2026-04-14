# Methods

## Framing

This project is a spatial prioritisation system, not a causal model. The aim is to identify places in England where rewilding appears most promising under different policy objectives by combining multiple geospatial signals into scenario-based suitability scores.

## Unit of analysis

The main analysis unit is a 1 km hex grid in British National Grid (`EPSG:27700`). A regular grid makes it easier to integrate heterogeneous source layers and compare scenarios consistently across England.

## MVP feature set

The initial MVP focuses on a manageable set of defensible features:

- habitat context from land-cover or priority-habitat layers,
- connectivity opportunity from proximity to existing habitat,
- agricultural opportunity cost using Agricultural Land Classification,
- flood opportunity from flood-related layers.

Peat restoration and biodiversity occurrence features are planned extensions once the baseline workflow is stable.

## Scoring approach

Each feature is converted to a common 0 to 100 interpretation where higher values mean stronger rewilding opportunity. The repo currently defines three starting scenarios:

- `scenario_nature_first`
- `scenario_balanced`
- `scenario_low_conflict`

These are intended as transparent policy lenses rather than claims about a single objectively correct ranking.

## Limitations

- Suitability scores are only as strong as the source layers and feature engineering choices.
- Opportunity proxies should not be interpreted as proof of ecological or flood outcomes.
- Agricultural tradeoff is simplified when represented only through dominant ALC grade.
- Biodiversity occurrence data, when added, will require effort-bias handling.

## Next steps

1. Add England boundary and priority habitat source layers.
2. Build the first reproducible hex grid product.
3. Generate a baseline per-hex feature table.
4. Validate top-ranked areas with map inspection and case studies.

## Current implementation note

The current local MVP uses a proxy analysis boundary derived from ALC coverage because an official England boundary layer has not yet been added to the repository. Habitat-context features are currently sourced from the locally generated CORINE subset in British National Grid.

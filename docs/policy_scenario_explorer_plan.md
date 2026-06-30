# Nature Recovery Policy Explorer

## Project Concept

`nature-recovery-policy-explorer`

A smaller companion project that compares how different policy priorities change a national shortlist for nature recovery.

Core question:

How do different public policy priorities change which places appear strongest for nature recovery?

This makes the project about tradeoffs rather than about finding one "correct" answer.

## How It Should Differ From The Current Atlas

The current project is:

- a full national screening workflow
- one main model with scenario variants
- a broad atlas and product

This project should be:

- tighter and more policy-focused
- built around comparison rather than just scoring
- simpler technically and clearer conceptually
- explicitly aimed at decision support

The main output is not just "here is the shortlist".

It is:

- here is what stays stable across priorities
- here is what changes
- here is why

## Recommended Scope

Keep the geography manageable.

Options:

- England again, reusing the base layer
- one region, if a lighter version is preferred

Recommended approach:

Reuse the England hex layer and core indicators from the current repo, but build a separate repo with a cleaner scenario-comparison product.

## Scenario Set

Use four or five named scenarios with clear policy logic.

Recommended set:

### Nature Recovery

Focus on biodiversity, habitat expansion, and connectivity.

### Flood Resilience

Focus on floodplain, wetland, and hydrological opportunity.

### Carbon Restoration

Focus on peat and longer-term ecological recovery.

### Lower Conflict

Focus on reducing tension with productive farmland.

### Balanced Strategy

A mixed public-policy baseline.

Each scenario should include:

- a one-sentence rationale
- a transparent weight table
- a note on what it deprioritises

That explicit tradeoff framing is part of what makes the project strong.

## Core Features

Build the project around these outputs.

### 1. Scenario Switcher

Lets users move between policy lenses.

### 2. Stable-Core Layer

Shows places that remain strong across all scenarios.

### 3. Sensitive-Areas Layer

Shows places that rise or fall depending on priorities.

### 4. Comparison Metrics

Overlap, churn, rank change, and stable top cells.

### 5. Per-Place Explanation

Why a place ranks well under one scenario and not another.

### 6. Findings Page

A short plain-English summary of what the scenario comparison shows.

## Pages And Screens

Keep it to five pages maximum.

### 1. Home

What the tool is, what question it answers, and why policy tradeoffs matter.

### 2. Explorer

Interactive map with scenario switching and an explanation panel.

### 3. Compare

Overlap metrics, stable-core map, and biggest movers.

### 4. Scenarios

Definitions, weight tables, rationale, and limitations.

### 5. Methods

Data, model structure, and caveats.

That is enough. The project should stay focused.

## Repo Structure

```text
nature-recovery-policy-explorer/
  README.md
  pyproject.toml
  data/
  src/
    scenarios.py
    scoring.py
    compare.py
    exports.py
  scripts/
    build_explorer.py
    build_site.py
    run_policy_scenarios.py
  outputs/
  docs/
```

## Recommended Technical Shape

Reuse what already works:

- 1 km grid
- main indicator layers
- scoring pipeline ideas
- site generation pattern

New logic to add:

- scenario registry
- scenario comparison metrics
- stable-core detection
- rank-change summaries
- scenario-specific explanation text

This keeps the project distinct without rebuilding the whole base system from scratch.

## Key Analysis Outputs

These are the most useful comparison outputs:

- top 100 overlap by scenario
- Jaccard overlap matrix
- cells appearing in all scenarios
- cells unique to one scenario
- average rank shift by area
- most policy-sensitive candidate zones

These provide strong material for both visuals and write-up.

## What Employers Will Notice

This project signals good practice because it shows:

- value judgments are made explicit
- alternatives are compared directly
- uncertainty is communicated clearly
- analysis is turned into a user-facing tool
- policy decisions are treated as tradeoffs, not just optimisation problems

That is a strong signal for consulting, govtech, public sector, and climate or nature product roles.

## Milestone Plan

### Phase 1: Define The Scenarios

- choose four to five policy lenses
- write rationale for each
- lock weight tables
- document what each scenario emphasises

### Phase 1 Output

Phase 1 should end with a single scenario registry that every later script uses.

That registry should define:

- scenario id
- public-facing label
- one-sentence rationale
- weight table
- what the scenario emphasises
- what the scenario deprioritises

The recommended feature set is the same one already used in the atlas:

- `restoration_opportunity_score`
- `flood_opportunity_score_raw`
- `peat_opportunity_score_raw`
- `agri_opportunity_score_raw`
- `habitat_mosaic_score`
- `biodiversity_observation_score_raw`

### Recommended Phase 1 Scenario Definitions

#### 1. Nature Recovery

Rationale:

Prioritise places that look strongest for habitat recovery, biodiversity, and ecological connection, even when they may involve greater land-use tradeoffs.

Draft weights:

- restoration opportunity: `0.34`
- flood opportunity: `0.12`
- peat opportunity: `0.12`
- agricultural opportunity: `0.08`
- habitat mosaic: `0.09`
- biodiversity observation: `0.25`

Emphasises:

- biodiversity signal
- restoration potential near existing habitat
- ecological continuity and mixed habitat context

Deprioritises:

- lower-conflict land-use framing
- purely delivery-oriented caution

Why this is distinct:

This should be the clearest ecological upside scenario, and it should visibly raise places with strong biodiversity and restoration logic even when they are not the easiest sites politically or economically.

#### 2. Flood Resilience

Rationale:

Prioritise places where nature recovery overlaps strongly with wetland, floodplain, and hydrological restoration value.

Draft weights:

- restoration opportunity: `0.22`
- flood opportunity: `0.32`
- peat opportunity: `0.10`
- agricultural opportunity: `0.10`
- habitat mosaic: `0.06`
- biodiversity observation: `0.20`

Emphasises:

- flood-related opportunity
- restoration in wetland and floodplain contexts
- biodiversity where it aligns with hydrological restoration

Deprioritises:

- peat-specific restoration unless it overlaps with flood logic
- lower-conflict framing as the main objective

Why this is distinct:

This should create visibly different outputs in lowland wetland and floodplain landscapes, and it gives the project a clear adaptation and resilience angle that employers will recognise.

#### 3. Carbon Restoration

Rationale:

Prioritise places where nature recovery aligns most strongly with peat and longer-term carbon restoration logic.

Draft weights:

- restoration opportunity: `0.24`
- flood opportunity: `0.10`
- peat opportunity: `0.32`
- agricultural opportunity: `0.08`
- habitat mosaic: `0.06`
- biodiversity observation: `0.20`

Emphasises:

- peat opportunity
- restoration logic in upland or carbon-relevant landscapes
- biodiversity where it overlaps with carbon restoration

Deprioritises:

- lower-conflict farmland framing
- floodplain restoration unless it also overlaps with peat value

Why this is distinct:

This gives the project a clear climate-policy dimension and should reveal whether peat-heavy landscapes stay strong even when biodiversity and flood are not the sole focus.

#### 4. Lower Conflict

Rationale:

Prioritise places that look easier to advance with less tension around productive farmland and land-use tradeoffs.

Draft weights:

- restoration opportunity: `0.20`
- flood opportunity: `0.12`
- peat opportunity: `0.08`
- agricultural opportunity: `0.36`
- habitat mosaic: `0.09`
- biodiversity observation: `0.15`

Emphasises:

- reduced agricultural conflict
- feasible-looking restoration contexts
- mixed landscapes that may be easier to open for discussion

Deprioritises:

- maximum ecological ambition where it conflicts with delivery ease
- peat and flood unless they coincide with lower-conflict land

Why this is distinct:

This is the scenario that makes the tradeoff logic most visible. It should move the shortlist in ways that clearly communicate the cost of prioritising ease of delivery.

#### 5. Balanced Strategy

Rationale:

Provide a mixed policy baseline that spreads weight across ecological recovery, flood, peat, and land-use tradeoff without pushing too strongly in one direction.

Draft weights:

- restoration opportunity: `0.28`
- flood opportunity: `0.18`
- peat opportunity: `0.14`
- agricultural opportunity: `0.16`
- habitat mosaic: `0.07`
- biodiversity observation: `0.17`

Emphasises:

- an all-round public-policy compromise
- no single objective dominating the shortlist
- interpretability as a baseline reference

Deprioritises:

- none entirely, but it does not maximise any single policy aim

Why this is distinct:

This should be the anchor scenario used for most comparison pages. It gives users a reasonable baseline before they inspect more specialised lenses.

### Phase 1 Rules For Locking The Weight Tables

To keep the scenario set disciplined, use these rules:

1. Every scenario must sum to `1.00`.
2. Every scenario must contain all six components, even if some are low-weight.
3. No scenario should differ only trivially from another; each one should produce a meaningful shift in outputs.
4. Every scenario must have a short policy rationale that a non-technical user could understand.
5. The balanced strategy should stay close enough to the current atlas baseline to act as a stable reference.

### Phase 1 Documentation To Produce

At the end of Phase 1, create:

- a `src/scenarios.py` registry
- a `docs/scenarios.md` page with rationale and weight tables
- a small comparison chart showing scenario weights side by side
- one short note explaining why these are policy lenses rather than neutral truths

### Recommended Phase 1 Decision

Use all five scenarios above.

Why:

- four scenarios is workable, but five gives a clearer policy spread
- flood and carbon deserve to be separate lenses
- balanced strategy gives the comparison a stable anchor
- lower conflict keeps the delivery side visible
- nature recovery remains the clear ecological reference

### Phase 2: Build The Comparison Pipeline

- score all scenarios
- compute overlaps and rank shifts
- derive stable-core and sensitive-area layers

### Phase 3: Build The Explorer

- scenario switcher
- explanation panel
- shortlist view
- comparison overlays

### Phase 4: Build The Site

- home
- scenarios page
- compare page
- methods page

### Phase 5: Write Findings

Good examples:

- which places are stable regardless of policy
- which places are contested
- which objectives create the biggest divergence

## What To Put In The README

Keep it simple:

- project question
- why scenario comparison matters
- scenarios included
- main findings
- screenshots
- link to live site
- link to the original national screening repo

## How To Make It Distinct From The Atlas

Be deliberate about the framing:

- call it a policy explorer, not a rewilding atlas
- foreground comparison, not ranking
- keep the interface cleaner and more analytic
- focus the writing on tradeoffs and interpretation

## Recommendation

Build this as:

`nature-recovery-policy-explorer`

Recommended form:

- England reuse
- five policy scenarios
- a strong Compare page

This is likely the best balance of:

- manageable effort
- clear distinction from the current project
- strong employer signal

## Next Optional Step

If this project is chosen, the next planning document should define:

1. the actual scenario definitions and weights
2. a draft README
3. a first-week build checklist

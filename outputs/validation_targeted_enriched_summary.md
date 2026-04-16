# Enriched Rewilding Model: Technical Report And Findings

## Executive Summary

This rerun answers a practical question: what changes when flood, peat, and biodiversity stop being placeholder dimensions and become active parts of the ranking?

The short answer is that the shortlist becomes both more credible and more interpretable. A meaningful core survives across objectives, but the enriched features clearly reshape which edge cases rise or fall. That is exactly what we would want from an improved model: not random churn, but targeted reordering that reveals different kinds of opportunity.

For a portfolio audience, the key takeaway is that this project is not just a map-making exercise. It shows a full decision-support workflow: feature engineering, targeted reruns for computational efficiency, robustness testing, scenario comparison, and narrative interpretation of what the model is actually doing.

## 1. Technical Report

### Purpose

The purpose of this targeted enriched run was to test whether activating flood, peat, and biodiversity signals changes the national shortlist in a meaningful and defensible way, without paying the cost of a full national rebuild.

### Scope And Method

- Source layer: `data/interim/mvp_official_boundary_1km_targeted_enriched/hex_scores_targeted_enriched.parquet`
- Validation design: rerun flood, peat, and biodiversity features for the union of the top 5,000 cells from each legacy scenario
- Candidate universe rerun: `6,335` cells
- Comparison scale: top `100` cells per scenario

This is a shortlist-focused enriched rerun, not a full national reprocessing pass. That matters because the goal here is validation of shortlist behavior, not publication of a new canonical national surface.

### Scenario Stability

- `63` cells appear in the top 100 under all three objectives.
- Nature-first vs balanced overlap: `78` shared cells, Jaccard `0.639`.
- Nature-first vs low-conflict overlap: `64` shared cells, Jaccard `0.471`.
- Balanced vs low-conflict overlap: `75` shared cells, Jaccard `0.600`.

Interpretation: the enriched shortlist is cohesive, but not objective-invariant. Balanced and low-conflict remain close to one another, while nature-first is the scenario that most clearly pulls the ranking toward a different edge of the opportunity space.

### Shortlist Churn Vs Earlier Scores

- Nature-first keeps `24` of the old top 100 and replaces `76`.
- Balanced keeps `33` of the old top 100 and replaces `67`.
- Low-conflict keeps `43` of the old top 100 and replaces `57`.

Interpretation: the added features are not cosmetic. They materially reorder the shortlist, especially for the more ecologically directional scenario.

### Sensitivity To Weight Changes

Top-100 overlap after a +/-20% perturbation to each enriched weight:

- Nature-first: flood `91-95`, peat `74-93`, biodiversity `83-88`
- Balanced: flood `90-92`, peat `89-94`, biodiversity `89-91`
- Low-conflict: flood `92-95`, peat `95-97`, biodiversity `93-96`

Interpretation: balanced and low-conflict are robust to moderate reweighting. Nature-first is visibly more sensitive, and peat is the main swing factor inside that scenario.

### What The New Objectives Are Actually Doing

Across the enriched top 100:

- Nature-first mean scores: flood `39.24`, peat `33.26`, biodiversity `63.32`
- Balanced mean scores: flood `39.34`, peat `33.14`, biodiversity `61.23`
- Low-conflict mean scores: flood `37.65`, peat `32.97`, biodiversity `62.11`

Every shortlisted cell now carries non-zero flood, peat, and biodiversity values. That is a substantial modeling improvement over earlier score layers where some of these dimensions were effectively inert.

## 2. Findings Article

### Finding 1: The enriched model produces a real “core shortlist,” not just three unrelated rankings

The most reassuring result is the existence of a `63`-cell shared core across all three top-100 lists. That is too large to dismiss as accidental overlap. It means the model is repeatedly rediscovering a common set of strong opportunities even when the objective changes.

That matters because portfolio projects often look fragile once multiple scenarios are introduced. Here, the opposite is true: scenario design changes the edges of the shortlist more than the center. The project therefore supports a stronger story than “here is one arbitrary ranking.” It supports “here is a stable national core plus policy-specific extensions.”

### Finding 2: Enrichment changes the ecological story more than the delivery story

Shortlist churn is not evenly distributed. Low-conflict retains `43` of the previous top 100, balanced retains `33`, and nature-first retains only `24`.

That asymmetry is non-obvious and important. It suggests the enriched features are not acting like a general noise injection. Instead, they are correcting the ranking most strongly where the model is supposed to care most about ecological nuance. In other words, the new layers sharpen the ecological scenario far more than they disrupt the feasibility-oriented one.

### Finding 3: Peat is the decisive swing feature inside the nature-first scenario

The strongest sensitivity result is not flood or biodiversity. It is peat. Under a +/-20% perturbation, nature-first overlap falls as low as `74`, while the same scenario stays in the `91-95` range for flood and `83-88` for biodiversity.

That points to a deeper structural lesson: once you already have strong connectivity and restoration signals, peat becomes one of the main factors deciding which ecologically promising cells break into the very top tier. That makes peat less of a “nice to have” layer and more of a rank-shaping feature for ecology-led prioritisation.

### Finding 4: The new policy layers are filtering and reordering, not dominating the shortlist by themselves

Flood and peat means sit in the high 30s and low 30s across the shortlisted cells, while biodiversity sits around `61-63`. Those are meaningful values, but not runaway values. Combined with the case studies, this suggests the enriched layers are acting more like discriminators within already promising landscapes than like single-handed drivers of selection.

That is a healthy result. It means the shortlist is still anchored in structural restoration logic such as connectivity, restoration headroom, and agricultural tradeoff, while flood, peat, and biodiversity help decide which of those already-promising places should move up or down.

### Finding 5: The right product is not one ranking, but a core-plus-variants decision package

The stable core winner, the nature-first specialist, and the low-conflict specialist tell a consistent story. Some cells are strong regardless of objective. Others only become attractive when the scenario genuinely leans toward ecological upside or delivery practicality.

That means the strongest presentation format for this project is not “the top 100 places in England.” It is:

- a shared core shortlist for regret-minimising candidates,
- a nature-first expansion set for ecological ambition,
- and a low-conflict expansion set for delivery-oriented prioritisation.

This is a more mature decision-support product because it admits that objective choice is part of the analysis rather than something to hide after scoring.

## 3. Illustrative Cases

### Stable Core Winner

- Hex: `hex_0054754`
- Ranks: nature-first `1`, balanced `1`, low-conflict `3`
- Signals: flood `40.00`, peat `33.94`, biodiversity `74.33`, agriculture `100.00`, connectivity `98.22`, restoration `84.52`

Why it matters: this is the “regret-minimising” type of candidate. It stays near the top because it is strong on both practicality and ecological context.

### Nature-First Specialist

- Hex: `hex_0017898`
- Ranks: nature-first `35`, balanced `32987`, low-conflict `33760`
- Signals: flood `39.66`, peat `22.71`, biodiversity `73.77`, agriculture `80.00`, connectivity `99.04`, restoration `86.21`

Why it matters: this is a strong example of objective dependence. The cell does not disappear because it is weak; it disappears because it stops fitting the decision logic once practicality is weighted more heavily.

### Low-Conflict Delivery Specialist

- Hex: `hex_0083178`
- Ranks: low-conflict `55`, balanced `123`, nature-first `85`
- Signals: flood `30.07`, peat `33.67`, biodiversity `67.42`, agriculture `100.00`, connectivity `99.23`, restoration `77.59`

Why it matters: this is the kind of place that stays respectable ecologically but becomes much more compelling when delivery feasibility is treated as a first-order concern.

## 4. Implementation Gaps And Next Data

The current tool already covers most of the spatial prioritisation backbone from the original brief, but it is still best understood as a first strong version rather than the final decision-ready product.

| Brief ambition | Implemented now | Next data needed |
| --- | --- | --- |
| National England prioritisation | England-wide analysis extent with official boundary workflow | Keep the canonical published build tied to the final official boundary inputs |
| Consistent spatial comparison | 1 km hex grid in British National Grid | No major new data needed |
| Habitat-led opportunity mapping | Habitat context and habitat proximity / connectivity are active in scoring | Better habitat condition and restoration potential layers |
| Biodiversity signal | Bird-observation layer from verified NBN/iRecord records | More taxa, habitat-condition indicators, and protected or priority species evidence where appropriate |
| Agricultural tradeoff / feasibility | Agricultural Land Classification proxy is active | Stronger land-use feasibility layers, farm systems, land value, or management context |
| Flood opportunity | Dedicated flood path supported, with fallback proxy logic | Ensure the dedicated flood dataset is used in the canonical build |
| Peat / carbon opportunity | Dedicated peat path supported, with peat active in enriched runs | Dedicated peat in the canonical build, plus fuller carbon layers beyond peat if that remains part of the brief |
| Scenario-based scoring | `scenario_nature_first`, `scenario_balanced`, and `scenario_low_conflict` are implemented | Scenario refinement once richer evidence layers are added |
| Policy geography | LNRS slicing and summaries are supported in outputs | Bring policy geography further into interpretation or prioritisation logic, not just reporting |
| Shortlist outputs | Top-candidate exports, clustered zones, candidate brief, and map app | Regenerate polished outputs from the latest canonical run |
| Validation / robustness checks | Overlap, churn, sensitivity, and case-study style validation are in place | Full national enriched rerun once the final data stack is settled |
| Findings narrative | Technical report plus findings article now drafted | Add literature synthesis tied to the main findings |
| Delivery constraints | Not really implemented beyond the agricultural proxy | Ownership, tenure, designations, access, existing schemes, and local delivery constraints |
| Species-specific insight | Not implemented as species modelling | Species-specific or multi-taxon evidence if species claims are needed |
| Decision-ready rewilding tool | Partly there as a screening and teaching tool | Stronger ecological, policy, and delivery layers to move from shortlist tool to fuller decision-support tool |

In practice, that means the project is already strong enough to teach from and to support a literature-backed shortlist narrative. The main missing pieces are the layers that would let it carry stronger biodiversity, feasibility, and implementation claims.

## 5. Bottom Line

This enriched rerun makes the project stronger in three ways.

First, it shows that the pipeline can absorb better environmental signals and produce materially different results. Second, it demonstrates that those differences are interpretable rather than arbitrary. Third, it creates a better final product for a real audience: not a single brittle ranking, but a stable core shortlist plus scenario-led variants that reflect actual strategic choice.

For portfolio and hiring purposes, that is the most valuable story in the repo. It demonstrates geospatial engineering, model iteration, validation discipline, and the ability to turn technical outputs into decision-grade findings.

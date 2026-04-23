# Canonical v6 Findings

This page summarises the portfolio-level story from the `canonical_v6` run. It is written for readers who want the main lessons before opening the detailed methods, validation tables, or interactive explorer.

## 1. The model is best read as core plus variants

The canonical v6 validation found that `36` cells appear in the top 100 under all three scenario objectives. That shared core is the most defensible shortlist: cells that remain strong whether the model is viewed through nature-first, balanced, or lower-conflict priorities.

The variant sets are still useful. Nature-first and low-conflict diverge sharply, with only `36` shared cells and a Jaccard overlap of `0.22`. That is the point of the scenario design: it shows where objective choice changes the answer.

## 2. The v6 correction makes the shortlist more plausible

The v6 run corrected habitat-share scaling before restoration scoring. The leading balanced zones now have low to moderate habitat share rather than being dominated by existing habitat.

That matters because the model is trying to find restoration opportunity, not simply existing nature value. The top zones now better match the intended logic: near habitat, but with room for recovery.

## 3. Balanced opportunities are geographically clustered, but less concentrated than before

The balanced top 100 resolves into `11` candidate zones. The top three zones contain `42` of the 100 cells, so the model still finds coherent spatial clusters rather than isolated one-off cells.

The leading areas in the candidate brief are:

- Northern Eastern Zone, Nottinghamshire
- Southern Western Zone, Somerset
- Southwest Peninsula, Cornwall

This spread supports a more useful product story: the model surfaces a national shortlist that can be reviewed as candidate areas, not just individual hexes.

## 4. The model is robust to moderate reweighting

Sensitivity tests perturb flood, peat, and biodiversity weights by `+/-20%` while renormalising each scenario. The top-100 overlap remains high:

- Balanced: minimum overlap `91`
- Nature-first: minimum overlap `90`
- Low-conflict: minimum overlap `93`

That suggests the corrected v6 shortlist is not fragile to modest judgement calls about weights.

## 5. The strongest public claim is screening, not recommendation

The project is strongest when framed as a transparent spatial screening workflow. It identifies places worth closer review under different objectives, while explicitly avoiding claims about final site selection, predicted ecological outcomes, ownership, or delivery feasibility.

That makes it suitable as a decision-support prototype and portfolio project: it demonstrates geospatial data engineering, feature design, scenario modelling, validation, and product packaging without overclaiming.

## Where To Look Next

- Methods note: `outputs/methods.md`
- Candidate brief: `outputs/candidate_brief.md`
- Validation summary: `outputs/validation/validation_summary.md`
- Visual model: `docs/visual_model.md`
- Explorer app: `outputs/app/rewilding_opportunity_explorer.html`

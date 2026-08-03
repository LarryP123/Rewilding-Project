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

## 5. Registered BNG market activity does not track the model's top opportunity areas

To connect the model to a real policy mechanism, hex proximity to England's actual Biodiversity Gain Sites Register was checked against the balanced-scenario top 100. The register (312 sites nationally, via a daily-updated public mirror) records where developers are already buying off-site habitat-creation units — a live signal of where the BNG market is active today, not where ecological opportunity is highest.

Nationally, BNG activity is fairly widespread: `45.3%` of all scored hexes sit within 10km of a registered site, and `85.3%` within 20km. But the model's top 100 balanced candidates are not more likely to be near one than that baseline — only `40.0%` sit within 10km (vs `45.3%` nationally), and the correlation between the balanced suitability score and BNG proximity across all `204,703` hexes is essentially flat (`r = 0.10`).

The same check was repeated across all three scenario lenses, on the theory that low-conflict (which favours easy, lower-grade farmland) might line up better with real gain sites than nature-first. It does not — if anything, the opposite:

| Scenario | Correlation with BNG proximity | Top-100 within 10km |
| --- | --- | --- |
| Nature-first | `0.138` | `41.0%` |
| Balanced | `0.095` | `40.0%` |
| Low-conflict | `-0.010` | `35.0%` |

None of the three explain more than a couple of percent of the variation, and low-conflict — the one built to favour lower-friction agricultural land — has the weakest relationship of all. That rules out land-quality logic as the explanation.

So what does explain gain-site placement? Testing it directly rather than just speculating: distance from each hex to the nearest CORINE urban or industrial polygon was checked as a proxy for "where development, and therefore offset demand, already exists." That proxy explains BNG proximity roughly twice as well as any scenario lens does (`r = 0.267` vs `0.138` at best), and the pattern holds at the site level too — registered BNG sites sit consistently closer to urban/industrial land than the national baseline at every distance checked: `73.7%` of sites are within 2km of urban land, against `63.0%` of all hexes nationally (mean `1.59km` vs `2.02km`). The effect is real but modest, not overwhelming — England's urban/industrial land is already dense enough that the national baseline is high to begin with. Reproduce this with `python scripts/analyze_bng_alignment.py`, which also writes a timestamped record to `outputs/bng_alignment_tracking.jsonl` for tracking whether this shifts as the register grows.

That is a useful finding, not a null result: it suggests the current BNG market is placed more by proximity to existing development than by ecological or agricultural strategy, under any of the scenario framings tested here. The market is still young (mandatory BNG only began in February 2024, and 312 sites is an early snapshot), so this is worth rechecking as the register grows. For now, treat "ecologically promising" and "commercially active for BNG" as two separate questions this project can answer, not one.

Reproduce the core comparison with `python scripts/apply_bng_opportunity_score.py`.

## 6. The strongest public claim is screening, not recommendation

The project is strongest when framed as a transparent spatial screening workflow. It identifies places worth closer review under different objectives, while explicitly avoiding claims about final site selection, predicted ecological outcomes, ownership, or delivery feasibility.

That makes it suitable as a decision-support prototype and portfolio project: it demonstrates geospatial data engineering, feature design, scenario modelling, validation, and product packaging without overclaiming.

## Where To Look Next

- Methods note: `outputs/methods.md`
- Candidate brief: `outputs/candidate_brief.md`
- Validation summary: `outputs/validation/validation_summary.md`
- Visual model: `docs/visual_model.md`
- Explorer app: `outputs/app/rewilding_opportunity_explorer.html`
- BNG market-proximity script: `scripts/apply_bng_opportunity_score.py`

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

## 6. Real rewilding sites beat chance under low-conflict, but not under nature-first

The BNG check compares the model to a policy market. A different, arguably more direct question is whether the model rediscovers places rewilding practitioners have already chosen — not a market signal, but a genuine external validation, since these locations were never used to build or weight the model.

The Rewilding Network (Rewilding Britain's public directory of active rewilding projects) lists `89` sites across Britain. After excluding `3` the network deliberately obscures the location of and filtering to England, `64` real, precisely-located sites remain — a smaller sample than the BNG register, and worth reading with that in mind.

The top-100 result points the opposite way from BNG: the model's top candidates *are* closer to real rewilding sites than the national baseline, by a wide margin. Nationally only `3.6%` of hexes sit within 5km of a real site; the balanced top 100 reaches `13.0%` — over three times the baseline rate.

The sharper test is per-site: for the hex nearest each real project, what percentile does it fall at nationally under each scenario? A model with no relationship to real siting would average the 50th percentile by construction.

| Scenario | Mean percentile of nearest hex | Share in the model's top decile |
| --- | --- | --- |
| Nature-first | `50.1` | `9.4%` |
| Balanced | `53.5` | `10.9%` |
| Low-conflict | `60.5` | `15.6%` |

Nature-first lands almost exactly at chance — the purely ecological lens shows no edge at all. Low-conflict shows the clearest one: real sites are `1.5x` more likely than chance to fall in the model's own top decile under that lens specifically.

That lines up with the BNG finding rather than contradicting it. Both checks say the same thing from different data: real-world siting, whether a commercial BNG transaction or a genuine grassroots rewilding project, tracks practical and land-availability factors more than pure ecological optimisation. Nature-first is the model's best ecological argument and its weakest real-world predictor in both checks.

Reproduce this with `python scripts/analyze_rewilding_network_validation.py`.

## 7. The strongest public claim is screening, not recommendation

The project is strongest when framed as a transparent spatial screening workflow. It identifies places worth closer review under different objectives, while explicitly avoiding claims about final site selection, predicted ecological outcomes, ownership, or delivery feasibility.

That makes it suitable as a decision-support prototype and portfolio project: it demonstrates geospatial data engineering, feature design, scenario modelling, validation, and product packaging without overclaiming.

## Where To Look Next

- Methods note: `outputs/methods.md`
- Candidate brief: `outputs/candidate_brief.md`
- Validation summary: `outputs/validation/validation_summary.md`
- Visual model: `docs/visual_model.md`
- Explorer app: `outputs/app/rewilding_opportunity_explorer.html`
- BNG market-proximity script: `scripts/apply_bng_opportunity_score.py`
- Rewilding Network validation script: `scripts/analyze_rewilding_network_validation.py`

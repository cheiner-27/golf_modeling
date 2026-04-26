# Feature guide — `data/processed/features.csv`

One row per `(event_id_year, dg_id)`. 24,998 rows × 189 columns. Joins
1:1 to `event_table.csv` on the same two keys.

## How to read a column name

`{group}_{stat}_{window}[_agg]`

| Part | What it means |
|---|---|
| **group** | 3-letter prefix (`tgt_`, `ctx_`, `crs_`, `plr_`, `rcn_`, `rst_`, `exp_`, `res_`, `fld_`, `rel_`) — see groups below. |
| **stat** | Base column being aggregated. Usually a rounds-level stat (`sg_total`, `score_to_par`, `gir`, ...). For `fld_*` and `rel_*`, the stat keeps its source-group prefix because the feature is *of* a player-level feature — e.g. `fld_plr_sg_total_l24r_mean` is the field's mean of the player-level `plr_sg_total_l24r`. |
| **window** | Time/sample range. `l12r` = last 12 rounds, `l24r` = last 24 rounds, `l10e` = last 10 events, `l90d`/`l180d` = last N days, `career` = all prior history. |
| **agg** | `mean`, `std`, `med` (median), `z` (within-field z-score), `pct`, `corr`, `slope`. Omitted when only one aggregator makes sense for the stat. |

Examples:
- `plr_sg_total_l24r` — player's mean sg_total over their last 24 rounds (mean is the only sensible agg, so omitted).
- `rcn_top10_pct_l10e` — % of top-10 finishes over the player's last 10 events.
- `crs_sg_ott_corr_career` — correlation between sg_ott and round_score across all prior rounds at this course.
- `fld_plr_sg_total_l24r_std` — within-event std of `plr_sg_total_l24r` across all starters.
- `rel_plr_score_to_par_l12r_z` — z-score of `plr_score_to_par_l12r` for this player vs the event field.
- `res_finish_vs_exp_med_career` — historical median of (actual finish − expected finish) for this player.

## Leakage rule

Every aggregation is taken over data with `end_date < this row's start_date`.
Constructed by:
- `plr_*`/`rcn_*`/`rst_*`: per-player rolling/expanding aggregates with `.shift(1)`, snapshotted at the player's first round (round_num min) of the event.
- `crs_*`: per-course filtered to `end_date < start_date`, then rounds-weighted across the courses the player played in this event.
- `fld_*`: aggregate of per-starter `plr_*`/`rcn_*` (already leakage-safe) within event.
- `rel_*` and `exp_*` / `res_*`: derived from the above; all inputs are leakage-safe.
- `tgt_*` and `ctx_*`: target uses current-event score-rank (this is fine; targets aren't features). Field size is known pre-tee-off.

## Groups (turn on/off for ablation)

Programmatic spec: `reports/feature_groups.yaml`. Human summary:

| Prefix | Count | Description |
|---|---:|---|
| `tgt_` | 2 | Targets (`tgt_top10`, `tgt_score_to_par`). **Required for training; never use as features.** |
| `ctx_` | 1 | Event context (field size). |
| `crs_` | 11 | Course history at the courses the player played in this event. |
| `plr_` | 40 | Player history: career + last-12-round + last-24-round means of 13 stats, plus `plr_career_rounds`. |
| `rcn_` | 2 | Recent form (event-level): top-10 rate and SG slope over last 10 events. |
| `rst_` | 4 | Rust / cadence. |
| `exp_` | 1 | Expected finish from prior skill rank. |
| `res_` | 1 | Historical residual vs expectation. |
| `fld_` | 84 | Field's mean + std of every `plr_*`/`rcn_*` feature. **Constant within event.** |
| `rel_` | 42 | Player z-score vs field for every `plr_*`/`rcn_*` feature. |

Stable join keys (always kept): `event_id_year`, `dg_id`.

### Loading specific groups

```python
import yaml, pandas as pd

with open("reports/feature_groups.yaml") as f:
    spec = yaml.safe_load(f)

# E.g. train on plr + rel only:
keep = set(spec["keys"])
for g in ("tgt", "plr", "rel"):
    keep.update(spec["groups"][g].get("columns", []))
    # rel/fld use base_columns; expand to actual column names
    for base in spec["groups"][g].get("base_columns", []):
        if g == "rel":
            keep.add(f"rel_{base}_z")
        elif g == "fld":
            keep.add(f"fld_{base}_mean")
            keep.add(f"fld_{base}_std")

df = pd.read_csv("data/processed/features.csv", usecols=lambda c: c in keep)
```

## Known NaN sources (all expected; AutoGluon handles natively)

| Feature class | Why it can be NaN |
|---|---|
| All `plr_*` / `rcn_*` / `exp_*` / `rel_*` | Player has no prior real rounds (rookie debut). 518 such rows in current build. |
| `rst_days_since` / `rst_events_l*` / `rst_days_since_med_career` | Player's first event in dataset. |
| All `crs_*` | First post-2016 playing of this course (no prior history). 100% of 2016 rows + ~20% of later years. |
| `crs_sg_*_corr_career` | Course has fewer than 50 prior rounds (sample-size floor). |
| `res_finish_vs_exp_med_career` | Player has never both (a) had a defined `exp_finish_sg_career` and (b) survived the cut at a prior event. |
| `fld_*_std` | Edge: only one starter has a defined value for the underlying feature. |

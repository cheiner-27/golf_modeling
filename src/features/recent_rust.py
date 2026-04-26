"""
Recent (rcn_*) and rust (rst_*) features.

  rcn_top10_pct_l10e          — % of top-10 finishes in player's prior 10 events.
  rcn_sg_total_slope_l10e     — linear-regression slope of event-mean sg_total
                                over player's prior 10 events.
  rst_days_since              — days from prior event's end_date to this event's
                                start_date.
  rst_events_l90d / l180d     — count of player's events ending in the 90 / 180
                                days before this event's start_date.
  rst_days_since_med_career   — player's career median of rst_days_since.

Per-event, per-player history is built from rounds_imputed.csv across ALL
starters (not just event_table survivors); top10 status uses event_table's
total_score (so a player who didn't survive the drop filter is treated as
non-top-10 — the score-rank target rule).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import PROCESSED, RECENT_EVENTS, load_rounds


def _slope(x):
    v = pd.Series(x).dropna().values
    if len(v) < 2:
        return np.nan
    return float(np.polyfit(np.arange(len(v)), v, 1)[0])


def build() -> pd.DataFrame:
    """
    Returns all-starter rows. Orchestrator filters to event_table keys.
    """
    rounds_real = load_rounds()
    rounds_real = rounds_real[~rounds_real["is_imputed_round"].astype(bool)]

    per_ep = (
        rounds_real.groupby(
            ["event_id_year", "dg_id", "start_date", "end_date"], as_index=False
        ).agg(event_mean_sg_total=("sg_total", "mean"))
    )
    et = pd.read_csv(
        PROCESSED / "event_table.csv",
        usecols=["event_id_year", "dg_id", "total_score"],
    )
    per_ep = per_ep.merge(et, on=["event_id_year", "dg_id"], how="left")
    per_ep["finish_rank"] = (
        per_ep.groupby("event_id_year")["total_score"].rank(method="min", ascending=True)
    )
    per_ep["top10_flag"] = (
        (per_ep["finish_rank"] <= 10) & per_ep["total_score"].notna()
    ).astype("int8")

    per_ep = per_ep.sort_values(
        ["dg_id", "start_date", "event_id_year"], kind="mergesort"
    ).reset_index(drop=True)
    g = per_ep.groupby("dg_id", sort=False)

    per_ep["rcn_top10_pct_l10e"] = g["top10_flag"].transform(
        lambda s: s.shift(1).rolling(RECENT_EVENTS, min_periods=1).mean()
    )
    per_ep["rcn_sg_total_slope_l10e"] = g["event_mean_sg_total"].transform(
        lambda s: s.shift(1).rolling(RECENT_EVENTS, min_periods=2).apply(_slope, raw=False)
    )

    per_ep["prev_end"] = g["end_date"].shift(1)
    per_ep["rst_days_since"] = (
        (per_ep["start_date"] - per_ep["prev_end"]).dt.days
    )
    per_ep["rst_days_since_med_career"] = g["rst_days_since"].transform(
        lambda s: s.shift(1).expanding().median()
    )

    out_l90 = np.full(len(per_ep), np.nan)
    out_l180 = np.full(len(per_ep), np.nan)
    for _, sub in g:
        idxs = sub.index.values
        starts = sub["start_date"].values.astype("datetime64[D]")
        ends = sub["end_date"].values.astype("datetime64[D]")
        end_sorted = np.sort(ends)
        for k, row_i in enumerate(idxs):
            s = starts[k]
            for days, out in ((90, out_l90), (180, out_l180)):
                cutoff = s - np.timedelta64(days, "D")
                out[row_i] = (
                    np.searchsorted(end_sorted, s, side="left")
                    - np.searchsorted(end_sorted, cutoff, side="left")
                )
    per_ep["rst_events_l90d"] = out_l90
    per_ep["rst_events_l180d"] = out_l180

    keep = [
        "event_id_year", "dg_id",
        "rcn_top10_pct_l10e", "rcn_sg_total_slope_l10e",
        "rst_days_since", "rst_events_l90d", "rst_events_l180d",
        "rst_days_since_med_career",
    ]
    return per_ep[keep].reset_index(drop=True)

"""
Player history features (plr_*).

  plr_career_rounds         — count of prior real rounds (excludes imputed).
  plr_{stat}_career         — expanding mean over all prior rounds.
  plr_{stat}_l12r           — rolling mean over the prior 12 rounds.
  plr_{stat}_l24r           — rolling mean over the prior 24 rounds.

`stat` ranges over base.STATS (sg_*, driving_*, gir, scrambling, prox_*,
score_to_par).

Leakage: rounds are sorted per player by (start_date, round_num); rolling
and expanding windows are shifted by one before the snapshot is taken at
the player's first round (round_num == min) of each event, so every value
reflects only rounds that ENDED before this event's start_date.

Imputed rounds are excluded from history aggregations — they were
synthesized for total-score consistency, not as real performance.
"""

from __future__ import annotations

import pandas as pd

from .base import ROUND_WINDOWS, STATS, load_rounds


def build() -> pd.DataFrame:
    """
    Returns all-starter rows (one per (event, player) for everyone in
    rounds_imputed.csv post-2016, non-Zurich). The orchestrator filters
    to event_table keys for the final features.csv; field aggregates
    consume the all-starter frame directly.
    """
    rounds = load_rounds()
    rounds = rounds[~rounds["is_imputed_round"].astype(bool)].copy()
    rounds = rounds.sort_values(
        ["dg_id", "start_date", "event_id_year", "round_num"], kind="mergesort"
    ).reset_index(drop=True)

    rounds["plr_career_rounds"] = rounds.groupby("dg_id").cumcount()

    g = rounds.groupby("dg_id", sort=False)
    for stat in STATS:
        s = g[stat]
        rounds[f"plr_{stat}_career"] = s.transform(
            lambda x: x.shift(1).expanding().mean()
        )
        for tag, n in ROUND_WINDOWS.items():
            rounds[f"plr_{stat}_{tag}"] = s.transform(
                lambda x, n=n: x.shift(1).rolling(n, min_periods=1).mean()
            )

    feat_cols = ["plr_career_rounds"] + [
        f"plr_{stat}_{w}"
        for stat in STATS
        for w in ("career", *ROUND_WINDOWS.keys())
    ]
    first_idx = rounds.groupby(["event_id_year", "dg_id"])["round_num"].idxmin()
    return rounds.loc[first_idx, ["event_id_year", "dg_id", *feat_cols]].reset_index(drop=True)

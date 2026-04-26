"""
Event-context features (ctx_*).

  ctx_field_size  — count of distinct dg_id with any round in this event
                    (taken from rounds_imputed.csv, so MC players count).
                    Known pre-tournament; not subject to leakage.
"""

from __future__ import annotations

import pandas as pd

from .base import load_rounds, load_target_index


def build() -> pd.DataFrame:
    rounds = load_rounds()
    field = (
        rounds.groupby("event_id_year")["dg_id"].nunique()
        .rename("ctx_field_size").reset_index()
    )
    t = load_target_index()[["event_id_year", "dg_id"]]
    return t.merge(field, on="event_id_year", how="left")

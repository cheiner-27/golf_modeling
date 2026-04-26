"""
Field aggregate features (fld_*).

For every event, summarises the FULL starter pool's plr_*/rcn_* features.
Output columns:

  fld_{plr_or_rcn_col}_mean
  fld_{plr_or_rcn_col}_std

The aggregation is over all starters in the event (all dg_ids with any
round in rounds_imputed.csv for that event), not just event_table
survivors. crs_* and rst_* are not aggregated:
  - crs_* is constant across the field by construction.
  - rst_* describes the player's own scheduling pattern; its field-mean
    isn't a useful comparison.
"""

from __future__ import annotations

import pandas as pd


def build(per_starter: pd.DataFrame) -> pd.DataFrame:
    """
    `per_starter` must be a DataFrame keyed by (event_id_year, dg_id) with
    plr_* / rcn_* columns merged in (one row per starter, per event).
    Returns one row per event_id_year with fld_*_mean / fld_*_std columns.
    """
    base_cols = [c for c in per_starter.columns if c.startswith(("plr_", "rcn_"))]
    g = per_starter.groupby("event_id_year")
    pieces = {}
    for col in base_cols:
        pieces[f"fld_{col}_mean"] = g[col].mean()
        pieces[f"fld_{col}_std"] = g[col].std()
    return pd.DataFrame(pieces).reset_index()

"""
Player-vs-field z-scores (rel_*).

For each plr_*/rcn_* column on a starter, compute:

  rel_{col}_z = (player_value - fld_{col}_mean) / fld_{col}_std

Field mean/std include the player themselves (standard within-field
normalization; the leave-one-out delta is <1% with ~150-player fields).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def build(per_starter: pd.DataFrame, fld: pd.DataFrame) -> pd.DataFrame:
    base_cols = [c for c in per_starter.columns if c.startswith(("plr_", "rcn_"))]
    merged = per_starter.merge(fld, on="event_id_year", how="left")
    out = merged[["event_id_year", "dg_id"]].copy()
    for col in base_cols:
        std = merged[f"fld_{col}_std"].replace(0, np.nan)
        out[f"rel_{col}_z"] = (merged[col] - merged[f"fld_{col}_mean"]) / std
    return out

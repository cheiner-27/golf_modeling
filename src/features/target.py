"""
Target features (tgt_*).

  tgt_top10         — 1 if score-rank within event is <= 10 (ties via
                      method='min', so a four-way T8 all sit at rank 8
                      and all qualify as top-10).
  tgt_score_to_par  — total_score - total_course_par for the event.
                      Negative = under par. Scales correctly for 3-round
                      survivors (par sum is per-round so the comparison
                      stays fair).
"""

from __future__ import annotations

import pandas as pd

from .base import PROCESSED


def build() -> pd.DataFrame:
    et = pd.read_csv(
        PROCESSED / "event_table.csv",
        usecols=["event_id_year", "dg_id", "total_score", "total_course_par"],
    )
    et["finish_rank"] = (
        et.groupby("event_id_year")["total_score"].rank(method="min", ascending=True)
    )
    et["tgt_top10"] = (et["finish_rank"] <= 10).astype("int8")
    et["tgt_score_to_par"] = et["total_score"] - et["total_course_par"]
    return et[["event_id_year", "dg_id", "tgt_top10", "tgt_score_to_par"]]

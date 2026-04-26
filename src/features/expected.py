"""
Expected/residual features (exp_*, res_*).

  exp_finish_sg_career             — within-event rank of the player by
                                     plr_sg_total_career (better SG = better
                                     rank = lower number).
  res_finish_vs_exp_med_career     — player's historical median of
                                     (actual_finish - exp_finish_sg_career).
                                     Pulled only from events the player
                                     survived (where actual_finish is defined).

Leakage: plr_sg_total_career is itself an as-of-event-start aggregate.
The residual feature uses .shift(1).expanding().median() per player, so
the value for event E is the median over events strictly before E.
"""

from __future__ import annotations

import pandas as pd

from .base import PROCESSED, load_events


def build(per_starter: pd.DataFrame) -> pd.DataFrame:
    df = per_starter[["event_id_year", "dg_id", "plr_sg_total_career"]].copy()
    df["exp_finish_sg_career"] = (
        df.groupby("event_id_year")["plr_sg_total_career"]
        .rank(method="min", ascending=False)
    )

    et = pd.read_csv(
        PROCESSED / "event_table.csv",
        usecols=["event_id_year", "dg_id", "total_score"],
    )
    et["actual_finish"] = (
        et.groupby("event_id_year")["total_score"].rank(method="min", ascending=True)
    )
    df = df.merge(
        et[["event_id_year", "dg_id", "actual_finish"]],
        on=["event_id_year", "dg_id"], how="left",
    )
    df["residual"] = df["actual_finish"] - df["exp_finish_sg_career"]

    df = df.merge(
        load_events()[["event_id_year", "start_date"]],
        on="event_id_year", how="left",
    )
    df = df.sort_values(
        ["dg_id", "start_date", "event_id_year"], kind="mergesort"
    ).reset_index(drop=True)
    df["res_finish_vs_exp_med_career"] = (
        df.groupby("dg_id", sort=False)["residual"]
        .transform(lambda s: s.shift(1).expanding().median())
    )

    return df[
        ["event_id_year", "dg_id",
         "exp_finish_sg_career", "res_finish_vs_exp_med_career"]
    ]

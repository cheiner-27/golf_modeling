#!/usr/bin/env python3
"""
Builds rounds_imputed.csv from rounds.csv by inserting synthetic rows for
players who survived the event_table drop filter but played fewer rounds
than the event total (in practice: WD-after-R3 players in 4-round events).

Imputed values:
  - All per-round numeric stats (round_score, sg_*, driving_*, gir, scrambling,
    prox_*, shot/score-class counts) are filled with the player's mean across
    their other rounds in that event.
  - course_key + course_par are copied from the player's most-played course
    for that event (handles multi-course events).
  - round_num is filled to whichever round number(s) the player was missing.
  - fin_text / start_hole / teetime stay NaN — not used downstream.
  - is_imputed_round is True for synthetic rows, False for real ones.

Output:
  data/processed/rounds_imputed.csv

Run with: python src/impute_rounds.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"

MIN_YEAR = 2016
DROP_EVENTS = {"18_2023", "18_2025"}  # Zurich Classic (team format)

# A round is "stat-null" if any of these is missing — same definition the
# event_table drop filter uses.
STAT_COLS = [
    "sg_putt", "sg_arg", "sg_app", "sg_ott", "sg_t2g",
    "driving_dist", "driving_acc", "gir", "scrambling",
    "prox_rgh", "prox_fw",
]

# Numeric per-round columns mean-imputed when synthesizing a missing round.
NUMERIC_COLS = [
    "round_score",
    "sg_putt", "sg_arg", "sg_app", "sg_ott", "sg_t2g", "sg_total",
    "driving_dist", "driving_acc", "gir", "scrambling",
    "prox_rgh", "prox_fw",
    "great_shots", "poor_shots",
    "eagles_or_better", "birdies", "pars", "bogies", "doubles_or_worse",
]

# Subset of NUMERIC_COLS that are integer-valued in the source data; rounded
# after mean imputation so the model doesn't learn imputation-driven decimals.
INT_COLS = [
    "round_score",
    "great_shots", "poor_shots",
    "eagles_or_better", "birdies", "pars", "bogies", "doubles_or_worse",
]


def main() -> None:
    print("=== Building rounds_imputed.csv ===\n")

    rounds = pd.read_csv(PROCESSED / "rounds.csv", low_memory=False)
    rounds["is_imputed_round"] = False

    # Universe we operate on — pre-2016 rows and dropped events are passed
    # through unchanged (no imputation, no removal).
    work = rounds[
        (rounds["year"] >= MIN_YEAR) & (~rounds["event_id_year"].isin(DROP_EVENTS))
    ].copy()
    work["stat_null"] = work[STAT_COLS].isna().any(axis=1)

    per_player = (
        work.groupby(["event_id_year", "dg_id"], as_index=False)
        .agg(
            rounds_played=("round_num", "size"),
            stat_null_rounds=("stat_null", "sum"),
        )
    )
    survivors = per_player[
        (per_player["rounds_played"] > 2) & (per_player["stat_null_rounds"] < 2)
    ]

    num_rounds_event = (
        work.groupby("event_id_year")["round_num"].max().rename("num_rounds_event")
    )
    survivors = survivors.merge(num_rounds_event, on="event_id_year")

    needs_imp = survivors[survivors["rounds_played"] < survivors["num_rounds_event"]]
    print(f"  player-events needing imputation: {len(needs_imp):,}")

    # Index work for fast lookup per (event, player).
    work_idx = work.set_index(["event_id_year", "dg_id"]).sort_index()

    imp_rows = []
    for _, row in needs_imp.iterrows():
        key = (row["event_id_year"], row["dg_id"])
        played = work_idx.loc[[key]]
        n_total = int(row["num_rounds_event"])

        played_rounds = set(played["round_num"].astype(int))
        missing = [r for r in range(1, n_total + 1) if r not in played_rounds]

        means = played[NUMERIC_COLS].mean()
        primary_course = played["course_key"].mode().iloc[0]
        primary_par = played.loc[played["course_key"] == primary_course, "course_par"].iloc[0]
        event_id = played["event_id"].iloc[0]
        year = played["year"].iloc[0]

        for r_num in missing:
            new_row = {col: np.nan for col in rounds.columns}
            new_row["event_id_year"] = row["event_id_year"]
            new_row["event_id"] = event_id
            new_row["year"] = year
            new_row["dg_id"] = row["dg_id"]
            new_row["round_num"] = r_num
            new_row["course_key"] = primary_course
            new_row["course_par"] = primary_par
            new_row["is_imputed_round"] = True
            for col in NUMERIC_COLS:
                val = means[col]
                if col in INT_COLS:
                    val = float(np.round(val))
                new_row[col] = val
            imp_rows.append(new_row)

    imp_df = pd.DataFrame(imp_rows, columns=rounds.columns)
    out = pd.concat([rounds, imp_df], ignore_index=True)
    out = out.sort_values(
        ["year", "event_id", "dg_id", "round_num"], kind="mergesort"
    ).reset_index(drop=True)

    path = PROCESSED / "rounds_imputed.csv"
    out.to_csv(path, index=False)
    print(f"\n  saved -> data/processed/rounds_imputed.csv  "
          f"({len(out):,} rows total, {len(imp_df):,} imputed)")
    print("\n=== Done ===")


if __name__ == "__main__":
    main()

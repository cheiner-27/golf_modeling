"""
Shared loaders + constants for the feature pipeline.

Two canonical frames the rest of the package depends on:

  - rounds:  rounds_imputed.csv enriched with per-round score_to_par,
             event start_date, and end_date. One row per (event, player, round).
             Includes EVERY starter (MC players too) so field-level
             aggregates can read off the full field.

  - events:  one row per event_id_year with start_date, end_date,
             course_key (primary), num_rounds_event.

  - target_index:  the (event_id_year, dg_id) keys we emit features for —
             pulled from event_table.csv. Every feature module returns
             a frame indexed by these keys (with NaN allowed).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROCESSED = Path(__file__).resolve().parents[2] / "data" / "processed"

# Stat columns the feature pipeline aggregates. score_to_par is computed
# on the fly in load_rounds so it's available alongside the raw stats.
STATS = [
    "sg_putt", "sg_arg", "sg_app", "sg_ott", "sg_t2g", "sg_total",
    "driving_dist", "driving_acc", "gir", "scrambling",
    "prox_rgh", "prox_fw",
    "score_to_par",
]

# Strokes-gained categories used for course-correlation features.
SG_CATS = ["sg_putt", "sg_arg", "sg_app", "sg_ott", "sg_t2g", "sg_total"]

# Rolling windows (in rounds) for plr_* features.
ROUND_WINDOWS = {"l12r": 12, "l24r": 24}

# Recent-event window (in events) for rcn_* features.
RECENT_EVENTS = 10


def load_events() -> pd.DataFrame:
    e = pd.read_csv(PROCESSED / "event_table.csv", parse_dates=["start_date", "end_date"])
    return (
        e[["event_id_year", "event_id", "year", "start_date", "end_date",
           "num_rounds_event", "course_key"]]
        .drop_duplicates("event_id_year")
        .sort_values("start_date")
        .reset_index(drop=True)
    )


def load_rounds() -> pd.DataFrame:
    """
    rounds_imputed.csv joined to event start/end dates, with score_to_par.
    One row per (event, player, round). Includes ALL starters in each event.
    """
    r = pd.read_csv(PROCESSED / "rounds_imputed.csv", low_memory=False)
    e = load_events()[["event_id_year", "start_date", "end_date"]]
    r = r.merge(e, on="event_id_year", how="inner")  # drops pre-2016 / Zurich
    r["score_to_par"] = r["round_score"] - r["course_par"]
    return r.sort_values(["dg_id", "end_date", "round_num"]).reset_index(drop=True)


def load_target_index() -> pd.DataFrame:
    """
    The (event_id_year, dg_id) rows the final features.csv emits.
    Carries event_id, year, start_date, end_date so feature modules can
    use them without reloading.
    """
    t = pd.read_csv(
        PROCESSED / "event_table.csv",
        parse_dates=["start_date", "end_date"],
        usecols=["event_id_year", "event_id", "year", "dg_id",
                 "start_date", "end_date", "course_key", "num_rounds_event"],
    )
    return t.sort_values(["start_date", "event_id_year", "dg_id"]).reset_index(drop=True)


def load_weather() -> pd.DataFrame:
    w = pd.read_csv(PROCESSED / "weather.csv", parse_dates=["date"])
    return w


def keys(df: pd.DataFrame) -> pd.DataFrame:
    return df[["event_id_year", "dg_id"]].copy()

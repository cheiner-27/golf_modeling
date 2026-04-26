#!/usr/bin/env python3
"""
Builds the per-(event, player) training table from the four processed tables.

Output (data/processed/):
  event_table.csv  — one row per (event_id_year, dg_id)

Pipeline:
  1. Filter rounds to year >= 2016 and drop the Zurich Classic team-format
     events (18_2023, 18_2025) where every round_score is null.
  2. For each (event, player), drop the row if the player played <= 2 rounds
     OR if >= 2 of their rounds are missing detailed stats. rounds.csv itself
     is left untouched so field-size features later can still see everyone.
  3. Aggregate kept (event, player) rows: rounds_played, total_score,
     total_course_par. total_course_par sums per-round par so it scales with
     however many rounds the player actually finished.
  4. Backfill missing start_date as end_date - (num_rounds - 1) days,
     assuming one round per day with all players on the same day.
  5. Aggregate weather over the playing-day window. weather.csv is keyed by
     (event_id_year, course_key, date); grouping by event_id_year alone
     collapses multi-course events into a single row.

Run with: python src/build_event_table.py
"""

from pathlib import Path

import pandas as pd

PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"

MIN_YEAR = 2016
DROP_EVENTS = {"18_2023", "18_2025"}  # Zurich Classic (team format)

# Detailed stat columns. A round is "stat-null" if any of these is missing.
# sg_total has older coverage so it isn't part of this signal.
STAT_COLS = [
    "sg_putt", "sg_arg", "sg_app", "sg_ott", "sg_t2g",
    "driving_dist", "driving_acc", "gir", "scrambling",
    "prox_rgh", "prox_fw",
]


def load_rounds() -> pd.DataFrame:
    """
    Reads rounds_imputed.csv (built by src/impute_rounds.py), which adds
    synthetic rows for WD-after-R3 players so total_score scales with the
    full event length.
    """
    rounds = pd.read_csv(PROCESSED / "rounds_imputed.csv", low_memory=False)
    rounds = rounds[rounds["year"] >= MIN_YEAR]
    rounds = rounds[~rounds["event_id_year"].isin(DROP_EVENTS)]
    return rounds.copy()


def aggregate_player_rounds(rounds: pd.DataFrame) -> pd.DataFrame:
    """
    One row per (event_id_year, dg_id) after dropping players with too few
    rounds or too many stat-blank rounds.
    """
    r = rounds.copy()
    r["stat_null"] = r[STAT_COLS].isna().any(axis=1)

    agg = (
        r.groupby(["event_id_year", "event_id", "year", "dg_id"], as_index=False)
        .agg(
            rounds_played=("round_score", "size"),
            stat_null_rounds=("stat_null", "sum"),
            total_score=("round_score", "sum"),
            total_course_par=("course_par", "sum"),
        )
    )

    before = len(agg)
    keep = (agg["rounds_played"] > 2) & (agg["stat_null_rounds"] < 2)
    agg = agg[keep].drop(columns=["stat_null_rounds"]).reset_index(drop=True)
    print(f"  player-events: {before:,} -> {len(agg):,} "
          f"(dropped {before - len(agg):,} for <=2 rounds or >=2 stat-null rounds)")
    return agg


def build_event_dates(rounds: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """
    Per event: course_key, end_date (= event_completed), num_rounds_event
    (max round_num), and start_date (backfilled when missing as
    end_date - (num_rounds - 1) days).
    """
    num_rounds = (
        rounds.groupby("event_id_year")["round_num"].max()
        .rename("num_rounds_event").reset_index()
    )

    ev = events[["event_id_year", "start_date", "event_completed", "course_key"]].copy()
    ev["start_date"] = pd.to_datetime(ev["start_date"], errors="coerce")
    ev["end_date"] = pd.to_datetime(ev["event_completed"], errors="coerce")
    ev = ev.merge(num_rounds, on="event_id_year", how="inner")

    needs_fill = ev["start_date"].isna() & ev["end_date"].notna()
    ev.loc[needs_fill, "start_date"] = (
        ev.loc[needs_fill, "end_date"]
        - pd.to_timedelta(ev.loc[needs_fill, "num_rounds_event"] - 1, unit="D")
    )
    print(f"  start_date backfilled for {needs_fill.sum()} events")

    return ev[["event_id_year", "course_key", "start_date", "end_date", "num_rounds_event"]]


def aggregate_weather(weather: pd.DataFrame, ev: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate weather over the playing-day window [start_date, end_date].

    Grouping by event_id_year alone collapses multi-course events; daily
    rows from each course are pooled before computing summary stats.
    """
    w = weather.copy()
    w["date"] = pd.to_datetime(w["date"])
    w = w.merge(ev[["event_id_year", "start_date", "end_date"]], on="event_id_year", how="inner")
    w = w[(w["date"] >= w["start_date"]) & (w["date"] <= w["end_date"])]

    g = w.groupby("event_id_year")
    out = pd.DataFrame({
        "precip_total_mm":     g["precipitation_mm"].sum(),
        "precip_max_daily_mm": g["precipitation_mm"].max(),
        "temp_max_c":          g["temperature_mean_c"].max(),
        "temp_min_c":          g["temperature_mean_c"].min(),
        "temp_mean_c":         g["temperature_mean_c"].mean(),
        "temp_std_c":          g["temperature_mean_c"].std(),
        "wind_max_kmh":        g["wind_speed_max_kmh"].max(),
        "wind_min_kmh":        g["wind_speed_max_kmh"].min(),
        "wind_mean_kmh":       g["wind_speed_max_kmh"].mean(),
        "wind_std_kmh":        g["wind_speed_max_kmh"].std(),
        "humidity_max_pct":    g["relative_humidity_pct"].max(),
        "humidity_min_pct":    g["relative_humidity_pct"].min(),
        "humidity_mean_pct":   g["relative_humidity_pct"].mean(),
        "humidity_std_pct":    g["relative_humidity_pct"].std(),
    }).reset_index()
    return out


def build_event_table() -> pd.DataFrame:
    print("Loading rounds ...")
    rounds = load_rounds()

    print("Aggregating player rounds ...")
    player_agg = aggregate_player_rounds(rounds)

    print("Building event dates ...")
    events = pd.read_csv(PROCESSED / "events.csv")
    ev_dates = build_event_dates(rounds, events)

    print("Aggregating weather ...")
    weather = pd.read_csv(PROCESSED / "weather.csv")
    weather_agg = aggregate_weather(weather, ev_dates)

    print("Joining ...")
    courses = pd.read_csv(PROCESSED / "courses.csv")
    event_meta = ev_dates.merge(courses[["course_key", "country"]], on="course_key", how="left")

    out = (
        player_agg
        .merge(event_meta, on="event_id_year", how="inner")
        .merge(weather_agg, on="event_id_year", how="left")
    )

    cols = [
        "event_id_year", "event_id", "year", "dg_id",
        "start_date", "end_date", "num_rounds_event",
        "course_key", "country",
        "rounds_played", "total_score", "total_course_par",
        "precip_total_mm", "precip_max_daily_mm",
        "temp_max_c", "temp_min_c", "temp_mean_c", "temp_std_c",
        "wind_max_kmh", "wind_min_kmh", "wind_mean_kmh", "wind_std_kmh",
        "humidity_max_pct", "humidity_min_pct", "humidity_mean_pct", "humidity_std_pct",
    ]
    return out[cols].sort_values(["year", "event_id", "dg_id"]).reset_index(drop=True)


def main() -> None:
    print("=== Building event_table.csv ===\n")
    df = build_event_table()
    path = PROCESSED / "event_table.csv"
    df.to_csv(path, index=False)
    print(f"\n  saved -> data/processed/event_table.csv  "
          f"({len(df):,} rows, {df['event_id_year'].nunique()} events)")
    print("\n=== Done ===")


if __name__ == "__main__":
    main()

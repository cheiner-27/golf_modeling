#!/usr/bin/env python3
"""
Builds four normalized tables from raw DataGolf data.

Output (data/processed/):
  players.csv  — one row per player
  courses.csv  — one row per course, with location
  events.csv   — one row per tournament-year
  rounds.csv   — one row per player × round

Run with: python src/process.py
"""

import pandas as pd
from pathlib import Path

RAW       = Path(__file__).resolve().parents[1] / "data" / "raw"
PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)


def save(df: pd.DataFrame, name: str) -> None:
    path = PROCESSED / name
    df.to_csv(path, index=False)
    print(f"  saved -> data/processed/{name}  ({len(df):,} rows)")


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_rounds_raw() -> pd.DataFrame:
    """Concatenate all historical round CSVs into one DataFrame."""
    dfs = []
    for f in sorted((RAW / "historical" / "rounds").glob("rounds_pga_*.csv")):
        dfs.append(pd.read_csv(f, low_memory=False))
    return pd.concat(dfs, ignore_index=True)


def load_schedules() -> pd.DataFrame:
    """Concatenate all schedule CSVs and parse start_date."""
    dfs = []
    for f in sorted((RAW / "schedule").glob("schedule_pga_*.csv")):
        dfs.append(pd.read_csv(f))
    df = pd.concat(dfs, ignore_index=True)
    df["start_date"] = pd.to_datetime(df["start_date"])
    return df


# ── Table builders ─────────────────────────────────────────────────────────────

def build_players() -> pd.DataFrame:
    """
    One row per player.
    Source: players/player_list.csv
    """
    df = pd.read_csv(RAW / "players" / "player_list.csv")
    df = (
        df[["dg_id", "player_name", "country", "country_code", "amateur"]]
        .drop_duplicates("dg_id")
        .sort_values("dg_id")
        .reset_index(drop=True)
    )
    return df


def build_courses() -> pd.DataFrame:
    """
    One row per course.
    Course names/keys come from rounds (full history).
    Location (lat/lon, city, country) joined from schedule files.
    """
    rounds = load_rounds_raw()

    # All unique courses that appear in historical rounds
    courses = (
        rounds[["course_num", "course_name"]]
        .drop_duplicates("course_num")
        .rename(columns={"course_num": "course_key"})
    )

    # Location data from schedule files (2024-2026 covers nearly all courses).
    # Multi-course events store keys as "704;202;233" — explode to one row per course.
    schedule = load_schedules()
    sched_loc = schedule[["course_key", "course", "location", "country", "latitude", "longitude"]].copy()
    sched_loc["course_key"] = sched_loc["course_key"].astype(str).str.split(";")
    sched_loc["course"]     = sched_loc["course"].astype(str).str.split(";")
    sched_loc = sched_loc.explode(["course_key", "course"])
    sched_loc["course_key"] = pd.to_numeric(sched_loc["course_key"], errors="coerce")
    sched_loc = sched_loc.dropna(subset=["course_key"])
    sched_loc["course_key"] = sched_loc["course_key"].astype(int)
    location = sched_loc[["course_key", "location", "country", "latitude", "longitude"]].drop_duplicates("course_key")

    # Manual supplement for courses not covered by recent schedules
    supplement = pd.read_csv(RAW / "course_coords_supplement.csv")
    supplement["course_key"] = supplement["course_key"].astype(int)
    location = pd.concat([location, supplement], ignore_index=True).drop_duplicates("course_key")

    courses = (
        courses
        .merge(location, on="course_key", how="left")
        .sort_values("course_key")
        .reset_index(drop=True)
    )
    return courses[["course_key", "course_name", "location", "country", "latitude", "longitude"]]


def build_events() -> pd.DataFrame:
    """
    One row per tournament-year.
    Core fields (event_id, year, event_name) come from rounds.
    start_date, status, winner joined from schedule where available.
    course_key derived from the primary (round 1) course in rounds data.
    """
    rounds = load_rounds_raw()

    # Unique event occurrences from rounds
    event_cols = ["event_id", "year", "season", "event_name", "tour", "event_completed"]
    events = (
        rounds[event_cols]
        .drop_duplicates(["event_id", "year"])
    )
    events["event_completed"] = pd.to_datetime(events["event_completed"])

    # Primary course per event: course played in round 1 (or first available)
    primary_course = (
        rounds.sort_values("round_num")
        .drop_duplicates(["event_id", "year"])
        [["event_id", "year", "course_num"]]
        .rename(columns={"course_num": "course_key"})
    )
    events = events.merge(primary_course, on=["event_id", "year"], how="left")

    # Enrich from schedule: start_date, status, winner
    schedule = load_schedules()
    schedule["year"] = schedule["start_date"].dt.year
    # Take only first course_key for multi-course events so it casts cleanly
    schedule["course_key"] = (
        schedule["course_key"].astype(str).str.split(";").str[0]
    )
    schedule["course_key"] = pd.to_numeric(schedule["course_key"], errors="coerce")
    schedule_slim = schedule[["event_id", "year", "start_date", "status", "winner"]]
    events = events.merge(schedule_slim, on=["event_id", "year"], how="left")

    events = events.sort_values(["year", "event_id"]).reset_index(drop=True)
    events["event_id_year"] = events["event_id"].astype(str) + "_" + events["year"].astype(str)
    return events[[
        "event_id_year", "event_id", "year", "season", "event_name", "tour",
        "start_date", "event_completed", "course_key", "status", "winner",
    ]]


def build_rounds() -> pd.DataFrame:
    """
    One row per player × round.
    Redundant event/player/course descriptor columns are dropped — join
    to the other tables via event_id+year (events), dg_id (players),
    course_key (courses).
    """
    rounds = load_rounds_raw()
    rounds = rounds.rename(columns={"course_num": "course_key"})

    # Drop columns that live in other tables
    drop_cols = ["tour", "season", "event_completed", "event_name",
                 "player_name", "course_name"]
    rounds = rounds.drop(columns=[c for c in drop_cols if c in rounds.columns])

    rounds["event_id_year"] = rounds["event_id"].astype(str) + "_" + rounds["year"].astype(str)
    rounds = rounds.sort_values(["year", "event_id", "dg_id", "round_num"]).reset_index(drop=True)
    return rounds[[
        "event_id_year", "event_id", "year", "dg_id", "round_num", "course_key", "course_par",
        "fin_text", "start_hole", "teetime", "round_score",
        "sg_putt", "sg_arg", "sg_app", "sg_ott", "sg_t2g", "sg_total",
        "driving_dist", "driving_acc", "gir", "scrambling", "prox_rgh", "prox_fw",
        "great_shots", "poor_shots",
        "eagles_or_better", "birdies", "pars", "bogies", "doubles_or_worse",
    ]]


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=== Building processed tables ===\n")

    print("Players ...")
    save(build_players(), "players.csv")

    print("Courses ...")
    save(build_courses(), "courses.csv")

    print("Events ...")
    save(build_events(), "events.csv")

    print("Rounds ...")
    save(build_rounds(), "rounds.csv")

    print("\n=== Done ===")


if __name__ == "__main__":
    main()

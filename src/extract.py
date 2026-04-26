#!/usr/bin/env python3
"""
DataGolf API data extraction script.

Fetches and saves to data/raw/:
  - Player data: player list, DG rankings, skill ratings
  - Schedule / course: PGA schedule, field updates
  - Historical event lists: raw-data and odds (needed for downstream pulls)
  - Historical raw rounds: round scoring/SG by year (2017–2026)
  - Historical odds: outrights (FanDuel + DraftKings, 2019–2025)

Rate limit: 45 requests/min — enforced via RateLimiter. Exceeding causes a 5-min suspension.
"""

import os
import time
from collections import deque
from pathlib import Path

import requests
from dotenv import load_dotenv

# ── Config ─────────────────────────────────────────────────────────────────────

load_dotenv()
API_KEY = os.environ["DATAGOLF_API_KEY"]
BASE_URL = "https://feeds.datagolf.com"
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

# Adjust these to control the scope of historical pulls
HIST_TOURS = ["pga"]
ROUNDS_YEARS = list(range(2004, 2027))   # PGA Tour round data available from 2004
ODDS_YEARS   = list(range(2019, 2026))   # historical odds available 2019–2025

OUTRIGHT_MARKETS = ["win", "top_5", "top_10", "top_20", "make_cut"]
ODDS_BOOKS       = ["draftkings", "fanduel"]


# ── Rate limiter ───────────────────────────────────────────────────────────────

class RateLimiter:
    """
    Enforces at most `limit` calls per 60 seconds (sliding window) AND a minimum
    `min_interval` seconds between consecutive requests (~40 req/min at 1.5s).
    The interval floor is the primary guard; the window cap is a backstop.
    """

    def __init__(self, limit: int = 40, min_interval: float = 1.5):
        self.limit = limit
        self.min_interval = min_interval
        self._timestamps: deque = deque()
        self._last: float = 0.0

    def wait(self):
        # Enforce minimum gap between requests
        now = time.monotonic()
        gap = now - self._last
        if gap < self.min_interval:
            time.sleep(self.min_interval - gap)
            now = time.monotonic()

        # Sliding-window backstop
        while self._timestamps and now - self._timestamps[0] > 60.0:
            self._timestamps.popleft()
        if len(self._timestamps) >= self.limit:
            sleep_for = 60.0 - (now - self._timestamps[0]) + 0.1
            if sleep_for > 0:
                print(f"  [rate limit] sleeping {sleep_for:.1f}s …")
                time.sleep(sleep_for)
            now = time.monotonic()

        self._last = now
        self._timestamps.append(now)


_limiter = RateLimiter(45)


# ── HTTP / IO helpers ──────────────────────────────────────────────────────────

def get(endpoint: str, params: dict | None = None) -> str:
    """Rate-limited GET; returns raw response text (CSV). Raises HTTPError on non-2xx."""
    _limiter.wait()
    p = dict(params or {})
    p["key"] = API_KEY
    p["file_format"] = "csv"
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    resp = requests.get(url, params=p, timeout=30)
    resp.raise_for_status()
    return resp.text


def save(data: str, *path_parts: str) -> None:
    path = DATA_DIR.joinpath(*path_parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        f.write(data)
    print(f"  saved -> data/raw/{'/'.join(path_parts)}")


# ── Player data ────────────────────────────────────────────────────────────────

def fetch_player_list() -> None:
    print("Fetching player list …")
    save(get("get-player-list"), "players", "player_list.csv")


def fetch_dg_rankings() -> None:
    print("Fetching DG rankings …")
    save(get("preds/get-dg-rankings"), "players", "dg_rankings.csv")


def fetch_skill_ratings() -> None:
    print("Fetching skill ratings …")
    for display in ("value", "rank"):
        save(
            get("preds/skill-ratings", {"display": display}),
            "players", f"skill_ratings_{display}.csv",
        )


# ── Schedule / course / tourney ────────────────────────────────────────────────

def fetch_schedules(
    tours: tuple = ("pga",),
    seasons: tuple = (2024, 2025, 2026),
) -> None:
    for tour in tours:
        for season in seasons:
            print(f"Fetching schedule ({tour} {season}) …")
            save(
                get("get-schedule", {"tour": tour, "season": season, "upcoming_only": "no"}),
                "schedule", f"schedule_{tour}_{season}.csv",
            )


def fetch_field_updates(tours: tuple = ("pga",)) -> None:
    for tour in tours:
        print(f"Fetching field updates ({tour}) …")
        save(
            get("field-updates", {"tour": tour}),
            "schedule", f"field_updates_{tour}.csv",
        )


# ── Historical event lists ─────────────────────────────────────────────────────

def fetch_historical_raw_event_list(tours: list = HIST_TOURS) -> None:
    for tour in tours:
        print(f"Fetching historical raw event list ({tour}) …")
        save(
            get("historical-raw-data/event-list", {"tour": tour}),
            "historical", "event_lists", f"raw_events_{tour}.csv",
        )


def fetch_historical_odds_event_list(tours: list = ("pga",)) -> None:
    for tour in tours:
        print(f"Fetching historical odds event list ({tour}) …")
        save(
            get("historical-odds/event-list", {"tour": tour}),
            "historical", "event_lists", f"odds_events_{tour}.csv",
        )


# ── Historical raw rounds ──────────────────────────────────────────────────────

def fetch_historical_rounds(
    tours: list = HIST_TOURS,
    years: list = ROUNDS_YEARS,
) -> None:
    """One request per tour/year using event_id=all."""
    for tour in tours:
        for year in years:
            print(f"Fetching historical rounds ({tour} {year}) …")
            try:
                save(
                    get("historical-raw-data/rounds", {
                        "tour": tour, "event_id": "all", "year": year,
                    }),
                    "historical", "rounds", f"rounds_{tour}_{year}.csv",
                )
            except requests.HTTPError as exc:
                print(f"  WARNING: {exc}")


# ── Historical odds ────────────────────────────────────────────────────────────

def fetch_historical_outrights(
    tours: list = ("pga",),
    years: list = ODDS_YEARS,
    markets: list = OUTRIGHT_MARKETS,
    books: list = ODDS_BOOKS,
) -> None:
    """One request per tour/year/market/book using event_id=all."""
    for tour in tours:
        for year in years:
            for market in markets:
                for book in books:
                    print(f"Fetching historical outrights ({tour} {year} {market} {book}) …")
                    try:
                        save(
                            get("historical-odds/outrights", {
                                "tour": tour, "event_id": "all", "year": year,
                                "market": market, "book": book, "odds_format": "decimal",
                            }),
                            "historical", "odds", "outrights",
                            f"outrights_{tour}_{year}_{market}_{book}.csv",
                        )
                    except requests.HTTPError as exc:
                        print(f"  WARNING: {exc}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=== DataGolf Data Extraction ===\n")

    # Player snapshots
    fetch_player_list()
    fetch_dg_rankings()
    fetch_skill_ratings()

    # Tournament / course info
    fetch_schedules()
    fetch_field_updates()

    # Historical event lists (reference + required for downstream)
    fetch_historical_raw_event_list()
    fetch_historical_odds_event_list()

    # Historical results: round-level scoring + strokes-gained
    fetch_historical_rounds()

    # Historical odds: FanDuel + DraftKings outrights (2019–2025)
    fetch_historical_outrights()

    print("\n=== Done ===")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Fetches daily weather for every PGA Tour event and writes a single table.

Output: data/processed/weather.csv
  event_id, year, course_key, date,
  temperature_mean_c, precipitation_mm, wind_speed_max_kmh, relative_humidity_pct

Coverage: 2 days before first round through the final round.
Units: Celsius, mm, km/h, %.

For upcoming events use fetch_forecast() directly at prediction time.

Run with: python src/fetch_weather.py
"""

import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

DATA_DIR  = Path(__file__).resolve().parents[1] / "data"
PROCESSED = DATA_DIR / "processed"

ARCHIVE_URL  = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

TODAY = date.today()


# ── HTTP + parsing ─────────────────────────────────────────────────────────────

def _get(url: str, params: dict, retries: int = 3) -> dict:
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise


def fetch_weather(lat: float, lon: float, start: date, end: date) -> pd.DataFrame:
    """
    Returns one row per date with temperature, precipitation,
    wind speed, and humidity. Uses archive API for past dates,
    forecast API for future dates.
    """
    url = FORECAST_URL if end >= TODAY else ARCHIVE_URL
    data = _get(url, {
        "latitude":           round(lat, 4),
        "longitude":          round(lon, 4),
        "start_date":         start.isoformat(),
        "end_date":           end.isoformat(),
        "daily":              "temperature_2m_mean,precipitation_sum,wind_speed_10m_max",
        "hourly":             "relative_humidity_2m",
        "timezone":           "auto",
        "temperature_unit":   "celsius",
        "wind_speed_unit":    "kmh",
        "precipitation_unit": "mm",
    })

    daily = pd.DataFrame(data["daily"]).rename(columns={
        "time":                "date",
        "temperature_2m_mean": "temperature_mean_c",
        "precipitation_sum":   "precipitation_mm",
        "wind_speed_10m_max":  "wind_speed_max_kmh",
    })
    daily["date"] = pd.to_datetime(daily["date"]).dt.date

    hourly = pd.DataFrame(data["hourly"])
    hourly["date"] = pd.to_datetime(hourly["time"]).dt.date
    humidity = (
        hourly.groupby("date")["relative_humidity_2m"]
        .mean().round(1).reset_index()
        .rename(columns={"relative_humidity_2m": "relative_humidity_pct"})
    )

    return daily.merge(humidity, on="date", how="left")


# ── Main batch ─────────────────────────────────────────────────────────────────

def run() -> None:
    events  = pd.read_csv(PROCESSED / "events.csv",
                          parse_dates=["start_date", "event_completed"])
    courses = pd.read_csv(PROCESSED / "courses.csv")

    df = events.merge(
        courses[["course_key", "latitude", "longitude"]],
        on="course_key", how="left",
    ).dropna(subset=["latitude", "longitude", "event_completed"])

    print(f"Fetching weather for {len(df)} events ...\n")

    rows, errors = [], []
    for i, row in enumerate(df.itertuples(), 1):
        event_end   = row.event_completed.date()
        event_start = (row.start_date.date() if pd.notna(row.start_date)
                       else event_end - timedelta(days=3))
        fetch_start = event_start - timedelta(days=2)

        print(f"  [{i}/{len(df)}] {row.event_name} {int(row.year)}"
              f"  ({fetch_start} -> {event_end})")
        try:
            wdf = fetch_weather(row.latitude, row.longitude, fetch_start, event_end)
            wdf.insert(0, "event_id_year", f"{int(row.event_id)}_{int(row.year)}")
            wdf.insert(1, "event_id",   int(row.event_id))
            wdf.insert(2, "year",       int(row.year))
            wdf.insert(3, "course_key", int(row.course_key))
            rows.append(wdf)
            time.sleep(0.1)
        except Exception as exc:
            print(f"    WARNING: {exc}")
            errors.append((row.event_id, row.year, str(exc)))

    out = pd.concat(rows, ignore_index=True)
    out.to_csv(PROCESSED / "weather.csv", index=False)
    print(f"\n  saved -> data/processed/weather.csv  ({len(out):,} rows)")
    print(f"  {len(errors)} errors" + (f": {errors}" if errors else ""))


# ── Live forecast ──────────────────────────────────────────────────────────────

def fetch_forecast(event_id: int, year: int,
                   lat: float, lon: float,
                   start: date, end: date) -> pd.DataFrame:
    """
    Pull the weather forecast for an upcoming event at prediction time.
    Returns the same schema as weather.csv so it can be joined to rounds.
    """
    df = fetch_weather(lat, lon, start - timedelta(days=2), end)
    df.insert(0, "event_id",   event_id)
    df.insert(1, "year",       year)
    return df


if __name__ == "__main__":
    run()

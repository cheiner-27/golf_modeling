"""Generates notebooks/01_data_exploration.ipynb"""
import nbformat as nbf

nb = nbf.v4.new_notebook()
cells = []

# ── Title ──────────────────────────────────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell(
    "# Golf Modeling - Data Exploration\n"
    "Summary tables for each processed CSV: field definitions, data types, "
    "null rates, outliers, and quality issues."
))

# ── Setup ──────────────────────────────────────────────────────────────────────
cells.append(nbf.v4.new_code_cell(
"""import pandas as pd
import numpy as np
from IPython.display import display

DATA = "../data/processed/"

pd.set_option("display.max_colwidth", None)
pd.set_option("display.max_rows", 200)


def outlier_count(series):
    \"\"\"IQR x1.5 for numeric; rare-value count (<0.5% freq) for categorical.\"\"\"
    s = series.dropna()
    if pd.api.types.is_numeric_dtype(s):
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            return 0
        return int(((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum())
    else:
        freq = s.value_counts(normalize=True)
        rare = freq[freq < 0.005].index
        return int(s.isin(rare).sum())


def summary_table(df, meta):
    n = len(df)
    rows = []
    for col in df.columns:
        m = meta.get(col, {})
        null_n = int(df[col].isnull().sum())
        out_n  = outlier_count(df[col])
        dtype  = df[col].dtype
        if pd.api.types.is_float_dtype(dtype):
            t = "float"
        elif pd.api.types.is_integer_dtype(dtype):
            t = "integer"
        elif pd.api.types.is_bool_dtype(dtype):
            t = "boolean"
        else:
            t = "string"
        rows.append({
            "Field":               col,
            "Description":         m.get("description", ""),
            "Type":                t,
            "Blanks":              null_n,
            "% Blank":             round(null_n / n, 6),
            "Variable Category":   m.get("category", ""),
            "Outliers":            out_n,
            "% Outlier":           round(out_n / n, 6),
            "Data Quality Issues": m.get("quality_issues", ""),
        })
    out = pd.DataFrame(rows)
    return out.style \\
        .format({"% Blank": "{:.2%}", "% Outlier": "{:.2%}"}) \\
        .set_properties(**{"text-align": "left", "white-space": "pre-wrap"}) \\
        .set_table_styles([{"selector": "th", "props": [("text-align", "left")]}]) \\
        .applymap(lambda v: "background-color: #fff3cd" if v else "",
                  subset=["Data Quality Issues"])


def section(df, meta, title):
    print(f"\\n{'='*80}\\n  {title}  ({len(df.columns)} fields, {len(df):,} rows)\\n{'='*80}")
    display(summary_table(df, meta))
"""
))

# ── PLAYERS ────────────────────────────────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("## 1. players.csv"))
cells.append(nbf.v4.new_code_cell(
"""players = pd.read_csv(DATA + "players.csv")
players.head()"""
))
cells.append(nbf.v4.new_code_cell(
"""players_meta = {
    "dg_id": {
        "description": "Unique DataGolf player identifier. Primary key.",
        "category": "identifier",
        "quality_issues": "",
    },
    "player_name": {
        "description": "Player full name in 'Last, First' format.",
        "category": "identifier",
        "quality_issues": "Name format does not match winner field in events.csv, which appends DG ID in parentheses.",
    },
    "country": {
        "description": "Player home country (full English name).",
        "category": "demographic",
        "quality_issues": "",
    },
    "country_code": {
        "description": "ISO 3-letter country code for player home country.",
        "category": "demographic",
        "quality_issues": "",
    },
    "amateur": {
        "description": "Amateur status flag. 1 = amateur, 0 = professional.",
        "category": "demographic",
        "quality_issues": "Static snapshot only - does not reflect historical status. A now-professional player will show 0 even for rounds played as an amateur.",
    },
}

section(players, players_meta, "players.csv")
"""
))

# ── COURSES ────────────────────────────────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("## 2. courses.csv"))
cells.append(nbf.v4.new_code_cell(
"""courses = pd.read_csv(DATA + "courses.csv")
courses.head()"""
))
cells.append(nbf.v4.new_code_cell(
"""courses_meta = {
    "course_key": {
        "description": "Unique DataGolf course identifier. Primary key.",
        "category": "identifier",
        "quality_issues": "",
    },
    "course_name": {
        "description": "Official name of the golf course or specific layout (e.g., 'South Course').",
        "category": "identifier",
        "quality_issues": "",
    },
    "location": {
        "description": "City and state/region where the course is located.",
        "category": "geographic",
        "quality_issues": "Sourced from 2024-2026 schedule for recent courses; manually filled for historical venues - format may be inconsistent.",
    },
    "country": {
        "description": "Country where the course is located.",
        "category": "geographic",
        "quality_issues": "Mixed format: schedule-sourced entries use full country name; manual supplement entries use 3-letter ISO codes. Normalize before use.",
    },
    "latitude": {
        "description": "Geographic latitude of the course in decimal degrees.",
        "category": "geographic",
        "quality_issues": "Coordinates for courses absent from the 2024-2026 schedule were filled manually from domain knowledge. Verify before high-stakes use.",
    },
    "longitude": {
        "description": "Geographic longitude of the course in decimal degrees.",
        "category": "geographic",
        "quality_issues": "See latitude note.",
    },
}

section(courses, courses_meta, "courses.csv")
"""
))

# ── EVENTS ─────────────────────────────────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("## 3. events.csv"))
cells.append(nbf.v4.new_code_cell(
"""events = pd.read_csv(DATA + "events.csv", parse_dates=["start_date", "event_completed"])
events.head()"""
))
cells.append(nbf.v4.new_code_cell(
"""events_meta = {
    "event_id_year": {
        "description": "Composite primary key: event_id and year joined by underscore (e.g., '6_2024'). Unique per tournament occurrence.",
        "category": "identifier",
        "quality_issues": "",
    },
    "event_id": {
        "description": "DataGolf event identifier. Reused across years for recurring tournaments.",
        "category": "identifier",
        "quality_issues": "Not unique alone - always pair with year or use event_id_year.",
    },
    "year": {
        "description": "Calendar year the tournament was played.",
        "category": "temporal",
        "quality_issues": "",
    },
    "season": {
        "description": "PGA Tour season year. May differ from calendar year for events straddling the season boundary.",
        "category": "temporal",
        "quality_issues": "",
    },
    "event_name": {
        "description": "Official tournament name. Subject to sponsorship-driven changes year over year.",
        "category": "tournament metadata",
        "quality_issues": "Same physical event may have different names across years due to sponsorship changes. Use event_id to track recurring events consistently.",
    },
    "tour": {
        "description": "Tour identifier. All records are PGA Tour ('pga').",
        "category": "tournament metadata",
        "quality_issues": "",
    },
    "start_date": {
        "description": "First round date of the tournament.",
        "category": "temporal",
        "quality_issues": "Null for ~89% of records (pre-2024 events) - sourced only from 2024-2026 schedule files.",
    },
    "event_completed": {
        "description": "Date the tournament concluded (final round date). Used to derive per-round dates in the absence of explicit date columns.",
        "category": "temporal",
        "quality_issues": "",
    },
    "course_key": {
        "description": "Foreign key to courses.csv. Set to the round 1 course for multi-course rotation events.",
        "category": "tournament metadata",
        "quality_issues": "Multi-course events (e.g., Pebble Beach Pro-Am) rotate players across courses by round. Use course_key in rounds.csv for round-level accuracy.",
    },
    "status": {
        "description": "Tournament completion status (e.g., 'completed', 'in_progress', 'scheduled').",
        "category": "tournament metadata",
        "quality_issues": "Null for pre-2024 events.",
    },
    "winner": {
        "description": "Winning player name and DataGolf ID formatted as 'Last, First (dg_id)'.",
        "category": "tournament metadata",
        "quality_issues": "Null for pre-2024 events. Not a clean foreign key - requires string parsing to extract dg_id. Derive winner from rounds.csv (fin_text == '1') for full historical coverage.",
    },
}

section(events, events_meta, "events.csv")
"""
))

# ── ROUNDS ─────────────────────────────────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("## 4. rounds.csv"))
cells.append(nbf.v4.new_code_cell(
"""rounds = pd.read_csv(DATA + "rounds.csv", low_memory=False)
rounds.head()"""
))
cells.append(nbf.v4.new_code_cell(
"""rounds_meta = {
    "event_id_year": {
        "description": "Foreign key to events.csv.",
        "category": "identifier",
        "quality_issues": "",
    },
    "event_id": {
        "description": "DataGolf event identifier. Not unique alone.",
        "category": "identifier",
        "quality_issues": "Not unique alone - use event_id_year.",
    },
    "year": {
        "description": "Calendar year the round was played.",
        "category": "identifier",
        "quality_issues": "",
    },
    "dg_id": {
        "description": "Foreign key to players.csv.",
        "category": "identifier",
        "quality_issues": "",
    },
    "round_num": {
        "description": "Round number within the tournament (1-4). Round 1 = Thursday, Round 4 = Sunday for standard events.",
        "category": "identifier",
        "quality_issues": "",
    },
    "course_key": {
        "description": "Foreign key to courses.csv. Varies by round in multi-course rotation events.",
        "category": "identifier",
        "quality_issues": "",
    },
    "course_par": {
        "description": "Par score for the course/layout played in this round.",
        "category": "scoring",
        "quality_issues": "",
    },
    "fin_text": {
        "description": "Player's final tournament result: numeric ('1') for winner, 'T5' for tied 5th, 'CUT' for missed cut, 'WD' for withdrawal, 'DQ' for disqualification, 'MDF' for made cut but did not finish.",
        "category": "scoring",
        "quality_issues": "Mixed text/numeric-like format - must be parsed before use as a numeric target or feature. CUT players have only 2 round records; rounds 3-4 do not exist for them.",
    },
    "start_hole": {
        "description": "Hole the player began their round on. 1 = standard start, 10 = split tee, 9 = rare variant.",
        "category": "scoring",
        "quality_issues": "55% null - not tracked for older events (pre-~2018). Do not use as a feature without year-filtering.",
    },
    "teetime": {
        "description": "Scheduled tee time in local time (e.g., '7:05am').",
        "category": "scoring",
        "quality_issues": "55% null - same coverage gap as start_hole. Stored as string; requires parsing before numeric use.",
    },
    "round_score": {
        "description": "Player's total stroke count for the round.",
        "category": "scoring",
        "quality_issues": "Null for WD/DQ players who did not complete the round (~0.2%).",
    },
    "sg_putt": {
        "description": "Strokes gained putting: strokes saved vs. field average on the putting green.",
        "category": "strokes gained",
        "quality_issues": "21% null - SG components not tracked before ~2017 for many events. sg_total has full coverage; component breakdown does not.",
    },
    "sg_arg": {
        "description": "Strokes gained around the green: strokes saved vs. field average on shots within ~30 yards of the hole, excluding putts.",
        "category": "strokes gained",
        "quality_issues": "21% null - see sg_putt.",
    },
    "sg_app": {
        "description": "Strokes gained approach: strokes saved vs. field average on approach shots (~30 to ~250 yards from the hole).",
        "category": "strokes gained",
        "quality_issues": "21% null - see sg_putt.",
    },
    "sg_ott": {
        "description": "Strokes gained off the tee: strokes saved vs. field average on tee shots on par 4s and par 5s.",
        "category": "strokes gained",
        "quality_issues": "21% null - see sg_putt.",
    },
    "sg_t2g": {
        "description": "Strokes gained tee to green: sg_ott + sg_app + sg_arg combined. Excludes putting.",
        "category": "strokes gained",
        "quality_issues": "21% null - see sg_putt. Collinear with components: sg_t2g + sg_putt = sg_total. Do not include all three in a model simultaneously.",
    },
    "sg_total": {
        "description": "Total strokes gained vs. field average for the round. Full historical coverage.",
        "category": "strokes gained",
        "quality_issues": "",
    },
    "driving_dist": {
        "description": "Average driving distance in yards for the round.",
        "category": "shot tracking",
        "quality_issues": "54% null - not tracked for many events without Shotlink data, concentrated in pre-2010 records.",
    },
    "driving_acc": {
        "description": "Driving accuracy: proportion of tee shots landing in the fairway (0.0-1.0).",
        "category": "shot tracking",
        "quality_issues": "52% null - see driving_dist.",
    },
    "gir": {
        "description": "Greens in regulation rate: proportion of holes where the green was reached in regulation (0.0-1.0).",
        "category": "shot tracking",
        "quality_issues": "52% null - see driving_dist.",
    },
    "scrambling": {
        "description": "Scrambling rate: proportion of holes where par or better was made after missing the green in regulation (0.0-1.0).",
        "category": "shot tracking",
        "quality_issues": "58% null - see driving_dist.",
    },
    "prox_rgh": {
        "description": "Average proximity to the hole in feet from approach shots played out of the rough.",
        "category": "shot tracking",
        "quality_issues": "59% null - see driving_dist. High variance when a player has few rough approach shots in a given round.",
    },
    "prox_fw": {
        "description": "Average proximity to the hole in feet from approach shots played from the fairway.",
        "category": "shot tracking",
        "quality_issues": "58% null - see driving_dist.",
    },
    "great_shots": {
        "description": "Count of shots classified as significantly above expected quality for the round.",
        "category": "shot tracking",
        "quality_issues": "58% null - see driving_dist. Classification threshold is DataGolf internal and not publicly documented.",
    },
    "poor_shots": {
        "description": "Count of shots classified as significantly below expected quality for the round.",
        "category": "shot tracking",
        "quality_issues": "58% null - see driving_dist. Same threshold caveat as great_shots.",
    },
    "eagles_or_better": {
        "description": "Number of holes scored at 2-under par or better in the round.",
        "category": "hole outcomes",
        "quality_issues": "~0.5% null - minor gap in early records.",
    },
    "birdies": {
        "description": "Number of holes scored at 1-under par in the round.",
        "category": "hole outcomes",
        "quality_issues": "~0.5% null - see eagles_or_better.",
    },
    "pars": {
        "description": "Number of holes scored at even par in the round.",
        "category": "hole outcomes",
        "quality_issues": "~0.5% null - see eagles_or_better.",
    },
    "bogies": {
        "description": "Number of holes scored at 1-over par in the round.",
        "category": "hole outcomes",
        "quality_issues": "~0.5% null - see eagles_or_better.",
    },
    "doubles_or_worse": {
        "description": "Number of holes scored at 2-over par or worse. Rough proxy for penalty stroke incidents.",
        "category": "hole outcomes",
        "quality_issues": "~0.5% null - see eagles_or_better.",
    },
}

section(rounds, rounds_meta, "rounds.csv")
"""
))

# ── WEATHER ────────────────────────────────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("## 5. weather.csv"))
cells.append(nbf.v4.new_code_cell(
"""weather = pd.read_csv(DATA + "weather.csv", parse_dates=["date"])
weather.head()"""
))
cells.append(nbf.v4.new_code_cell(
"""weather_meta = {
    "event_id_year": {
        "description": "Foreign key to events.csv. Join to rounds via event_id_year; match round date using event_completed minus (4 - round_num) days.",
        "category": "identifier",
        "quality_issues": "",
    },
    "event_id": {
        "description": "DataGolf event identifier.",
        "category": "identifier",
        "quality_issues": "",
    },
    "year": {
        "description": "Calendar year of the event.",
        "category": "identifier",
        "quality_issues": "",
    },
    "course_key": {
        "description": "Foreign key to courses.csv. Included for convenience - weather is already location-specific.",
        "category": "identifier",
        "quality_issues": "",
    },
    "date": {
        "description": "Calendar date of the observation. Covers 2 days before the first round through the final round (typically 6 rows per event).",
        "category": "temporal",
        "quality_issues": "",
    },
    "temperature_mean_c": {
        "description": "Mean daily air temperature at 2 meters above ground in degrees Celsius.",
        "category": "atmospheric",
        "quality_issues": "Actual observed weather used for historical records, not the pre-round forecast. Add Gaussian jitter (~±2°C) during training to simulate forecast uncertainty.",
    },
    "precipitation_mm": {
        "description": "Total precipitation for the day in millimeters.",
        "category": "atmospheric",
        "quality_issues": "Actual observed - see temperature note. Timing within the day is not captured; a high daily total could be a brief shower or all-day rain.",
    },
    "wind_speed_max_kmh": {
        "description": "Maximum wind speed at 10 meters above ground in km/h for the day.",
        "category": "atmospheric",
        "quality_issues": "Actual observed - see temperature note. Daily maximum does not distinguish sustained wind from gusts; wind direction not included.",
    },
    "relative_humidity_pct": {
        "description": "Mean daily relative humidity as a percentage (0-100), aggregated from hourly Open-Meteo data.",
        "category": "atmospheric",
        "quality_issues": "Actual observed - see temperature note.",
    },
}

section(weather, weather_meta, "weather.csv")
"""
))

nb.cells = cells

out = "notebooks/01_data_exploration.ipynb"
with open(out, "w", encoding="utf-8") as f:
    nbf.write(nb, f)
print(f"Written: {out}")

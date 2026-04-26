# Data Golf API Documentation

**Base URL:** `https://feeds.datagolf.com`  
**Authentication:** Append `&key=YOUR_API_KEY` to every request.  
**Rate Limit:** 45 requests/minute. Exceeding this results in a 5-minute suspension.  
**File Formats:** All endpoints support `json` (default) and `csv` via the `file_format` parameter.

---

## Overview

The API is divided into seven categories:

1. [General Use](#1-general-use)
2. [Model Predictions](#2-model-predictions)
3. [Live Model](#3-live-model)
4. [Betting Tools](#4-betting-tools)
5. [Historical Raw Data](#5-historical-raw-data)
6. [Historical Event Stats](#6-historical-event-stats)
7. [Historical Betting Odds](#7-historical-betting-odds)
8. [Historical DFS Data](#8-historical-dfs-data)

---

## 1. General Use

### Player List & IDs
Returns players who have played on a major tour since 2018 or are playing this week. Includes IDs, country, and amateur status.

**Endpoint:** `GET /get-player-list`

| Parameter | Description | Options |
|-----------|-------------|---------|
| `file_format` | File format | `json` (default), `csv` |

**Example:**
```
https://feeds.datagolf.com/get-player-list?file_format=json&key=API_TOKEN
```

---

### Tour Schedules
Season schedules for PGA, DP World, Korn Ferry, and LIV Golf. Includes event names/IDs, course names/IDs, location data, and winners for completed events.

**Endpoint:** `GET /get-schedule`

| Parameter | Description | Options |
|-----------|-------------|---------|
| `tour` | Tour | `all` (default), `pga`, `euro`, `kft`, `alt` / `liv` |
| `season` | Season year | `2026`, `2025`, `2024` (defaults to current) |
| `upcoming_only` | Only upcoming tournaments | `yes`, `no` (default) |
| `file_format` | File format | `json` (default), `csv` |

**Example:**
```
https://feeds.datagolf.com/get-schedule?tour=pga&season=2026&upcoming_only=no&file_format=json&key=API_TOKEN
```

---

### Field Updates
Field lists and updates (WDs, Monday qualifiers, tee times, start holes, courses) for upcoming tournaments. Includes Data Golf IDs and tour-specific IDs.

**Endpoint:** `GET /field-updates`

| Parameter | Description | Options |
|-----------|-------------|---------|
| `tour` | Tour | `pga` (default), `opp`, `euro`, `kft`, `alt` (LIV), `upcoming_pga` |
| `file_format` | File format | `json` (default), `csv` |

**Example:**
```
https://feeds.datagolf.com/field-updates?tour=pga&file_format=json&key=API_TOKEN
```

---

## 2. Model Predictions

### Data Golf Rankings
Top 500 players in current DG rankings with skill estimates and OWGR rank.

**Endpoint:** `GET /preds/get-dg-rankings`

| Parameter | Description | Options |
|-----------|-------------|---------|
| `file_format` | File format | `json` (default), `csv` |

**Example:**
```
https://feeds.datagolf.com/preds/get-dg-rankings?file_format=json&key=API_TOKEN
```

---

### Pre-Tournament Predictions
Full-field probabilistic forecasts for the upcoming tournament on PGA, European, and Korn Ferry Tours. Includes win, top 5, top 10, top 20, make cut probabilities from baseline and course-fit models.

**Endpoint:** `GET /preds/pre-tournament`

| Parameter | Description | Options |
|-----------|-------------|---------|
| `tour` | Tour | `pga` (default), `euro`, `kft`, `opp`, `alt` |
| `add_position` | Additional positions (comma-separated) | `1`–`50` |
| `dead_heat` | Adjust for dead-heat rules | `yes` (default), `no` |
| `odds_format` | Odds format | `percent` (default), `american`, `decimal`, `fraction` |
| `file_format` | File format | `json` (default), `csv` |

**Example:**
```
https://feeds.datagolf.com/preds/pre-tournament?tour=pga&add_position=17,23&dead_heat=yes&odds_format=decimal&file_format=json&key=API_TOKEN
```

---

### Pre-Tournament Predictions Archive
Historical archive of PGA Tour pre-tournament predictions.

**Endpoint:** `GET /preds/pre-tournament-archive`

| Parameter | Description | Options |
|-----------|-------------|---------|
| `event_id` | Event ID (use `/historical-odds/event-list` to find IDs) | — |
| `year` | Calendar year | `2020`–`2025` (default: `2025`) |
| `odds_format` | Odds format | `percent` (default), `american`, `decimal`, `fraction` |
| `file_format` | File format | `json` (default), `csv` |

**Example:**
```
https://feeds.datagolf.com/preds/pre-tournament-archive?event_id=14&year=2020&odds_format=american&file_format=json&key=API_TOKEN
```

---

### Player Skill Decompositions
Detailed strokes-gained prediction breakdown for every player in upcoming PGA and European Tour events.

**Endpoint:** `GET /preds/player-decompositions`

| Parameter | Description | Options |
|-----------|-------------|---------|
| `tour` | Tour | `pga` (default), `euro`, `opp`, `alt` |
| `file_format` | File format | `json` (default), `csv` |

**Example:**
```
https://feeds.datagolf.com/preds/player-decompositions?tour=pga&file_format=json&key=API_TOKEN
```

---

### Player Skill Ratings
Skill estimates and ranks for all players with sufficient ShotLink measured rounds (30+ rounds in last year, or 50+ in last 2 years).

**Endpoint:** `GET /preds/skill-ratings`

| Parameter | Description | Options |
|-----------|-------------|---------|
| `display` | Display mode | `value` (default), `rank` |
| `file_format` | File format | `json` (default), `csv` |

**Example:**
```
https://feeds.datagolf.com/preds/skill-ratings?display=value&file_format=json&key=API_TOKEN
```

---

### Detailed Approach Skill
Player-level approach performance stats (SG/shot, proximity, GIR, good shot rate, poor shot avoidance) across yardage/lie buckets.

**Endpoint:** `GET /preds/approach-skill`

| Parameter | Description | Options |
|-----------|-------------|---------|
| `period` | Time period | `l24` (last 24 months, default), `l12` (last 12 months), `ytd` |
| `file_format` | File format | `json` (default), `csv` |

**Example:**
```
https://feeds.datagolf.com/preds/approach-skill?period=l12&file_format=json&key=API_TOKEN
```

---

### Fantasy Projection Defaults
Default fantasy projections for main, showdown, late showdown, weekend, and captain mode contests at DraftKings, FanDuel, and Yahoo.

**Endpoint:** `GET /preds/fantasy-projection-defaults`

| Parameter | Description | Options |
|-----------|-------------|---------|
| `tour` | Tour | `pga` (default), `euro`, `opp`, `alt` |
| `site` | DFS site | `draftkings` (default), `fanduel`, `yahoo` |
| `slate` | Slate type (non-main slates only for DraftKings) | `main` (default), `showdown`, `showdown_late`, `weekend`, `captain` |
| `file_format` | File format | `json` (default), `csv` |

**Example:**
```
https://feeds.datagolf.com/preds/fantasy-projection-defaults?tour=pga&site=draftkings&slate=main&file_format=json&key=API_TOKEN
```

---

## 3. Live Model

### Live Model Predictions
Live finish probabilities updating every 5 minutes during ongoing PGA and European Tour tournaments.

**Endpoint:** `GET /preds/in-play`

| Parameter | Description | Options |
|-----------|-------------|---------|
| `tour` | Tour | `pga` (default), `euro`, `opp`, `kft`, `alt` |
| `dead_heat` | Adjust for dead-heat rules | `no` (default), `yes` |
| `odds_format` | Odds format | `percent` (default), `american`, `decimal`, `fraction` |
| `file_format` | File format | `json` (default), `csv` |

**Example:**
```
https://feeds.datagolf.com/preds/in-play?tour=euro&dead_heat=no&odds_format=percent&file_format=json&key=API_TOKEN
```

---

### Live Tournament Stats
Live strokes-gained and traditional stats for every player during PGA Tour tournaments.

**Endpoint:** `GET /preds/live-tournament-stats`

| Parameter | Description | Options |
|-----------|-------------|---------|
| `stats` | Comma-separated list of stats | `sg_putt`, `sg_arg`, `sg_app`, `sg_ott`, `sg_t2g`, `sg_bs`, `sg_total`, `distance`, `accuracy`, `gir`, `prox_fw`, `prox_rgh`, `scrambling`, `great_shots`, `poor_shots` |
| `round` | Round | `event_cumulative`, `event_avg`, `1`, `2`, `3`, `4` |
| `display` | Display mode | `value` (default), `rank` |
| `file_format` | File format | `json` (default), `csv` |

**Example:**
```
https://feeds.datagolf.com/preds/live-tournament-stats?stats=sg_ott,distance,accuracy,sg_app,gir,prox_fw,sg_putt,scrambling&key=API_TOKEN
```

---

### Live Hole Scoring Distributions
Live hole scoring averages and distributions (birdies, pars, bogeys, etc.) broken down by tee time wave.

**Endpoint:** `GET /preds/live-hole-stats`

| Parameter | Description | Options |
|-----------|-------------|---------|
| `tour` | Tour | `pga` (default), `euro`, `opp`, `kft`, `alt` |
| `file_format` | File format | `json` (default), `csv` |

**Example:**
```
https://feeds.datagolf.com/preds/live-hole-stats?tour=euro&file_format=json&key=API_TOKEN
```

---

### Live Strokes-Gained ⚠️ DEPRECATED
Use **Live Tournament Stats** instead.

**Endpoint:** `GET /preds/live-strokes-gained`

---

## 4. Betting Tools

### Outright (Finish Position) Odds
Most recent win, top 5, top 10, top 20, make/miss cut, and first round leader odds from 11 sportsbooks alongside DG model predictions.

**Endpoint:** `GET /betting-tools/outrights`

| Parameter | Description | Options |
|-----------|-------------|---------|
| `tour` | Tour | `pga` (default), `euro`, `kft`, `opp`, `alt` |
| `market` | **Required.** Market | `win`, `top_5`, `top_10`, `top_20`, `mc`, `make_cut`, `frl` |
| `odds_format` | Odds format | `percent`, `american`, `decimal` (default), `fraction` |
| `file_format` | File format | `json` (default), `csv` |

**Example:**
```
https://feeds.datagolf.com/betting-tools/outrights?tour=pga&market=win&odds_format=decimal&file_format=json&key=API_TOKEN
```

---

### Match-Up & 3-Ball Odds
Most recent tournament match-up, round match-up, and 3-ball odds from 8 sportsbooks alongside DG model predictions.

**Endpoint:** `GET /betting-tools/matchups`

| Parameter | Description | Options |
|-----------|-------------|---------|
| `tour` | Tour | `pga` (default), `euro`, `opp`, `alt` |
| `market` | **Required.** Market | `tournament_matchups`, `round_matchups`, `3_balls` |
| `odds_format` | Odds format | `percent`, `american`, `decimal` (default), `fraction` |
| `file_format` | File format | `json` (default), `csv` |

**Example:**
```
https://feeds.datagolf.com/betting-tools/matchups?tour=pga&market=3_balls&odds_format=decimal&file_format=json&key=API_TOKEN
```

---

### Match-Up & 3-Ball Odds — All Pairings
DG matchup/3-ball odds for every pairing in the next round of current PGA Tour and European Tour events.

**Endpoint:** `GET /betting-tools/matchups-all-pairings`

| Parameter | Description | Options |
|-----------|-------------|---------|
| `tour` | Tour | `pga` (default), `euro`, `opp`, `alt` |
| `odds_format` | Odds format | `percent`, `american`, `decimal` (default), `fraction` |
| `file_format` | File format | `json` (default), `csv` |

**Example:**
```
https://feeds.datagolf.com/betting-tools/matchups-all-pairings?tour=pga&odds_format=decimal&file_format=json&key=API_TOKEN
```

---

## 5. Historical Raw Data

### Historical Raw Data Event IDs
List of tournaments and IDs available through the historical raw data endpoint. Use to get `event_id` and `year` for the rounds endpoint.

**Endpoint:** `GET /historical-raw-data/event-list`

| Parameter | Description | Options |
|-----------|-------------|---------|
| `tour` | Tour code | `pga`, `euro`, `kft`, `cha`, `jpn`, `anz`, `alp`, `champ`, `kor`, `ngl`, `bet`, `chn`, `afr`, `pgt`, `pgti`, `atvt`, `atgt`, `sam`, `ept`, `can`, `liv`, `mex`, `pta`, `cpt`, `tpga`, `tpt` |
| `file_format` | File format | `json` (default), `csv` |

**Example:**
```
https://feeds.datagolf.com/historical-raw-data/event-list?file_format=json&key=API_TOKEN
```

---

### Round Scoring, Stats & Strokes Gained
Round-level scoring, traditional stats, strokes-gained, and tee time data across 22 global tours.

**Endpoint:** `GET /historical-raw-data/rounds`

| Parameter | Description | Options |
|-----------|-------------|---------|
| `tour` | **Required.** Tour code | Same as event-list above |
| `event_id` | **Required.** Event ID or `all` | Use `/historical-raw-data/event-list` to find IDs |
| `year` | **Required.** Calendar year | `1983`–`2026` (Majors/Players); `2004`–`2026` (PGA); `2017`–`2026` (other tours) |
| `file_format` | File format | `json` (default), `csv` |

**Example:**
```
https://feeds.datagolf.com/historical-raw-data/rounds?tour=pga&event_id=535&year=2021&file_format=json&key=API_TOKEN
```

---

## 6. Historical Event Stats

### Historical Event Data Event IDs
List of tournaments and IDs for the historical event data endpoint.

**Endpoint:** `GET /historical-event-data/event-list`

| Parameter | Description | Options |
|-----------|-------------|---------|
| `tour` | Tour | `pga` |
| `file_format` | File format | `json` (default), `csv` |

**Example:**
```
https://feeds.datagolf.com/historical-event-data/event-list?file_format=json&key=API_TOKEN
```

---

### Event Finishes, Earnings & Points
Event-level finishes, earnings, FedExCup points, and DG Points from official PGA Tour tournaments.

**Endpoint:** `GET /historical-event-data/events`

| Parameter | Description | Options |
|-----------|-------------|---------|
| `tour` | **Required.** Tour | `pga` |
| `event_id` | **Required.** Event ID | Use `/historical-event-data/event-list` to find IDs |
| `year` | **Required.** Calendar year | `2025`, `2026` (more available by request) |
| `file_format` | File format | `json` (default), `csv` |

**Example:**
```
https://feeds.datagolf.com/historical-event-data/events?tour=pga&event_id=14&year=2025&file_format=json&key=API_TOKEN
```

---

## 7. Historical Betting Odds

### Historical Odds Event IDs
List of tournaments and IDs for the historical odds/predictions endpoints. Use to get `event_id` and `year` for the historical outrights and matchups endpoints.

**Endpoint:** `GET /historical-odds/event-list`

| Parameter | Description | Options |
|-----------|-------------|---------|
| `tour` | Tour | `pga` (default), `euro`, `alt` |
| `file_format` | File format | `json` (default), `csv` |

**Example:**
```
https://feeds.datagolf.com/historical-odds/event-list?tour=pga&file_format=json&key=API_TOKEN
```

---

### Historical Outrights
Opening and closing lines for win, top 5, make cut, etc. at 11 sportsbooks. Bet outcomes included.

**Endpoint:** `GET /historical-odds/outrights`

| Parameter | Description | Options |
|-----------|-------------|---------|
| `tour` | Tour | `pga` (default), `euro`, `alt` |
| `event_id` | Event ID or `all` | Use `/historical-odds/event-list`; omit for most recent |
| `year` | Calendar year | `2019`–`2025` (default: `2025`) |
| `market` | **Required.** Market | `win`, `top_5`, `top_10`, `top_20`, `make_cut`, `mc` |
| `book` | **Required.** Sportsbook | `bet365`, `betcris`, `betmgm`, `betonline`, `betway`, `bovada`, `caesars`, `corale`, `circa`, `draftkings`, `fanduel`, `pinnacle`, `skybet`, `sportsbook`, `unibet`, `williamhill` |
| `odds_format` | Odds format | `percent`, `american`, `decimal` (default), `fraction` |
| `file_format` | File format | `json` (default), `csv` |

**Example:**
```
https://feeds.datagolf.com/historical-odds/outrights?tour=pga&event_id=14&year=2020&market=win&book=pinnacle&key=API_TOKEN
```

---

### Historical Match-Ups & 3-Balls
Opening and closing lines for tournament match-ups, round match-ups, and 3-balls at 12 sportsbooks. Bet outcomes included.

**Endpoint:** `GET /historical-odds/matchups`

| Parameter | Description | Options |
|-----------|-------------|---------|
| `tour` | Tour | `pga` (default), `euro`, `alt` |
| `event_id` | Event ID or `all` | Use `/historical-odds/event-list`; omit for most recent |
| `year` | Calendar year | `2019`–`2025` (default: `2025`) |
| `book` | **Required.** Sportsbook | `5dimes`, `bet365`, `betcris`, `betmgm`, `betonline`, `bovada`, `caesars`, `circa`, `draftkings`, `fanduel`, `pinnacle`, `sportsbook`, `williamhill`, `unibet` |
| `odds_format` | Odds format | `percent`, `american`, `decimal` (default), `fraction` |
| `file_format` | File format | `json` (default), `csv` |

**Example:**
```
https://feeds.datagolf.com/historical-odds/matchups?tour=pga&event_id=14&year=2020&book=draftkings&odds_format=decimal&file_format=json&key=API_TOKEN
```

---

## 8. Historical DFS Data

### Historical DFS Event IDs
List of tournaments and IDs for the historical DFS data endpoint.

**Endpoint:** `GET /historical-dfs-data/event-list`

| Parameter | Description | Options |
|-----------|-------------|---------|
| `file_format` | File format | `json` (default), `csv` |

**Example:**
```
https://feeds.datagolf.com/historical-dfs-data/event-list?file_format=json&key=API_TOKEN
```

---

### DFS Points & Salaries
Salaries and ownerships alongside event-level finish, hole, and bonus scoring for PGA and European Tour events on DraftKings and FanDuel.

**Endpoint:** `GET /historical-dfs-data/points`

| Parameter | Description | Options |
|-----------|-------------|---------|
| `tour` | **Required.** Tour | `pga`, `euro` |
| `site` | DFS site | `draftkings` (default), `fanduel` |
| `event_id` | **Required.** Event ID | Use `/historical-dfs-data/event-list` to find IDs |
| `year` | **Required.** Calendar year | `2017`–`2025` |
| `file_format` | File format | `json` (default), `csv` |

**Example:**
```
https://feeds.datagolf.com/historical-dfs-data/points?tour=pga&site=draftkings&event_id=535&year=2021&file_format=json&key=API_TOKEN
```

---

## Tour Code Reference

| Code | Tour |
|------|------|
| `pga` | PGA Tour |
| `euro` | DP World Tour (European Tour) |
| `kft` | Korn Ferry Tour |
| `alt` / `liv` | LIV Golf |
| `opp` | Opposite field PGA Tour event |
| `cha` | Champions Tour |
| `jpn` | Japan Golf Tour |
| `anz` | PGA Tour of Australasia |
| `alp` | Alps Tour |
| `champ` | Major Championships |
| `kor` | Korean Tour |
| `can` | PGA Tour Canada |
| `liv` | LIV Golf |

---

## Notes

- **Required vs Optional:** Parameters marked **Required** must be included. All others have defaults.
- **Event IDs:** Always use the corresponding `/event-list` endpoint to retrieve valid `event_id` values before querying data endpoints.
- **`all` keyword:** Some endpoints accept `event_id=all` to return all events for a given year and tour.
- **Membership:** API access requires a Scratch Plus membership at datagolf.com.
- **Support:** Contact via https://datagolf.com/contact

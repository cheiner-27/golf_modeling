# Tableau Visualization Guide: Golf Feature Engineering Exploration

## Data Connection

Connect to the processed CSVs as a **multi-table data source**:

1. Open Tableau → Connect → Text File → select `data/processed/rounds.csv`
2. Open the Data Source tab, drag in `players.csv` and join on `dg_id = dg_id` (Inner join)
3. Drag in `events.csv` and join on `event_id_year = event_id_year` (Inner join)

This gives you one flat table: rounds enriched with player names and event metadata.

**Key fields you'll use frequently:**
- Dimensions: `player_name`, `event_id_year`, `event_name`, `year`, `round_num`
- Measures: `sg_total`, `sg_putt`, `sg_app`, `sg_ott`, `sg_arg`, `sg_t2g`, `round_score`, `fin_num`

---

## Pre-work: Calculated Fields

Create these before building any charts. Right-click the data pane → Create Calculated Field.

**`Field Size`**
Number of players who started each event (used to assign a penalty finish to CUT players):
```
{ FIXED [Event Id Year] : COUNTD(IF [Round Num] = 1 THEN [Dg Id] END) }
```

**`Finish (Numeric)`**
Assigns CUT players a penalty finish of field size + 1; parses T## and ## finishes to numbers:
```
IF [Fin Text] = "CUT"
THEN [Field Size] + 1
ELSE FLOAT(REGEXP_REPLACE([Fin Text], "[^0-9]", ""))
END
```
Note: WD/DQ rows will return null — filter these out in any chart using this field.

**`Score vs Par`**
```
[Round Score] - [Course Par]
```

**`Event-Round Mean Score`**
```
{ FIXED [Event Id Year], [Round Num] : AVG([Round Score]) }
```

**`Adjusted Round Score`**
```
[Round Score] - [Event-Round Mean Score]
```

**`SG Total (Player Career Avg)`**
```
{ FIXED [Dg Id] : AVG([Sg Total]) }
```

**`Rolling Mean SG (10 events)`**
The actual form feature — player's average SG total over the 10 events prior to the current one. The inner AVG aggregates to the event level; WINDOW_AVG applies the window across events. The -1 offset excludes the current event to prevent data leakage.
```
WINDOW_AVG(AVG([Sg Total]), -10, -1)
```
This is a table calculation. After placing it in the view: right-click → Edit Table Calculation → Specific Dimensions → check `event_id_year` → Restart Every `Dg Id` → Sort by `Start Date` ascending.

Duplicate this field and change the window bounds to experiment with other sizes (e.g., `-5, -1` for 5 events, `-20, -1` for 20 events).

**`Rolling Volatility SG (10 events)`**
Player's SG variability over the prior 10 events — a candidate feature for capturing consistency:
```
WINDOW_STDEV(AVG([Sg Total]), -10, -1)
```
Same table calculation settings as Rolling Mean SG.

---

## Chart 1: Rolling Window Size Comparison

**Purpose:** Determine the right lookback window for your rolling mean SG feature by comparing how well different window sizes predict finish position.

**Setup:**
1. Create three versions of the rolling mean field using different window bounds (see Pre-work): 5 events, 10 events, 20 events
2. For each, build a scatter plot:
   - Columns: `Rolling Mean SG (N events)`
   - Rows: `AVG([Finish (Numeric)])`
   - Mark type: Circle, 15–20% opacity
   - Add a Trend Line (Analytics pane) and display R² in the title
3. Arrange the three sheets side-by-side on a dashboard with consistent axes

**What to look for:** The window size with the highest R² and steepest trend slope is the most predictive. If 5 and 20 events give similar R², prefer the shorter window as it reflects more recent form.

---

## Chart 2: Rolling Mean SG Convergence

**Purpose:** Show how many tournaments it takes for a rolling average to stabilize for a given player.

**Setup:**
1. Filter to 5–8 well-known players with long careers (e.g., Scheffler, McIlroy, Thomas). Add `player_name` to Filters → select your players.
2. Create a row-number field per player ordered by event date. This requires a calculated field:
   ```
   INDEX()
   ```
   This is a table calculation — right-click the field on Rows → Edit Table Calculation → Compute Using: `event_id_year`, Restart Every: `player_name`.
3. Columns: `INDEX()` (rename to "Career Event #")
4. Rows: Running average of `sg_total`:
   - Drag `Sg Total` to Rows
   - Right-click → Quick Table Calculation → Running Average
   - Edit Table Calculation → Compute Using: `event_id_year`, Restart Every: `player_name`
5. Color: `player_name`
6. Mark type: Line

**What to look for:** The point at which each player's line flattens out — typically around event 15–25 — is when the rolling estimate has "enough" data to be reliable.

---

## Chart 3: SG Component Correlation Heatmap

**Purpose:** Check multicollinearity between SG components before deciding whether to include all four or collapse some.

Tableau's native correlation heatmap is limited; the most practical approach:

**Option A — Scatter matrix (Tableau)**
1. Create four separate scatter plots pairing each component combination: `sg_putt` vs `sg_app`, `sg_putt` vs `sg_ott`, `sg_app` vs `sg_ott`, etc.
2. For each: Columns = Component A, Rows = Component B, Mark type = Circle, reduce opacity to 20–30%
3. Add a Trend Line (Analytics pane → Trend Line → Linear) and show the R² in the tooltip
4. Arrange on a single dashboard in a 3×3 grid layout

**Option B — Correlation summary (import)**
Compute a correlation matrix in Python (`rounds[sg_cols].corr()`) and export as CSV. Then in Tableau:
1. Columns: `Var1`, Rows: `Var2`, Color: `Correlation` (diverging red–blue palette, center at 0), Text: `Correlation` rounded to 2 decimals

**What to look for:** Any pair with |r| > 0.7 at the player-event level is a collinearity concern. You'll likely find the components are fairly independent of each other.

---

## Chart 4: SG Component Variance Decomposition

**Purpose:** See which components drive overall performance spread — if one component dominates, it's nearly redundant with `sg_total`.

**Setup:**
1. Create player-level average calculated fields for each component (LOD expressions):
   ```
   { FIXED [Dg Id] : AVG([Sg Putt]) }
   { FIXED [Dg Id] : AVG([Sg App]) }
   { FIXED [Dg Id] : AVG([Sg Ott]) }
   { FIXED [Dg Id] : AVG([Sg Arg]) }
   ```
2. To compare spreads on a single axis, reshape using Tableau's Measure Names/Values:
   - Drag `Measure Names` to Columns
   - Drag `Measure Values` to Rows
   - Filter `Measure Names` to only the four player-avg SG fields
   - Mark type: Box Plot (under the Marks dropdown)

**What to look for:** Components with wider IQRs have more player-differentiating signal. Narrow-IQR components may not be worth including individually.

---

## Chart 5: Event Difficulty Distribution

**Purpose:** Confirm that course/event difficulty is large enough to warrant an adjusted-score feature.

**Setup — Side-by-side distributions:**
1. Create two histograms on a dashboard:

   **Raw score histogram:**
   - Columns: `Round Score` (right-click → Create Bins, bin size = 1)
   - Rows: `CNT(rounds.csv)`
   - Mark type: Bar

   **Adjusted score histogram (same setup but use `Adjusted Round Score`):**
   - Columns: `Adjusted Round Score` bins
   - Rows: `CNT(rounds.csv)`

2. Place both on a dashboard side-by-side with synchronized axes

**What to look for:** If the adjusted histogram is noticeably narrower (lower std), the event-difficulty adjustment is doing real work and worth engineering as a feature.

---

## Chart 6: Event Difficulty vs. Player Skill Interaction

**Purpose:** Test whether top players are buffered from course difficulty — if so, a player×difficulty interaction term is valuable.

**Setup:**
1. Columns: `Score vs Par` (average, aggregated at event level using LOD: `{ FIXED [Event Id Year] : AVG([Score Vs Par]) }`)
2. Rows: `Sg Total` (player average for that event)
3. Mark type: Circle, one mark per player-event
4. Add a reference line at x=0
5. Split by player skill tier: Create a calculated field:
   ```
   IF [SG Total (Player Career Avg)] > 1.5 THEN "Elite"
   ELSEIF [SG Total (Player Career Avg)] > 0.5 THEN "Above Avg"
   ELSE "Field"
   END
   ```
   Drag this to Color
6. Add a Trend Line per color group (Analytics pane → Trend Line → Per Color)

**What to look for:** If the elite tier's trend line is flatter (less negative slope on hard courses) than the field tier's, that's evidence for an interaction feature.

---

## Chart 7: Rolling Mean SG vs. Finish Position

**Purpose:** Validate that the rolling mean SG feature actually predicts finish — the most important chart for confirming form features are worth including.

**Setup:**
1. Columns: `Rolling Mean SG (10 events)` (the table calculation from Pre-work)
2. Rows: `AVG([Finish (Numeric)])`
3. Mark type: Circle, 15–20% opacity — one mark per player-event
4. Add a Trend Line (Analytics pane → Trend Line → Linear)
5. Color by `Player Skill Tier` (the Elite/Above Avg/Field field from Chart 6) to check whether the relationship holds across skill levels

Note: because `Rolling Mean SG` is a table calculation, Tableau requires it to be in the view before it can be placed on an axis. Add it to Detail first if needed, then move to Columns.

**What to look for:** A negative slope (higher rolling SG → lower finish number) confirms the feature is predictive. A flat or near-zero trend means recent SG isn't carrying signal and you may need a longer window or a different aggregation.

---

## Chart 8: Player Volatility vs. Average Finish

**Purpose:** Determine whether a player-level volatility feature (rolling std of SG) adds signal beyond the mean.

**Setup:**
1. Compute player-level SG std as a LOD:
   ```
   { FIXED [Dg Id] : STDEV([Sg Total]) }
   ```
   Name this `Player SG Volatility`
2. Compute player-level average finish:
   ```
   { FIXED [Dg Id] : AVG([Finish (Numeric)]) }
   ```
3. Columns: `Player SG Volatility`, Rows: `Player Avg Finish`
4. One mark per player (aggregate at player level — drag `Dg Id` to Detail)
5. Add a trend line
6. Filter to players with 30+ starts: create a LOD `{ FIXED [Dg Id] : COUNT([Event Id Year]) }` and add it as a filter ≥ 30

**What to look for:** If higher volatility correlates with worse average finish (positive slope, since lower finish number = better), volatility is an independent signal worth including. If no relationship, skip it.

---

## Chart 9: Finish Distribution Shape

**Purpose:** Decide what to model (raw finish, log-finish, binary top-10/win) based on distribution shape.

**Setup:**
1. Columns: `Finish (Numeric)` (bin size = 1), Rows: `CNT`
2. Mark type: Bar
3. Add reference line annotations at x = 1 (win), 5, 10, 25, and the typical cut line (~65–70)

**Bonus — log-transformed version:**
Create `LOG([Finish (Numeric)])` as a calculated field and build the same histogram alongside it on a dashboard.

**What to look for:** The raw finish distribution is right-skewed. If the log version looks approximately normal, log-finish is your best continuous target. If you see a clean mass at the cut line, make-cut is a viable binary classification target.

---

## Chart 10: SG Missingness by Year

**Purpose:** Confirm your usable training window — don't include years where SG data is too sparse.

**Setup:**
1. Columns: `Year`, Rows: each SG field as separate marks
2. The cleanest approach: create a calculated field for each stat:
   ```
   COUNTD(IF NOT ISNULL([Sg Putt]) THEN [Event Id Year] END)
   / COUNTD([Event Id Year])
   ```
   Repeat for each SG component.
3. Place all five completion-rate measures on a single axis using Measure Names/Values
4. Mark type: Line, Color: `Measure Names`
5. Add a reference line at y = 0.80 as a "reliable data" threshold

**What to look for:** The year at which all SG components cross the 80% threshold is your training data start year. Based on prior analysis, this should be around 2017.

---

## Dashboard Layout Suggestion

Organize finished sheets into three dashboards:

| Dashboard | Sheets |
|-----------|--------|
| **Signal Decay** | Window Size Comparison (Chart 1), Rolling Convergence (Chart 2), Rolling Mean vs Finish (Chart 7) |
| **Feature Structure** | Correlation Heatmap (Chart 3), Variance Decomposition (Chart 4), Volatility (Chart 8) |
| **Course & Target** | Difficulty Distribution (Chart 5), Difficulty × Skill (Chart 6), Finish Distribution (Chart 9), Missingness (Chart 10) |

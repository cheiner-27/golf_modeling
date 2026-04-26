"""
Course history features (crs_*).

Computed per (event, course) over all PRIOR rounds at that course
(end_date < event start_date), then aggregated to (event, player) as a
rounds-weighted mean over the courses each player actually played in
the event (handles multi-course events).

  crs_score_to_par_mean_career          — mean per-round score_to_par at this
                                          course historically.
  crs_score_to_par_madecut_mean_career  — same, restricted to rounds played
                                          by event_table survivors (made-cut).
  crs_{sg_cat}_corr_career              — corr(sg_cat, round_score) at this
                                          course over all prior rounds.
                                          NaN until 50 prior rounds exist.
  crs_temp_mean_career                  — mean daily temperature at the
                                          course across prior playings.
  crs_wind_mean_career                  — mean of daily max-wind at the
                                          course across prior playings.
  crs_precip_total_mean_career          — mean of per-event precipitation
                                          totals at the course historically.

Imputed rounds are excluded; weather is per (event_id_year, course_key).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import (
    PROCESSED, SG_CATS, load_events, load_rounds, load_target_index,
    load_weather,
)

CORR_MIN_ROUNDS = 50


def _per_event_course_features(
    rounds_real: pd.DataFrame,
    weather_event_course: pd.DataFrame,
    unique_ec: pd.DataFrame,
) -> pd.DataFrame:
    rounds_by_course = {
        c: g.sort_values("end_date").reset_index(drop=True)
        for c, g in rounds_real.groupby("course_key")
    }
    wx_by_course = {
        c: g.sort_values("start_date").reset_index(drop=True)
        for c, g in weather_event_course.groupby("course_key")
    }

    out_rows = []
    for row in unique_ec.itertuples(index=False):
        ev_id = row.event_id_year
        course = row.course_key
        start = row.start_date

        rec = {
            "event_id_year": ev_id,
            "course_key": course,
            "crs_score_to_par_mean_career": np.nan,
            "crs_score_to_par_madecut_mean_career": np.nan,
            "crs_temp_mean_career": np.nan,
            "crs_wind_mean_career": np.nan,
            "crs_precip_total_mean_career": np.nan,
        }
        for cat in SG_CATS:
            rec[f"crs_{cat}_corr_career"] = np.nan

        if course in rounds_by_course:
            crs_r = rounds_by_course[course]
            prior = crs_r[crs_r["end_date"] < start]
            if len(prior):
                rec["crs_score_to_par_mean_career"] = float(prior["score_to_par"].mean())
                mc = prior[prior["made_cut"]]
                if len(mc):
                    rec["crs_score_to_par_madecut_mean_career"] = float(mc["score_to_par"].mean())
                if len(prior) >= CORR_MIN_ROUNDS:
                    for cat in SG_CATS:
                        pair = prior[[cat, "round_score"]].dropna()
                        if len(pair) >= CORR_MIN_ROUNDS:
                            rec[f"crs_{cat}_corr_career"] = float(pair.corr().iloc[0, 1])

        if course in wx_by_course:
            crs_w = wx_by_course[course]
            prior_w = crs_w[crs_w["start_date"] < start]
            if len(prior_w):
                rec["crs_temp_mean_career"] = float(prior_w["temp_mean"].mean())
                rec["crs_wind_mean_career"] = float(prior_w["wind_mean"].mean())
                rec["crs_precip_total_mean_career"] = float(prior_w["precip_total"].mean())

        out_rows.append(rec)

    return pd.DataFrame(out_rows)


def build() -> pd.DataFrame:
    target = load_target_index()
    rounds_real = load_rounds()
    rounds_real = rounds_real[~rounds_real["is_imputed_round"].astype(bool)].copy()

    et_keys = pd.read_csv(
        PROCESSED / "event_table.csv", usecols=["event_id_year", "dg_id"]
    )
    et_keys["made_cut"] = True
    rounds_real = rounds_real.merge(et_keys, on=["event_id_year", "dg_id"], how="left")
    rounds_real["made_cut"] = rounds_real["made_cut"].fillna(False)

    weather = load_weather()
    events_df = load_events()[["event_id_year", "start_date"]]
    weather_event_course = (
        weather.groupby(["event_id_year", "course_key"], as_index=False)
        .agg(
            temp_mean=("temperature_mean_c", "mean"),
            wind_mean=("wind_speed_max_kmh", "mean"),
            precip_total=("precipitation_mm", "sum"),
        )
        .merge(events_df, on="event_id_year", how="left")
    )

    ep_courses = (
        rounds_real.groupby(["event_id_year", "dg_id", "course_key"], as_index=False)
        .agg(rounds_at_course=("round_num", "size"))
    )

    unique_ec = (
        target[["event_id_year", "start_date"]].drop_duplicates()
        .merge(
            ep_courses[["event_id_year", "course_key"]].drop_duplicates(),
            on="event_id_year", how="inner",
        )
    )

    feat_ec = _per_event_course_features(rounds_real, weather_event_course, unique_ec)
    feat_cols = [c for c in feat_ec.columns if c.startswith("crs_")]

    merged = ep_courses.merge(
        feat_ec, on=["event_id_year", "course_key"], how="left"
    )

    # Rounds-weighted mean over courses, per (event, player)
    agg_inputs = {}
    for col in feat_cols:
        num_col = f"__num_{col}"
        den_col = f"__den_{col}"
        merged[num_col] = merged[col] * merged["rounds_at_course"]
        merged[den_col] = merged["rounds_at_course"].where(merged[col].notna(), 0)
        agg_inputs[num_col] = "sum"
        agg_inputs[den_col] = "sum"

    agg = (
        merged.groupby(["event_id_year", "dg_id"], as_index=False)
        .agg(agg_inputs)
    )
    for col in feat_cols:
        num = agg[f"__num_{col}"]
        den = agg[f"__den_{col}"].replace(0, np.nan)
        agg[col] = num / den
    agg = agg[["event_id_year", "dg_id", *feat_cols]]

    return target[["event_id_year", "dg_id"]].merge(
        agg, on=["event_id_year", "dg_id"], how="left"
    )

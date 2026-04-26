#!/usr/bin/env python3
"""
Builds data/processed/features.csv — one row per (event_id_year, dg_id),
keyed identically to event_table.csv. Columns are grouped by prefix:

  tgt_  target
  ctx_  event context (field size)
  plr_  player history
  rcn_  player recency (event-level)
  rst_  player rust / cadence
  crs_  course history
  fld_  field aggregates (mean/std of plr_, rcn_)
  rel_  player vs field z-scores
  exp_  expected (rank by prior skill)
  res_  residual (actual − expected, historical median)

See reports/feature_groups.yaml for the column-by-column index.

Run with: python src/build_features.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from features import context, course, expected, field, player, recent_rust, relative, target
from features.base import PROCESSED, load_target_index


def _log_shape(name: str, df: pd.DataFrame) -> None:
    n_cols = sum(1 for c in df.columns if c not in ("event_id_year", "dg_id"))
    print(f"  {name:>14s}: {len(df):>7,} rows, {n_cols:>3d} cols")


def main() -> None:
    print("=== Building features.csv ===\n")

    target_idx = load_target_index()[["event_id_year", "dg_id"]]
    print(f"Target index : {len(target_idx):,} rows ({target_idx['event_id_year'].nunique()} events)\n")

    print("Per-starter features (universe = all starters in eligible events):")
    plr = player.build()
    _log_shape("plr_", plr)
    rcn = recent_rust.build()
    _log_shape("rcn_+rst_", rcn)

    per_starter = plr.merge(rcn, on=["event_id_year", "dg_id"], how="outer")
    _log_shape("per_starter", per_starter)

    print("\nField + relative + expected:")
    fld = field.build(per_starter)
    _log_shape("fld_", fld)
    rel = relative.build(per_starter, fld)
    _log_shape("rel_", rel)
    exp = expected.build(per_starter)
    _log_shape("exp_+res_", exp)

    print("\nTarget-keyed features:")
    tgt = target.build()
    _log_shape("tgt_", tgt)
    ctx = context.build()
    _log_shape("ctx_", ctx)
    crs = course.build()
    _log_shape("crs_", crs)

    print("\nJoining onto target index ...")
    out = target_idx.copy()
    for df, key in [
        (tgt, ["event_id_year", "dg_id"]),
        (ctx, ["event_id_year", "dg_id"]),
        (crs, ["event_id_year", "dg_id"]),
        (plr, ["event_id_year", "dg_id"]),
        (rcn, ["event_id_year", "dg_id"]),
        (exp, ["event_id_year", "dg_id"]),
        (rel, ["event_id_year", "dg_id"]),
        (fld, ["event_id_year"]),
    ]:
        out = out.merge(df, on=key, how="left")

    print(f"  final: {len(out):,} rows, {out.shape[1]} cols")

    n_dups = out.duplicated(subset=["event_id_year", "dg_id"]).sum()
    assert n_dups == 0, f"duplicate keys after join: {n_dups}"
    assert len(out) == len(target_idx), \
        f"row-count drift: {len(out)} vs {len(target_idx)}"

    path = PROCESSED / "features.csv"
    out.to_csv(path, index=False)
    print(f"\n  saved -> data/processed/features.csv  ({len(out):,} rows, {out.shape[1]} cols)")
    print("\n=== Done ===")


if __name__ == "__main__":
    main()

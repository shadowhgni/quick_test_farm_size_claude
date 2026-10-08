#!/usr/bin/env python3
"""
Independent check of v9 step 6: for sampled cells, rebuild every season's dry spells straight from
the CHIRPS cache (runs of days < DRY_MM inside [onset + EXCLUDE_FIRST, demise - EXCLUDE_LAST],
missing days break runs, runs >= SPELL_STATS_MIN) with plain Python, take the per-cell medians,
and compare with cells_spell_stats.nc. Also checks that the pooled "ALL" season counts equal the
number of valid seasons of the cells used. Exits 1 on any difference.

  python tests/check_spell_stats.py --region ci_nga --cells 12
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import v9_common as C   # noqa: E402


def runs(dry):
    out, s = [], None
    for i, d in enumerate(list(dry) + [False]):
        if d and s is None:
            s = i
        elif not d and s is not None:
            out.append((s, i - 1))
            s = None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="ci_nga")
    ap.add_argument("--name", default=None)
    ap.add_argument("--cells", type=int, default=12)
    a = ap.parse_args()
    rdir = C.region_dir(a.region)
    out = rdir / "step06" / (a.name or a.region)
    ds = xr.open_dataset(out / "cells_spell_stats.nc")
    cm = C.read_json(C.data_dir("chirps", a.region, "meta.json"))
    lat, lon = np.array(cm["lat"]), np.array(cm["lon"])
    mm = np.memmap(C.data_dir("chirps", a.region, "rain_u16.dat"), dtype=np.uint16, mode="r",
                   shape=(cm["n_days"], len(lat), len(lon)))
    has = np.load(rdir / "step03" / "day_has_data.npy")
    ok = np.argwhere(np.isfinite(ds.n_spells_mean.values))
    pick = ok[np.random.default_rng(5).choice(len(ok), min(a.cells, len(ok)), replace=False)]
    bad = n_seas = 0
    for i, j in pick:
        la, lo = float(ds.lat[i]), float(ds.lon[j])
        r, c = int(np.abs(lat - la).argmin()), int(np.abs(lon - lo).argmin())
        se = pd.read_parquet(rdir / "step03" / "seasons", filters=[("row", "=", r), ("col", "=", c)])
        se = se[se.valid]
        x = np.asarray(mm[:, r, c]).astype(np.int64)
        dry_day = (x != 65535) & has & (x < round(C.DRY_MM * 100))
        rec = {k: [] for k in ("n", "fs", "fl", "ls", "ll", "gs", "gl", "md")}
        dem_col = "demise_rain_date" if C.SPELL_STATS_DEMISE == "rain" else "demise_date"
        for s in se.itertuples():
            on = int(C.day_index(np.array([s.onset_date], dtype="datetime64[D]"))[0])
            de = int(C.day_index(np.array([getattr(s, dem_col)], dtype="datetime64[D]"))[0])
            w0, w1 = on + C.SPELL_STATS_EXCLUDE_FIRST, de - C.SPELL_STATS_EXCLUDE_LAST
            sp = [(on_ + w0 - on, e + w0 - on) for on_, e in runs(dry_day[w0:w1 + 1]) if e - on_ + 1 >= C.SPELL_STATS_MIN] \
                if w1 >= w0 else []
            rec["n"].append(len(sp))
            if sp:
                L = [e - b + 1 for b, e in sp]
                k = int(np.argmax(L))                       # first maximum = earliest longest
                rec["fs"].append(sp[0][0]), rec["fl"].append(L[0])
                rec["gs"].append(sp[k][0]), rec["gl"].append(L[k])
                rec["md"].append(float(np.median(L)))
                if len(sp) >= 2:
                    rec["ls"].append(sp[-1][0]), rec["ll"].append(L[-1])
        n_seas += len(se)

        def med(v, need):
            return float(np.median(v)) if len(v) >= need else np.nan
        mine = {"n_spells_median": med(rec["n"], C.MIN_VALID_SEASONS),
                "first_start_median": med(rec["fs"], C.SPELL_STATS_MIN_COND),
                "first_len_median": med(rec["fl"], C.SPELL_STATS_MIN_COND),
                "last_start_median": med(rec["ls"], C.SPELL_STATS_MIN_COND),
                "last_len_median": med(rec["ll"], C.SPELL_STATS_MIN_COND),
                "longest_start_median": med(rec["gs"], C.SPELL_STATS_MIN_COND),
                "longest_len_median": med(rec["gl"], C.SPELL_STATS_MIN_COND),
                "spell_len_median": med(rec["md"], C.SPELL_STATS_MIN_COND),
                "p_ge1": float(np.mean(np.array(rec["n"]) >= 1)), "p_ge2": float(np.mean(np.array(rec["n"]) >= 2))}
        for k, v in mine.items():
            got = float(ds[k].values[i, j])
            if not (np.isclose(got, v, atol=1e-5) or (np.isnan(got) and np.isnan(v))):
                bad += 1
                print(f"MISMATCH {k} at {la:.3f},{lo:.3f}: step6 {got} vs loop {v}")
    # pooled counts
    zs = pd.read_csv(out / "summary_by_zone.csv")
    allz = zs[(zs.zone == "ALL") & (zs.metric == "n_spells")].iloc[0]
    st = C.read_json(out / "status.json")
    n_used = int(np.nansum(ds.n_seasons.values[np.isfinite(ds.n_spells_mean.values)]))
    if allz.n_seasons != n_used or allz.n_defined != n_used:
        bad += 1
        print(f"MISMATCH pooled seasons {allz.n_seasons} vs cells {n_used}")
    print(f"checked {len(pick)} cells, {n_seas} seasons, pooled {allz.n_seasons:,} seasons "
          f"({st['n_seasons']:,} valid in the target); differences {bad}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

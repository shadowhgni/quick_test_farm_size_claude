#!/usr/bin/env python3
"""
CI check of v9 step 3 (seasons) on the Nigeria box. Exits 1 on any failure.

1. Independent re-computation: for sampled cells, rebuild the 365-day climatology, the
   smoothed cycle, the rainfall regime, the final regime (with the cell's NDVI season count from
   step 2), the major-season window, every year's onset / rainfall demise and the false start /
   false demise flags with plain Python loops straight from the CHIRPS cache, and compare with
   step 3 outputs. The NDVI demise adjustment is checked for consistency (adjusted = rainfall
   demise + shift, 0 <= shift <= DEMISE_SHIFT_MAX, one shift per cell with "median_offset").
2. Known sites (only when the grid covers them): the regime of well-documented places, and
   onset/demise dates within broad bounds consistent with the CHIRPS monthly means there
   (e.g. Kano: almost no rain before May, most rain Jun-Sep).

  python tests/check_seasons.py --region ci_nga --cells 6
"""
import argparse
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import v9_common as C

spec = importlib.util.spec_from_file_location("s3", HERE / "v9_03_spells_seasons.py")
S2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S2)

# regime expected from the CHIRPS climatology (calibration sites of v8)
SITES = {  # name: (lat, lon, allowed regimes, onset bounds (MM-DD), demise bounds (MM-DD))
    "Kano": (12.00, 8.52, {C.REGIME_UNI}, ("05-01", "07-10"), ("08-25", "10-31")),
    "Sokoto": (13.06, 5.24, {C.REGIME_UNI}, ("05-10", "07-20"), ("08-25", "10-31")),
    "Maiduguri": (11.85, 13.16, {C.REGIME_UNI}, ("05-10", "07-20"), ("08-25", "10-31")),
    "Abuja": (9.07, 7.48, {C.REGIME_UNI}, ("03-15", "05-31"), ("09-20", "11-30")),
    "Ibadan": (7.38, 3.93, {C.REGIME_BI}, ("02-15", "05-15"), ("06-15", "08-31")),
    "Lagos": (6.52, 3.38, {C.REGIME_BI}, ("02-15", "05-15"), ("06-15", "08-31")),
    "Ilorin": (8.50, 4.55, {C.REGIME_BI, C.REGIME_TRANSITION}, ("03-01", "05-31"), ("06-15", "09-15")),
    "Port Harcourt": (4.82, 7.03, {C.REGIME_TRANSITION, C.REGIME_BI}, ("01-15", "05-15"), ("07-01", "12-15")),
    "Enugu": (6.45, 7.50, {C.REGIME_TRANSITION, C.REGIME_BI}, ("02-15", "05-15"), ("07-01", "12-15")),
    "Makurdi": (7.73, 8.54, {C.REGIME_UNI, C.REGIME_TRANSITION}, ("03-01", "05-31"), ("09-15", "11-30")),
}


def mmdd(doy):
    return (np.datetime64("2001-01-01") + np.timedelta64(int(round(doy)), "D")).astype(str)[5:]


def in_bounds(doy, lo, hi):
    d = mmdd(doy)
    return lo <= d <= hi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="ci_nga")
    ap.add_argument("--cells", type=int, default=6)
    a = ap.parse_args()
    root = C.region_dir(a.region) / "step03"
    gm = xr.open_dataset(root / "grid_meta.nc")
    cm = C.read_json(C.data_dir("chirps", a.region, "meta.json"))
    lat, lon = np.array(cm["lat"]), np.array(cm["lon"])
    shape = (cm["n_days"], len(lat), len(lon))
    mm = np.memmap(C.data_dir("chirps", a.region, "rain_u16.dat"), dtype=np.uint16, mode="r", shape=shape)
    has = np.load(root / "day_has_data.npy")
    dates = C.ORIGIN + np.arange(shape[0]).astype("timedelta64[D]")
    years = dates.astype("datetime64[Y]").astype(int) + 1970
    doy = S2.noleap_doy(dates)
    bad = 0
    n_shift = []
    W = C.FALSE_WINDOW_DAYS

    def false_flag(rain, d0):
        seg = [rain[t] if 0 <= t < len(rain) else np.nan for t in range(d0, d0 + W)]
        dry = [(not np.isnan(x)) and x < C.DRY_MM for x in seg]
        if C.FALSE_DRY_MODE == "total":
            return sum(dry) >= C.FALSE_DRY_DAYS
        best = run = 0
        for x in dry:
            run = run + 1 if x else 0
            best = max(best, run)
        return best >= C.FALSE_DRY_DAYS

    # ---- 1. independent re-computation for sampled cells (+ the named sites)
    ok_cells = np.argwhere(gm.reason.values == C.REASON_OK)
    rng = np.random.default_rng(3)
    pick = [tuple(x) for x in ok_cells[rng.choice(len(ok_cells), min(a.cells, len(ok_cells)), replace=False)]]
    for la, lo_, *_ in SITES.values():
        if lat.min() <= la <= lat.max() and lon.min() <= lo_ <= lon.max():
            pick.append((int(np.abs(lat - la).argmin()), int(np.abs(lon - lo_).argmin())))
    rows = sorted({r for r, _ in pick})
    se = pd.read_parquet(root / "seasons", filters=[("row", "in", rows)])
    n_seasons = 0
    for r, c in pick:
        x = np.asarray(mm[:, r, c]).astype(np.int64)
        miss = (x == 65535) | ~has
        rain = np.where(miss, np.nan, x / 100.0)
        clim = np.array([np.nanmean(rain[(doy == k) & (years >= C.CLIM_YEAR_MIN) & (years <= C.CLIM_YEAR_MAX)])
                         for k in range(365)])
        md = np.nanmean(clim)
        h = C.REGIME_SMOOTH_DAYS // 2
        sc = np.array([np.mean(np.take(np.nan_to_num(clim, nan=md), range(k - h, k + h + 1), mode="wrap"))
                       for k in range(365)])
        nd = int(gm.ndvi_n_seasons.values[r, c]) if "ndvi_n_seasons" in gm else 0
        reg = S2.regime_one(sc, max(nd, 0))
        if md * 365 < C.ARID_MM:
            continue
        if reg["regime"] != int(gm.regime.values[r, c]) or reg["start"] != int(gm.window_start_doy.values[r, c]) \
                or reg["length"] != int(gm.window_len.values[r, c]) \
                or reg["rain_regime"] != int(gm.rain_regime.values[r, c]):
            bad += 1
            print(f"MISMATCH regime/window at row {r} col {c}: loop {reg} vs grid "
                  f"{int(gm.regime.values[r, c])}/{gm.window_start_doy.values[r, c]}/{gm.window_len.values[r, c]}")
        ref = np.mean(np.nan_to_num(clim, nan=md)[(reg["start"] + np.arange(reg["length"])) % 365])
        mine = {}
        for y in range(C.SEASON_YEAR_MIN - 1, C.SEASON_YEAR_MAX + 1):
            s = int(S2.doy_to_index(np.array([y]), np.array([reg["start"]]))[0])
            L = reg["length"]
            seg = np.array([rain[t] if 0 <= t < shape[0] else np.nan for t in range(s, s + L)])
            hs = np.array([has[t] if 0 <= t < shape[0] else False for t in range(s, s + L)])
            if hs.mean() < 0.95:
                continue
            S = np.cumsum(np.where(np.isnan(seg), 0.0, seg - ref))
            kmin = int(np.argmin(S))
            if kmin == 0 or kmin >= L - 1:
                continue
            kmax = kmin + 1 + int(np.argmax(S[kmin + 1:]))
            if S[kmax] <= S[kmin]:
                continue
            on, de = s + kmin + 1, s + kmax
            if not (C.SEASON_LEN_MIN <= de - on + 1 <= C.SEASON_LEN_MAX):
                continue
            oy = int(str(C.index_to_date(on))[:4])
            if oy in mine or not (C.SEASON_YEAR_MIN <= oy <= C.SEASON_YEAR_MAX):
                continue
            mine[oy] = (str(C.index_to_date(on)), str(C.index_to_date(de)), false_flag(rain, on), false_flag(rain, de - W + 1))
        cand = se[(se.row == r) & (se.col == c) & se.reason.isin([C.S_OK, C.S_FALSE_START, C.S_FALSE_DEMISE])]
        got = {int(y): (str(o.date()), str(d.date()), bool(fs), bool(fd))
               for y, o, d, fs, fd in zip(cand.year, pd.to_datetime(cand.onset_date),
                                          pd.to_datetime(cand.demise_rain_date), cand.false_start, cand.false_demise)}
        # exclusion flags
        for y, (_, _, fs, fd) in mine.items():
            row = cand[cand.year == y]
            if len(row):
                want = (C.S_FALSE_START if (fs and C.FALSE_START_EXCLUDE) else
                        C.S_FALSE_DEMISE if (fd and C.FALSE_DEMISE_EXCLUDE) else C.S_OK)
                if int(row.reason.iloc[0]) != want:
                    bad += 1
                    print(f"MISMATCH exclusion row {r} col {c} year {y}: reason {int(row.reason.iloc[0])} vs {want}")
        # NDVI demise adjustment: consistency
        v = se[(se.row == r) & (se.col == c) & se.valid]
        sh = (pd.to_datetime(v.demise_date) - pd.to_datetime(v.demise_rain_date)).dt.days
        if len(v) and (not (sh == v.demise_shift).all() or sh.min() < 0 or sh.max() > C.DEMISE_SHIFT_MAX
                       or (C.DEMISE_ADJUST == "median_offset" and sh.nunique() > 1)
                       or (C.DEMISE_ADJUST == "none" and sh.max() > 0)):
            bad += 1
            print(f"MISMATCH demise shift row {r} col {c}: {sorted(sh.unique())[:5]}")
        n_shift.extend(sh.tolist())
        n_seasons += len(mine)
        if got != mine:
            bad += 1
            diff = sorted(set(got.items()) ^ set(mine.items()))[:4]
            print(f"MISMATCH seasons at row {r} col {c}: {len(got)} vs {len(mine)}; e.g. {diff}")
    print(f"re-computed {len(pick)} cells, {n_seasons} seasons; demise shift (d) over their valid seasons: "
          f"median {np.median(n_shift) if n_shift else float('nan'):.0f}, max {max(n_shift) if n_shift else 0}")

    # ---- 2. known sites (expectations are about RAINFALL: rainfall regime, onset, rainfall demise;
    # when NDVI changes the regime only the onset is checked and the change is reported)
    for name, (la, lo_, regs, onb, deb) in SITES.items():
        if not (lat.min() <= la <= lat.max() and lon.min() <= lo_ <= lon.max()):
            continue
        r, c = int(np.abs(lat - la).argmin()), int(np.abs(lon - lo_).argmin())
        rreg, reg = int(gm.rain_regime.values[r, c]), int(gm.regime.values[r, c])
        on = float(gm.onset_doy_median.values[r, c])
        v = se[(se.row == r) & (se.col == c) & se.valid]
        dr = pd.to_datetime(v.demise_rain_date)
        de = float(np.median(S2.noleap_doy(dr.values.astype("datetime64[D]")))) if len(v) else np.nan
        same = reg == rreg
        ok = rreg in regs and in_bounds(on, *onb) and (not same or (np.isfinite(de) and in_bounds(de, *deb)))
        bad += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {name:<14} rain {C.REGIME_LABELS[rreg]:<11} final {C.REGIME_LABELS[reg]:<11} "
              f"trough ratio {float(gm.trough_ratio.values[r, c]):.2f}  NDVI seasons "
              f"{int(gm.ndvi_n_seasons.values[r, c])}  onset {mmdd(on)} (expected {onb[0]}..{onb[1]})  "
              f"rain demise {mmdd(de) if np.isfinite(de) else '-'} ({deb[0]}..{deb[1]}{'' if same else ', not checked'})  "
              f"demise shift {float(gm.demise_shift_median.values[r, c]):.0f} d  "
              f"seasons {int(gm.n_valid_seasons.values[r, c])}")
    print(f"failures: {bad}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

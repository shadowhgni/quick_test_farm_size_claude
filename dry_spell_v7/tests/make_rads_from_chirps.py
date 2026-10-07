#!/usr/bin/env python3
"""
Rebuild RADS-style onset / demise files from a CHIRPS daily file, using the method of
the RADS code (Bombardi et al. 2019, https://github.com/rjbombardi/onset_demise_rainy_season,
rainyseason.py + rainyseason_onset.py + rainyseason_demise.py), on PENTADS like the
"africa_RainyAndDrySeason.pentad.CHIRPS.YYYY.nc" files used on the HPC:

  * pentad means (73 per year, 29 Feb folded into the pentad of 28 Feb);
  * mean annual cycle; explained variance of harmonics 1-3; a cell is MASKED when the
    2nd or 3rd harmonic explains >= the 1st (bimodal / trimodal regime);
  * t0 = pentad of the minimum of (mean + 1st harmonic);
  * onset  = pentad after the minimum of the cumulative anomaly over the half year
             starting at t0 (Liebmann & Marengo 2001 first pass);
  * demise = same, computed backwards in time from the next t0;
  * outliers (> 1.5 IQR from the circular median) removed; cells with > 33 % of
    years missing are masked.
The B17 second pass of the original code is NOT reproduced (seasons it would recover
stay missing). This is a stand-in for the real RADS files, which are only distributed
through a Dropbox folder that a CI job cannot list.

Output: one file per reference year with dims (reference_year, latitude, longitude),
variables onset_date, demise_date (datetime64, NaT = missing), onset_pentad,
demise_pentad, durwet, totwet, durdry, totdry - same names as the HPC files.

  python make_rads_from_chirps.py chirps_data_cache/chirps_NGA_1981_2025.nc chirps_africa --y0 1981 --y1 2024
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

NP = 73          # pentads per year
HALF = NP // 2   # 36: half-year search window (int(tot/2) in the original)


def pentad_series(ds, rows_per_block=16):
    """Daily (time, lat, lon) -> pentad means (mm/day), computed in latitude strips to bound memory.
    Days are sorted, so pentad sums use reduceat."""
    da = ds["rainfall"]
    t = pd.DatetimeIndex(da.time.values)
    noleap_doy = t.dayofyear - ((t.is_leap_year) & (t.dayofyear > 59)).astype(int)   # 29 Feb -> 59
    p = (np.minimum(noleap_doy, 365) - 1) // 5                                          # 0..72
    pid = np.asarray((t.year - t.year.min()) * NP + p)
    starts = np.r_[0, np.nonzero(np.diff(pid))[0] + 1]
    n_pent = int(pid.max()) + 1
    ny, nx = da.shape[1:]
    pen = np.full((n_pent, ny, nx), np.nan, np.float32)
    for r0 in range(0, ny, rows_per_block):
        x = da.isel(latitude=slice(r0, r0 + rows_per_block)).values.astype(np.float32, copy=False)
        fin = np.isfinite(x) & (x >= 0)                                                 # -9999 / NaN = missing
        s = np.add.reduceat(np.where(fin, x, 0), starts, axis=0, dtype=np.float64)
        c = np.add.reduceat(fin, starts, axis=0, dtype=np.int32)
        with np.errstate(invalid="ignore", divide="ignore"):
            pen[pid[starts], r0:r0 + x.shape[1]] = np.where(c > 0, s / np.maximum(c, 1), np.nan)
    years = t.year.min() + np.arange(n_pent) // NP
    return pen, years, np.arange(n_pent) % NP


def harmonics(cycle):
    """cycle (NP, ncell) -> coef a,b (3, ncell), explained variance (3, ncell); as Harmonics()."""
    m = cycle.shape[0]
    tt = np.arange(1, m + 1)
    svar = ((cycle - cycle.mean(0)) ** 2).sum(0) / (m - 1)
    A, B, H = [], [], []
    for k in range(1, 4):
        a = (cycle * np.cos(2 * np.pi * k * tt / m)[:, None]).sum(0) * 2 / m
        b = (cycle * np.sin(2 * np.pi * k * tt / m)[:, None]).sum(0) * 2 / m
        with np.errstate(invalid="ignore", divide="ignore"):
            H.append(m * (a ** 2 + b ** 2) / (2 * (m - 1) * svar))
        A.append(a)
        B.append(b)
    return np.array(A), np.array(B), np.array(H)


def qc_circular(pent, tot=NP, k=1.5):
    """Drop dates further than k*IQR from the circular median (as in rainyseason.py)."""
    ok = pent >= 0
    if ok.sum() < 2:
        return pent
    ang = pent[ok] * 2 * np.pi / tot
    med = np.arctan2(np.median(np.sin(ang)), np.median(np.cos(ang))) * tot / (2 * np.pi)
    med = med + tot if med < 0 else med
    dev = np.where(ok, pent - med, 0.0)
    dev = np.where(dev > tot / 2, dev - tot, dev)
    dev = np.where(dev < -tot / 2, dev + tot, dev)
    iqr = np.percentile(dev[ok], 75) - np.percentile(dev[ok], 25)
    out = pent.copy()
    out[ok & (np.abs(dev) > iqr * k)] = -1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chirps")
    ap.add_argument("outdir")
    ap.add_argument("--y0", type=int, default=1981)
    ap.add_argument("--y1", type=int, default=2024)
    a = ap.parse_args()

    ds = xr.open_dataset(a.chirps)
    lat, lon = ds.latitude.values, ds.longitude.values
    pen, pyear, ppos = pentad_series(ds)
    ds.close()
    T, ny, nx = pen.shape
    P = pen.reshape(T, -1)
    ncell = P.shape[1]
    nmiss = np.isnan(P).mean(0)
    valid = nmiss <= 0.25                                         # dper = 25 %
    rm = np.nanmean(P, 0)
    cycle = np.full((NP, ncell), np.nan, np.float64)
    for k in range(NP):
        cycle[k] = np.nanmean(P[ppos == k], 0)
    cycle = np.nan_to_num(cycle)
    A, B, H = harmonics(cycle)
    bimodal = (H[1] >= H[0]) | (H[2] >= H[0])
    tt = np.arange(1, NP + 1)
    h1 = rm[None, :] + A[0][None, :] * np.cos(2 * np.pi * tt / NP)[:, None] + B[0][None, :] * np.sin(2 * np.pi * tt / NP)[:, None]
    t0 = np.argmin(h1, 0)                                          # pentad-of-year of the minimum
    use = valid & ~bimodal & (rm > 0)
    print(f"cells {ncell:,}: valid {valid.sum():,}, bimodal/trimodal masked {(valid & bimodal).sum():,}, used {use.sum():,}")

    anom = np.nan_to_num(P) - np.where(np.isfinite(rm), rm, 0)[None, :]
    anom[np.isnan(P)] = 0.0                                        # missing -> no anomaly ("prec[prec<0]=0" analogue)
    years = list(range(a.y0, a.y1 + 1))
    Y = len(years)
    on_idx = np.full((Y, ncell), -1, np.int64)
    de_idx = np.full((Y, ncell), -1, np.int64)
    ar = np.arange(HALF)
    for c in np.nonzero(use)[0]:
        S = np.nonzero(ppos == t0[c])[0]
        S = S[S < T - 5]
        if len(S) < 2:
            continue
        # onset: forward half-year cumulative anomaly from each t0
        win = S[:, None] + ar[None, :]
        inside = win < T
        cs = np.cumsum(np.where(inside, anom[np.minimum(win, T - 1), c], 0), axis=1)
        cs = np.where(inside, cs, np.inf)
        k = np.argmin(cs, 1)
        on = S + k + 1
        on = np.where(k + 1 < HALF, on, -1)
        # demise of the season that started at S[i]: backwards from S[i+1]
        wb = S[1:, None] - ar[None, :]
        csb = np.cumsum(anom[np.maximum(wb, 0), c], axis=1)
        kb = np.argmin(csb, 1)
        de = np.where(kb + 1 < HALF, S[1:] - (kb + 1), -1)
        de = np.r_[de, -1]
        # QC (pentad of year, circular)
        on_p = np.where(on >= 0, ppos[np.clip(on, 0, T - 1)], -1)
        de_p = np.where(de >= 0, ppos[np.clip(de, 0, T - 1)], -1)
        on = np.where(qc_circular(on_p.astype(float)) >= 0, on, -1)
        de = np.where(qc_circular(de_p.astype(float)) >= 0, de, -1)
        if np.mean(on < 0) > 0.33 or np.mean(de < 0) > 0.33:
            continue
        for i in range(len(S)):
            if on[i] < 0 or de[i] < 0 or de[i] <= on[i]:
                continue
            ry = int(pyear[on[i]])                                 # reference year = year of onset
            if a.y0 <= ry <= a.y1 and on_idx[ry - a.y0, c] < 0:
                on_idx[ry - a.y0, c] = on[i]
                de_idx[ry - a.y0, c] = de[i]

    # pentad index -> first calendar day of that pentad
    first_day = np.array([np.datetime64(f"{pyear[i]}-01-01") + np.timedelta64(int(ppos[i]) * 5, "D")
                          for i in range(T)])
    # pentads after 28 Feb start one day later in leap years
    leap = pd.DatetimeIndex(first_day).is_leap_year & (ppos >= 12)
    first_day = first_day + leap.astype("timedelta64[D]")
    asc = np.argsort(lat)                                          # write ascending latitudes, like the HPC files
    Path(a.outdir).mkdir(parents=True, exist_ok=True)
    # wet-season total from pentad means (5 days per pentad; leap-year pentad 12 has 6)
    cum = np.vstack([np.zeros((1, ncell), np.float32), np.cumsum(np.nan_to_num(P) * 5, 0, dtype=np.float32)])
    for yi, y in enumerate(years):
        o, d = on_idx[yi], de_idx[yi]
        ok = (o >= 0) & (d >= 0)
        od = np.where(ok, first_day[np.clip(o, 0, T - 1)], np.datetime64("NaT", "D"))
        dd = np.where(ok, first_day[np.clip(d, 0, T - 1)], np.datetime64("NaT", "D"))
        durwet = np.where(ok, (dd - od).astype("timedelta64[D]").astype(float), np.nan)
        totwet = np.full(ncell, np.nan)
        if ok.any():
            cells = np.nonzero(ok)[0]
            totwet[cells] = cum[d[cells], cells] - cum[o[cells], cells]
        def grid(v):
            return v.reshape(ny, nx)[asc][None]
        out = xr.Dataset(
            {"onset_date": (("reference_year", "latitude", "longitude"), grid(od.astype("datetime64[ns]"))),
             "demise_date": (("reference_year", "latitude", "longitude"), grid(dd.astype("datetime64[ns]"))),
             "onset_pentad": (("reference_year", "latitude", "longitude"),
                              grid(np.where(ok, ppos[np.clip(o, 0, T - 1)] + 1.0, np.nan))),
             "demise_pentad": (("reference_year", "latitude", "longitude"),
                               grid(np.where(ok, ppos[np.clip(d, 0, T - 1)] + 1.0, np.nan))),
             "durwet": (("reference_year", "latitude", "longitude"), grid(durwet)),
             "totwet": (("reference_year", "latitude", "longitude"), grid(totwet)),
             "durdry": (("reference_year", "latitude", "longitude"), grid(np.full(ncell, np.nan))),
             "totdry": (("reference_year", "latitude", "longitude"), grid(np.full(ncell, np.nan)))},
            coords={"reference_year": [y], "latitude": lat[asc].astype(np.float32),
                    "longitude": lon.astype(np.float32)},
            attrs={"note": "RADS-style seasons rebuilt from CHIRPS with the first pass of the RADS "
                           "algorithm (CI stand-in, not the official RADS files)"})
        out.to_netcdf(Path(a.outdir) / f"africa_RainyAndDrySeason.pentad.CHIRPS.{y}.nc")
        if yi % 10 == 0 or y == years[-1]:
            o_doy = pd.DatetimeIndex(od[ok]).dayofyear if ok.any() else []
            print(f"  {y}: seasons {ok.sum():,} cells; onset DOY median "
                  f"{np.median(o_doy) if len(o_doy) else float('nan'):.0f}; durwet median "
                  f"{np.nanmedian(durwet) if ok.any() else float('nan'):.0f} d")
    print(f"written {Y} files to {a.outdir}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v9 STEP 7 - what changes between scenarios (season source, exclusion windows, NDVI ...)
=======================================================================================

Compares scenarios of one region (each run by run_all.py --scenarios ... into
dryspell_v9/<region>/<scenario>/) against a BASE scenario (the first one):

  1. seasons, season by season: every (cell, season year) valid in the base AND in the other scenario
     -> onset and RAINFALL demise differences in days (other - base; the NDVI demise shift is a separate
     setting and is not part of this comparison); per cell: share of base seasons also valid
     in the other scenario, median onset / demise / length differences.
  2. per-cell layers side by side (step 3 grid_meta.nc, step 5 cells_spell_stats.nc of the region):
     median onset / demise / season length, number of valid seasons, number of dry spells per season,
     P(>= 1 spell), start / duration of the 1st and longest spell, dry share - with difference maps.
  3. tables by zone and latitude band (step 5 summaries of every scenario in one file).

Outputs: dryspell_v9/<region>/compare/<name>/
  scenarios.csv                    the settings that differ between the scenarios
  season_differences_by_cell.nc    per-cell differences of 1. (one layer set per other scenario)
  season_differences.csv           distribution (p10, p25, median, p75, p90) of the differences of 1.
  layers_by_latitude.csv           medians over cells of the layers of 2., per latitude band and scenario
  spell_stats_by_zone.csv, spell_stats_by_latitude.csv   step 5 summaries of all scenarios
  png/compare_<layer>.png          one panel per scenario + difference panels (other - base)
  png/season_shift_<other>.png     maps of the median onset / demise / length differences of 1.

  python v9_07_compare.py --region ci_nga --scenarios base chirps mask_bimodal excl0
"""

import argparse
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import v9_common as C   # noqa: E402

logger = logging.getLogger("dryspell_v9")

LAYERS = [   # (file, variable, title, unit, colour scale, circular day of year?)
    ("step03", "onset_doy_median", "Median onset", "day of year", "brand_teal", True),
    ("step03", "demise_rain_doy_median", "Median rainfall demise", "day of year", "brand_teal", True),
    ("step03", "demise_doy_median", "Median demise used (after the NDVI shift, if any)", "day of year", "brand_teal", True),
    ("step03", "season_len_median", "Median season length", "days", "brand_green", False),
    ("step03", "n_valid_seasons", "Valid seasons", "seasons", "brand_green", False),
    ("step05", "n_spells_mean", "Mean number of dry spells per season", "spells / season", "brand_risk", False),
    ("step05", "n_spells_median", "Median number of dry spells per season", "spells / season", "brand_risk", False),
    ("step05", "p_ge1", "P(at least one dry spell)", "probability", "brand_risk", False),
    ("step05", "first_start_median", "Median start of the 1st dry spell", "days after onset", "brand_teal", False),
    ("step05", "longest_len_median", "Median duration of the longest dry spell", "days", "brand_risk", False),
    ("step05", "dry_frac_median", "Median share of the season in dry spells", "fraction", "brand_risk", False),
]


def load_layer(region, scen, where, var):
    if where == "step03":
        p = C.region_dir(region, scen) / "step03" / "grid_meta.nc"
    else:
        p = C.region_dir(region, scen) / "step05" / region / "cells_spell_stats.nc"
    if not p.exists():
        return None
    with xr.open_dataset(p) as d:
        if var not in d:
            return None
        if where == "step03":
            ok = d["reason"].values == C.REASON_OK
            return np.where(ok, d[var].values.astype(float), np.nan), d.lat.values, d.lon.values
        return d[var].values.astype(float), d.lat.values, d.lon.values


def on_region_grid(arr, lat, lon, glat, glon):
    """Place a (sub-)grid on the region grid."""
    out = np.full((len(glat), len(glon)), np.nan)
    i0 = int(np.abs(glat - lat[0]).argmin())
    j0 = int(np.abs(glon - lon[0]).argmin())
    out[i0:i0 + len(lat), j0:j0 + len(lon)] = arr
    return out


def circ_diff(a, b):
    """a - b for days of year, wrapped to -182..182."""
    return (a - b + 182.5) % 365 - 182.5


def season_differences(region, base, other, nlat, nlon):
    """Season-by-season comparison over the step 3 parquet parts (same partitioning in both)."""
    import pyarrow.parquet as pq
    bdir = C.region_dir(region, base) / "step03" / "seasons"
    odir = C.region_dir(region, other) / "step03" / "seasons"
    cols = ["row", "col", "year", "onset_date", "demise_rain_date", "valid"]   # rainfall season (no NDVI shift)
    acc = {k: np.full((nlat, nlon), np.nan, np.float32) for k in
           ("matched_share", "onset_diff_median", "demise_diff_median", "length_diff_median", "n_base", "n_other")}
    allv = {"onset": [], "demise": [], "length": []}
    for pb in sorted(bdir.glob("part_*.parquet")):
        po = odir / pb.name
        if not po.exists():
            continue
        b = pq.read_table(pb, columns=cols).to_pandas()
        o = pq.read_table(po, columns=cols).to_pandas()
        b, o = b[b.valid], o[o.valid]
        for d in (b, o):
            d["on"] = pd.to_datetime(d.onset_date).values.astype("datetime64[D]").astype(np.int64)
            d["de"] = pd.to_datetime(d.demise_rain_date).values.astype("datetime64[D]").astype(np.int64)
        m = b.merge(o[["row", "col", "year", "on", "de"]], on=["row", "col", "year"], suffixes=("_b", "_o"))
        m["d_on"], m["d_de"] = m.on_o - m.on_b, m.de_o - m.de_b
        m["d_len"] = m.d_de - m.d_on
        nb = b.groupby(["row", "col"]).size()
        no = o.groupby(["row", "col"]).size()
        nm = m.groupby(["row", "col"]).size()
        for ser, key in ((nb, "n_base"), (no, "n_other")):
            if len(ser):
                r, c = np.array(ser.index.tolist()).T
                acc[key][r, c] = ser.values
        if len(nb):
            share = (nm.reindex(nb.index).fillna(0) / nb)
            r, c = np.array(share.index.tolist()).T
            acc["matched_share"][r, c] = share.values
        if len(m):
            med = m.groupby(["row", "col"])[["d_on", "d_de", "d_len"]].median()
            r, c = np.array(med.index.tolist()).T
            acc["onset_diff_median"][r, c] = med.d_on.values
            acc["demise_diff_median"][r, c] = med.d_de.values
            acc["length_diff_median"][r, c] = med.d_len.values
            allv["onset"].append(m.d_on.values)
            allv["demise"].append(m.d_de.values)
            allv["length"].append(m.d_len.values)
    rows = []
    for k, v in allv.items():
        v = np.concatenate(v) if v else np.zeros(0)
        q = np.percentile(v, [10, 25, 50, 75, 90]) if len(v) else [np.nan] * 5
        rows.append({"other": other, "variable": f"{k} difference (other - base), days", "n_seasons": len(v),
                     "share_identical": float((v == 0).mean()) if len(v) else np.nan,
                     "p10": q[0], "p25": q[1], "median": q[2], "p75": q[3], "p90": q[4],
                     "mean": float(v.mean()) if len(v) else np.nan})
    return acc, rows


def panel_maps(path, title, unit, cmap, arrays, labels, diffs, lat, lon, bnd):
    """Top row: each scenario (shared colour scale); bottom row: other - base (diverging)."""
    C.brand_style()
    import matplotlib.pyplot as plt
    n = len(arrays)
    extent = [lon.min() - 0.025, lon.max() + 0.025, lat.min() - 0.025, lat.max() + 0.025]
    aspect = (extent[3] - extent[2]) / (extent[1] - extent[0])
    w = 3.2
    fig, axes = plt.subplots(2, n, figsize=(w * n + 1.0, 2 * w * aspect + 1.2), squeeze=False)
    fin = np.concatenate([a[np.isfinite(a)] for a in arrays]) if arrays else np.zeros(0)
    vmin, vmax = (np.percentile(fin, 2), np.percentile(fin, 98)) if len(fin) else (0, 1)
    dfin = np.concatenate([np.abs(d[np.isfinite(d)]) for d in diffs if d is not None] or [np.zeros(1)])
    dmax = max(np.percentile(dfin, 98), 1e-6) if len(dfin) else 1
    im = imd = None
    for k in range(n):
        ax = axes[0, k]
        im = ax.imshow(arrays[k][::-1], extent=extent, cmap=cmap, vmin=vmin, vmax=vmax, interpolation="nearest")
        ax.set_title(labels[k], fontsize=9, loc="left")
        ax2 = axes[1, k]
        if diffs[k] is not None:
            imd = ax2.imshow(diffs[k][::-1], extent=extent, cmap="brand_div", vmin=-dmax, vmax=dmax,
                             interpolation="nearest")
            ax2.set_title(f"{labels[k]} - {labels[0]}", fontsize=9, loc="left")
        else:
            ax2.set_axis_off()
        for a_ in (ax, ax2):
            if bnd is not None and len(bnd) and a_.axison:
                bnd.boundary.plot(ax=a_, color=C.INK, linewidth=0.3)
            a_.set_xlim(extent[:2])
            a_.set_ylim(extent[2:])
            a_.set_xticks([])
            a_.set_yticks([])
            a_.set_xlabel("")
            a_.set_ylabel("")
    cb = fig.colorbar(im, ax=axes[0].tolist(), shrink=0.8, pad=0.01)
    cb.set_label(unit, fontsize=8)
    if imd is not None:
        cb2 = fig.colorbar(imd, ax=axes[1].tolist(), shrink=0.8, pad=0.01)
        cb2.set_label(f"difference ({unit})", fontsize=8)
    fig.suptitle(title, x=0.01, ha="left", fontsize=10)
    fig.savefig(path, dpi=C.FIG_DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", default="ci_nga")
    ap.add_argument("--scenarios", nargs="+", required=True, help="first = base")
    ap.add_argument("--name", default=None, help="output folder (default: the scenario names joined)")
    a = ap.parse_args()
    base, others = a.scenarios[0], a.scenarios[1:]
    name = a.name or "_vs_".join(a.scenarios)[:120]
    out = Path(C.OUT_ROOT) / a.region / "compare" / name
    out.mkdir(parents=True, exist_ok=True)
    C.setup_logging(out / "step07.log")
    t0 = time.time()
    missing = [s for s in a.scenarios if not (C.region_dir(a.region, s) / "step03" / "grid_meta.nc").exists()]
    if missing:
        sys.exit(f"scenarios without step 3 results: {missing} - run run_all.py --scenarios {' '.join(missing)}")
    logger.info("=" * 70)
    logger.info(f"v9 STEP7 compare  region={a.region}  base={base}  others={others}")
    logger.info("=" * 70)

    # ---- settings that differ
    sets = {s: C.scenario_settings(s) for s in a.scenarios}
    keys = sorted(k for k in sets[base] if k not in ("SCENARIOS",) and
                  any(str(sets[s].get(k)) != str(sets[base].get(k)) for s in a.scenarios))
    pd.DataFrame([{"setting": k, **{s: sets[s].get(k) for s in a.scenarios}} for k in keys]) \
        .to_csv(out / "scenarios.csv", index=False)
    for k in keys:
        logger.info(f"  {k:<28} " + "  ".join(f"{s}={sets[s].get(k)}" for s in a.scenarios))

    with xr.open_dataset(C.region_dir(a.region, base) / "step03" / "grid_meta.nc") as g:
        glat, glon = g.lat.values, g.lon.values
    meta = C.read_json(C.region_dir(a.region, base) / "step03" / "meta.json")
    bnd = C.load_boundaries(meta["bbox"])
    png = out / "png"
    png.mkdir(parents=True, exist_ok=True)

    # ---- 1. season by season
    rows, dv = [], {}
    for o in others:
        acc, r = season_differences(a.region, base, o, len(glat), len(glon))
        rows += r
        for k, v in acc.items():
            dv[f"{o}__{k}"] = (("lat", "lon"), v)
        for rr in r:
            logger.info(f"  {o}: {rr['variable']}: median {rr['median']:.0f}, IQR {rr['p25']:.0f}..{rr['p75']:.0f}, "
                        f"identical {rr['share_identical']:.0%} of {rr['n_seasons']:,} seasons valid in both")
        panel_maps(png / f"season_shift_{o}.png",
                   f"Season by season, {o} - {base} (median over the seasons valid in both)", "days", "brand_div",
                   [acc["onset_diff_median"], acc["demise_diff_median"], acc["length_diff_median"]],
                   ["onset shift", "demise shift", "length change"], [None, None, None], glat, glon, bnd)
    if dv:
        xr.Dataset(dv, coords={"lat": glat, "lon": glon}, attrs={"base": base}).to_netcdf(
            out / "season_differences_by_cell.nc", encoding={k: {"zlib": True} for k in dv})
    pd.DataFrame(rows).to_csv(out / "season_differences.csv", index=False)

    # ---- 2. layers side by side
    band = np.floor(glat / C.LAT_BAND_DEG) * C.LAT_BAND_DEG
    lrows = []
    for where, var, title, unit, cmap, circ in LAYERS:
        arrs = []
        for s in a.scenarios:
            r = load_layer(a.region, s, where, var)
            arrs.append(None if r is None else on_region_grid(r[0], r[1], r[2], glat, glon))
        if arrs[0] is None or all(x is None for x in arrs[1:]):
            continue
        labs = [s for s, x in zip(a.scenarios, arrs) if x is not None]
        arrs = [x for x in arrs if x is not None]
        diffs = [None] + [(circ_diff(x, arrs[0]) if circ else x - arrs[0]) for x in arrs[1:]]
        panel_maps(png / f"compare_{var}.png", f"{title} - scenarios (top) and difference to {labs[0]} (bottom)",
                   unit, cmap, arrs, labs, diffs, glat, glon, bnd)
        for s, x in zip(labs, arrs):
            for b_ in list(np.unique(band)) + ["ALL"]:
                sel = np.isfinite(x) & ((band[:, None] == b_) if b_ != "ALL" else True)
                if sel.any():
                    lrows.append({"layer": var, "scenario": s, "latitude_band":
                                  b_ if b_ == "ALL" else f"{b_:g} to {b_ + C.LAT_BAND_DEG:g}",
                                  "n_cells": int(sel.sum()), "median": float(np.median(x[sel])),
                                  "mean": float(np.mean(x[sel]))})
    pd.DataFrame(lrows).to_csv(out / "layers_by_latitude.csv", index=False)

    # ---- 3. step 5 summaries
    for kind in ("zone", "latitude"):
        parts = []
        for s in a.scenarios:
            p = C.region_dir(a.region, s) / "step05" / a.region / f"summary_by_{kind}.csv"
            if p.exists():
                parts.append(pd.read_csv(p).assign(scenario=s))
        if parts:
            pd.concat(parts, ignore_index=True).to_csv(out / f"spell_stats_by_{kind}.csv", index=False)
    lr = pd.DataFrame(lrows)
    if len(lr):
        allr = lr[lr.latitude_band == "ALL"].pivot(index="layer", columns="scenario", values="median")
        logger.info("  medians over all cells:\n" + allr.reindex(columns=[s for s in a.scenarios if s in allr]).round(2)
                    .to_string())
    logger.info(f"STEP7 done in {(time.time() - t0) / 60:.1f} min -> {out}")


if __name__ == "__main__":
    main()

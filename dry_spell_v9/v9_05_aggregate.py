#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v9 STEP 5 - aggregate the per-country step 4 results into one SSA folder
========================================================================

Reads every COUNTRY folder dryspell_v9/<region>/step04/<ISO3>/ written by v9_04_sowing_risk.py
(bbox / polygon / point runs are ignored) and builds dryspell_v9/<region>/step04/<SSA_NAME>/ :

  countries.csv            status of every country (ok / skipped + why / missing), cell counts
  country_summary.csv      national rows (zone == ALL) of every country, crop x cycle x sow
  country_zone_summary.csv every country x zone row (zones = SUMMARY_ZONES: aez8 / koppen / ...)
  ssa_summary.csv          SSA pooled, per zone and "ALL" (cell-weighted means over countries)
  ssa_stage_hits.csv       SSA pooled P(longest dry spell hits stage), per zone and "ALL"
  ssa_regime_summary.csv   SSA pooled per rainfall regime (unimodal / transition / bimodal)
  ssa_cells_<crop>.nc      mosaic of all countries on the step 3 grid (cycle, sow, [stage], lat, lon)
  png/                     SSA stage heatmaps (+ per zone), maps, zone curves, country comparison

Pooling: a mean over cells of several countries = sum(mean_c * n_c) / sum(n_c), with n_c the
number of cells behind each country mean (columns n_* written by step 4), so the SSA value
equals the mean over all SSA cells. Country medians (longest_*_median) cannot be pooled
exactly: the SSA columns *_median_wmean are cell-weighted means of country medians.

Usage
-----
  python v9_05_aggregate.py --region ssa
  python v9_05_aggregate.py --region study --name WA --countries NGA BEN GHA
"""

import argparse
import importlib.util
import json
import logging
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import v9_common as C

_spec = importlib.util.spec_from_file_location("step4", HERE / "v9_04_sowing_risk.py")
S4 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S4)

warnings.filterwarnings("ignore", category=RuntimeWarning)
logger = logging.getLogger("dryspell_v9")

KEYS = ["crop", "cycle", "sow"]


# =============================================================================
# TABLES
# =============================================================================

def wmean(df, value, weight):
    w = df[weight].where(df[value].notna(), 0)
    return (df[value].fillna(0) * w).sum() / w.sum() if w.sum() > 0 else np.nan


def pool_summary(rows):
    """Cell-weighted pooling of step 4 zone_summary rows (one group)."""
    n = rows.n_cells.sum()
    npos = rows.n_cells_possible.sum()
    return pd.Series({
        "n_countries": rows.iso3.nunique(), "n_cells": n, "n_cells_possible": npos,
        "pct_cells_impossible": 100 * (n - npos) / n if n else np.nan,
        "p_feasible_mean": wmean(rows, "p_feasible_mean", "n_cells"),
        "p_spell_mean": wmean(rows, "p_spell_mean", "n_cells_with_p"),
        "p_hit_window_mean": wmean(rows, "p_hit_window_mean", "n_cells_with_p"),
        "window_overlap_days_mean": wmean(rows, "window_overlap_days_mean", "n_cells_with_p"),
        "longest_len_median_wmean": wmean(rows, "longest_len_median", "n_cells_with_spell"),
        "longest_start_das_median_wmean": wmean(rows, "longest_start_das_median", "n_cells_with_spell"),
        "longest_end_das_median_wmean": wmean(rows, "longest_end_das_median", "n_cells_with_spell"),
        "n_cells_with_p": rows.n_cells_with_p.sum(),
    })


def pool_stage_hits(sh):
    g = sh.assign(pw=sh.p * sh.n_cells).groupby(KEYS + ["zone", "stage_idx", "stage"], as_index=False)
    out = g.agg(pw=("pw", "sum"), n_cells=("n_cells", "sum"))
    out["p"] = out.pw / out.n_cells.where(out.n_cells > 0)
    return out.drop(columns="pw")


# =============================================================================
# MOSAIC
# =============================================================================

def mosaic(crop, countries, sdir, lat, lon, iso_index):
    """Place every country's cells_<crop>.nc on the region grid (cells inside the country only)."""
    first = xr.open_dataset(sdir / countries[0] / f"cells_{crop}.nc")
    cycles, sows, stages = first.cycle.values, first.sow.values, first.stage.values
    first.close()
    nC, nS, nst = len(cycles), len(sows), len(stages)
    shp = (len(lat), len(lon))
    f32 = {k: np.full((nC, nS) + shp, np.nan, np.float32)
           for k in ("p_feasible", "p_spell", "p_hit_window", "longest_len_median", "longest_start_das_median")}
    impossible = np.full((nC, nS) + shp, -1, np.int8)
    most_hit = np.full((nC, nS) + shp, -1, np.int8)
    p_stage = np.full((nC, nS, nst) + shp, 255, np.uint8)          # percent, 255 = no data
    reason = np.full(shp, 1, np.uint8)                              # 1 = outside the countries
    iso = np.full(shp, -1, np.int16)
    zone = np.full(shp, -1, np.int16)
    regime = np.full(shp, 0, np.int8)
    for c in countries:
        with xr.open_dataset(sdir / c / f"cells_{crop}.nc") as d:
            if list(d.stage.values) != list(stages) or list(d.cycle.values) != list(cycles) \
                    or list(d.sow.values) != list(sows):
                raise ValueError(f"{c}: crop {crop} was run with other cycles / sowing dates / stages")
            ii = np.searchsorted(lat, d.lat.values[0])
            jj = np.searchsorted(lon, d.lon.values[0])
            if not (np.isclose(lat[ii], d.lat.values[0]) and np.isclose(lon[jj], d.lon.values[0])):
                raise ValueError(f"{c}: grid does not match the step 1 grid")
            h, w = d.sizes["lat"], d.sizes["lon"]
            box = (slice(ii, ii + h), slice(jj, jj + w))
            inside = d.reason.values != 1
            reason[box] = np.where(inside, d.reason.values, reason[box])
            iso[box] = np.where(inside, iso_index[c], iso[box])
            zone[box] = np.where(inside, d.zone.values, zone[box])
            regime[box] = np.where(inside, d.regime.values, regime[box])
            for k, a in f32.items():
                a[(slice(None), slice(None)) + box] = np.where(inside, d[k].values, a[(slice(None), slice(None)) + box])
            impossible[(slice(None), slice(None)) + box] = np.where(
                inside & (d.reason.values == 0), d.impossible.values, impossible[(slice(None), slice(None)) + box])
            ph = d.p_hit_stage.values                                  # (nC, nS, nst, h, w)
            pct = np.where(np.isfinite(ph), np.round(ph * 100), 255).astype(np.uint8)
            sel = (slice(None),) * 3 + box
            p_stage[sel] = np.where(inside, pct, p_stage[sel])
            with np.errstate(invalid="ignore"):
                mh = np.where(np.all(np.isnan(ph), 2), -1, np.nanargmax(np.where(np.isnan(ph), -1, ph), 2))
            most_hit[(slice(None), slice(None)) + box] = np.where(inside, mh, most_hit[(slice(None), slice(None)) + box])
    dv = {k: (("cycle", "sow", "lat", "lon"), v) for k, v in f32.items()}
    dv["impossible"] = (("cycle", "sow", "lat", "lon"), impossible)
    dv["most_hit_stage_idx"] = (("cycle", "sow", "lat", "lon"), most_hit)
    dv["p_hit_stage_pct"] = (("cycle", "sow", "stage", "lat", "lon"), p_stage)
    dv["reason"] = (("lat", "lon"), reason)
    dv["iso3_idx"] = (("lat", "lon"), iso)
    dv["zone"] = (("lat", "lon"), zone)
    dv["regime"] = (("lat", "lon"), regime)
    return xr.Dataset(dv, coords={"cycle": cycles, "sow": sows, "stage": stages, "lat": lat, "lon": lon})


def is_country(p):
    """step04 sub-folder written for a country (not a bbox / polygon / point run)."""
    st = p / "status.json"
    if not st.exists():
        return False
    s = json.loads(st.read_text())
    return (s.get("target") or {}).get("kind") == "country"


# =============================================================================
# FIGURES
# =============================================================================

def plot_country_comparison(path, crop, cs, cycles, sows, value, title, cmap):
    """Countries (rows) x cycle|sowing (columns) heatmap of one national value."""
    plt = S4._plt()
    t = cs[cs.crop == crop]
    if t.empty:
        return
    cols = [(L, s) for L in cycles for s in sows]
    piv = t.pivot_table(index="iso3", columns=["cycle", "sow"], values=value).reindex(columns=cols)
    piv = piv.loc[sorted(piv.index)]
    vmax = max(0.1, float(np.ceil(np.nanmax(piv.values) * 10) / 10)) if np.isfinite(piv.values).any() else 1.0
    fig, ax = plt.subplots(figsize=(1.0 + 0.42 * len(cols), 1.6 + 0.24 * len(piv)))
    im = ax.imshow(piv.values, cmap=cmap, vmin=0, vmax=vmax, aspect="auto", interpolation="nearest")
    ax.set_yticks(range(len(piv)))
    ax.set_yticklabels(piv.index, fontsize=7)
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels([f"+{s}" for _, s in cols], fontsize=6, rotation=90)
    for k, L in enumerate(cycles):
        ax.axvline(k * len(sows) - 0.5, color="white", linewidth=2)
        ax.text(k * len(sows) + (len(sows) - 1) / 2, 1.01, f"{L}-day cycle", ha="center", va="bottom",
                fontsize=8, transform=ax.get_xaxis_transform())
    ax.set_xlabel("sowing, days after onset (grouped by cycle length)", fontsize=8)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, shrink=0.6, pad=0.01)
    cb.set_label(value.replace("_", " "), fontsize=8)
    cb.outline.set_visible(False)
    ax.set_title(f"{S4.CROPS[crop]['label']} - {title}", loc="left", fontsize=10, pad=22)
    fig.savefig(path, dpi=C.FIG_DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# =============================================================================
# MAIN
# =============================================================================

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", default="ssa")
    ap.add_argument("--name", default=C.SSA_NAME, help="output sub-folder of step04/")
    ap.add_argument("--countries", nargs="*", default=None, help="default: every country folder of step04/")
    ap.add_argument("--no_mosaic", action="store_true", help="tables and charts only (no ssa_cells_*.nc, no maps)")
    a = ap.parse_args()

    rdir = C.region_dir(a.region)
    sdir = rdir / "step04"
    out = sdir / a.name
    C.setup_logging(out / "step05.log")
    t0 = time.time()
    found = sorted(p.name for p in sdir.iterdir() if p.is_dir() and p.name != a.name and is_country(p))
    wanted = a.countries or found
    rows = []
    for c in wanted:
        st = sdir / c / "status.json"
        if not st.exists():
            rows.append({"unit": c, "iso3": c, "status": "missing"})
            continue
        s = json.loads(st.read_text())
        if s.get("status") == "ok" and not (sdir / c / "zone_summary.csv").exists():
            s["status"] = "incomplete"
        rows.append(s)
    status = pd.DataFrame(rows)
    out.mkdir(parents=True, exist_ok=True)
    status.to_csv(out / "countries.csv", index=False)
    ok = status.loc[status.status == "ok", "unit"].tolist()
    logger.info("=" * 70)
    logger.info(f"v9 STEP5  region={a.region}  countries ok {len(ok)}, skipped "
                f"{(status.status == 'skipped').sum()}, missing/incomplete "
                f"{status.status.isin(['missing', 'incomplete']).sum()}")
    logger.info("=" * 70)
    if not ok:
        sys.exit("no country with step 4 results")

    # ---- tables
    summ = pd.concat([pd.read_csv(sdir / c / "zone_summary.csv") for c in ok], ignore_index=True)
    sh = pd.concat([pd.read_csv(sdir / c / "zone_stage_hits.csv") for c in ok], ignore_index=True)
    schemes = sorted(summ.zone_scheme.unique())
    if len(schemes) > 1:
        sys.exit(f"countries were summarised with different zones {schemes} - rerun step 4 with one --zones")
    summ["iso3"], sh["iso3"] = summ.unit, sh.unit
    logger.info(f"  zones: {schemes[0]}")
    st_df = pd.read_csv(sdir / ok[0] / "stage_windows.csv")
    crops = sorted(summ.crop.unique())
    cycles = sorted(summ.cycle.unique())
    sows_abs = sorted(summ.sow.unique())
    day0 = int(min(sows_abs))
    sows = [s - day0 for s in sows_abs]

    country = summ[summ.zone == "ALL"].copy()
    country.to_csv(out / "country_summary.csv", index=False)
    summ[summ.zone != "ALL"].to_csv(out / "country_zone_summary.csv", index=False)

    parts = []
    for grp, df in ((KEYS + ["zone"], summ[summ.zone != "ALL"]), (KEYS + ["zone"], summ[summ.zone == "ALL"])):
        for key, rows_ in df.groupby(grp):
            parts.append(pool_summary(rows_).to_frame().T.assign(**dict(zip(grp, key))))
    ssa = pd.concat(parts, ignore_index=True)[KEYS + ["zone"] + list(pool_summary(summ.head(1)).index)]
    for col in ("n_countries", "n_cells", "n_cells_possible", "n_cells_with_p", "cycle", "sow"):
        ssa[col] = ssa[col].astype(int)
    ssh = pool_stage_hits(sh)
    ssh = ssh.merge(st_df[["crop", "cycle", "stage_idx", "stage_name", "das_start", "das_end", "overlaps_window"]],
                    on=["crop", "cycle", "stage_idx"], how="left")
    # most hit stage: highest p (rounded to 1e-9, so that platform rounding never decides), ties -> earliest stage
    top = ssh.assign(_p=ssh.p.round(9)).sort_values(["_p", "stage_idx"], ascending=[False, True], kind="mergesort").drop(columns="_p").groupby(KEYS + ["zone"]).head(1)
    top = top[KEYS + ["zone", "stage", "stage_name", "das_start", "das_end", "p"]].rename(
        columns={"stage": "most_hit_stage", "stage_name": "most_hit_stage_name",
                 "das_start": "most_hit_das_start", "das_end": "most_hit_das_end", "p": "most_hit_p"})
    ssa = ssa.merge(top, on=KEYS + ["zone"], how="left").merge(
        st_df.groupby(["crop", "cycle"]).first()[["window_das_start", "window_das_end", "window_stages"]].reset_index(),
        on=["crop", "cycle"], how="left")
    ssa.to_csv(out / "ssa_summary.csv", index=False)
    rs = pd.concat([pd.read_csv(sdir / c / "regime_summary.csv") for c in ok
                    if (sdir / c / "regime_summary.csv").exists()], ignore_index=True)
    rs["iso3"] = rs.unit
    if len(rs):
        rparts = [pool_summary(r).to_frame().T.assign(**dict(zip(KEYS + ["regime"], k)))
                  for k, r in rs.groupby(KEYS + ["regime"])]
        pd.concat(rparts, ignore_index=True).to_csv(out / "ssa_regime_summary.csv", index=False)
    ssh.to_csv(out / "ssa_stage_hits.csv", index=False)
    logger.info("Written countries.csv, country_summary.csv, country_zone_summary.csv, ssa_summary.csv, "
                "ssa_stage_hits.csv")

    # ---- figures from tables
    png = out / "png"
    png.mkdir(exist_ok=True)
    zone_order = [x for x in sorted(ssa.zone.unique()) if x != "ALL"] + ["ALL"]
    for c in crops:
        for az in zone_order:
            h = ssh[(ssh.crop == c) & (ssh.zone == az)].assign(sow=lambda d: d.sow - day0)
            if h.empty:
                continue
            tag = a.name if az == "ALL" else az
            S4.plot_stage_heatmaps(png / f"stage_hits_{c}_{S4._slug(tag)}.png", c, st_df, h, cycles, sows, day0,
                                   f"{tag}: P(longest dry spell hits stage), mean over possible cells")
        S4.plot_zone_curves(png / f"zone_window_hit_{c}.png", c, ssa.assign(sow=ssa.sow - day0), cycles, sows,
                           day0, zone_order)
        plot_country_comparison(png / f"countries_window_hit_{c}.png", c, country, cycles, sows_abs,
                                "p_hit_window_mean", "P(longest dry spell hits the vulnerable window), national mean",
                                "Purples")
        plot_country_comparison(png / f"countries_impossible_{c}.png", c,
                                country.assign(share_impossible=country.pct_cells_impossible / 100), cycles,
                                sows_abs, "share_impossible", "share of cells where the cycle cannot be completed",
                                "Greys")

    # ---- mosaic + maps
    if not a.no_mosaic:
        with xr.open_dataset(rdir / "step03" / "grid_meta.nc") as g:
            lat, lon = g.lat.values, g.lon.values
        iso_index = {c: i for i, c in enumerate(ok)}
        bnd = C.load_boundaries(C.read_json(rdir / "step03" / "meta.json")["bbox"])
        if bnd is not None:
            bnd = bnd[bnd.iso_a3.isin(ok)]
        for c in crops:
            ds = mosaic(c, ok, sdir, lat, lon, iso_index)
            inside = ds.reason.values != 1
            rr, cc = np.nonzero(inside)
            ds = ds.isel(lat=slice(rr.min(), rr.max() + 1), lon=slice(cc.min(), cc.max() + 1))
            ds.attrs.update({"crop": c, "countries": " ".join(ok),
                             "iso3_idx": "index into the 'countries' attribute",
                             "reason": "0 ok, 1 outside the countries, 2 no usable CHIRPS, 3 no/too few valid seasons",
                             "regime": str(C.REGIME_LABELS),
                             "p_hit_stage_pct": "percent, 255 = no data"})
            ds.to_netcdf(out / f"ssa_cells_{c}.nc",
                         encoding={v: {"zlib": True, "complevel": 4} for v in ds.data_vars})
            analysed = ds.reason.values == 0
            S4.plot_window_maps(png / f"map_window_hit_{c}.png", c, ds, cycles, sows, day0,
                                ds.lon.values, ds.lat.values, bnd, analysed)
            del ds
        logger.info("Written ssa_cells_<crop>.nc and maps")

    # ---- digest
    nat = ssa[ssa.zone == "ALL"]
    for c in crops:
        logger.info(f"--- {c} ({a.name}, possible cells, {len(ok)} countries) ---")
        for r in nat[nat.crop == c].itertuples():
            logger.info(f"  {r.cycle:>3} d  sow +{r.sow:<3} impossible {r.pct_cells_impossible:5.1f}%  "
                        f"P(hit window) {r.p_hit_window_mean:.2f}  most hit: {r.most_hit_stage} "
                        f"({r.most_hit_stage_name}) p={r.most_hit_p:.2f}")
    logger.info(f"STEP5 done in {(time.time() - t0) / 60:.1f} min -> {out}")


if __name__ == "__main__":
    main()

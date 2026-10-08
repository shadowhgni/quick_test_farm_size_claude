#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v9 STEP 4 - sowing date x crop x cycle -> which stages does the LONGEST dry spell hit?
=====================================================================================

TARGET (one of, all on the grid of the region processed by steps 1-3):
  --iso3 NGA                          a country (Natural Earth boundaries)
  --bbox W S E N                      every cell whose centre is inside the box
  --polygon FILE [--polygon_field F --polygon_value V]
                                      a polygon file (.gpkg/.shp/.geojson; optionally one feature);
                                      cells whose centre is inside, or every touched cell if none is
  --point LAT LON                     the single grid cell containing the point (+ season_detail.csv)

For every valid grid cell of the target and every valid MAJOR season (v9_03_spells_seasons.py:
onset from CHIRPS with the RADS method, demise optionally adjusted to the NDVI end of season,
false starts / demises optionally excluded; bimodal cells: major season only):

  sowing day  S = onset + DAY0 + sow        sow in SOW_OFFSETS
  maturity    M = S + cycle - 1             cycle in CYCLES
  DAS         days after sowing, sowing day = DAS 0, maturity = DAS cycle-1

  * FEASIBLE season: M <= demise + DEMISE_GRACE and every day of [S, M] has rainfall data.
    Cell IMPOSSIBLE for a (crop, cycle, sow) when fewer than FEASIBLE_MIN_FRAC of its valid
    seasons are feasible.
  * Dry spells (< DRY_MM, missing days break spells) are clipped to [S, M] and kept if the
    clipped length >= MIN_SPELL_CROP[crop]. The longest one per season (ties -> earliest) is
    located in DAS and compared with every stage (HIT = >= 1 shared day; all hit stages count)
    and with the crop's most vulnerable window.
  * Probabilities are over FEASIBLE seasons; a season without a qualifying spell = "not hit".

Summary ZONES (SUMMARY_ZONES in v9_config.py or --zones):
  aez8    HarvestChoice AEZ, 8 classes (warm / cool x arid / semiarid / subhumid / humid)
  aez     HarvestChoice AEZ, all 3-digit classes
  koppen  Koppen-Geiger 1991-2020 (Beck et al. 2023)
  regime  rainfall regime (unimodal / transition / bimodal)
  FILE    any class raster (.tif/.asc/.zip, --zone_legend code,label CSV) or vector (--zone_field)
Results are always also summarised per rainfall regime.

Inputs: dryspell_v9/<region>/step03/ (spells, seasons, grid_meta.nc, day_has_data.npy, meta.json)

Outputs (dryspell_v9/<region>/step04/<name>/; name = ISO3, or --name)
  status.json                    ok / skipped (+ why), target, cell counts
  stage_windows.csv              stages + vulnerable window in DAS per crop x cycle
  cells_<crop>.nc                per-cell layers, dims (cycle, sow, [stage], lat, lon)
  cell_summary.parquet           one row per cell x crop x cycle x sow
  cell_stage_hits_<crop>.parquet P(longest spell hits stage) per cell (one column per stage)
  zone_summary.csv               per zone (+ "ALL") x crop x cycle x sow, with cell counts
  zone_stage_hits.csv            per zone (+ "ALL") x crop x cycle x sow x stage, with cell counts
  regime_summary.csv             per rainfall regime x crop x cycle x sow
  season_detail.csv              --point only: every season x crop x cycle x sow
  png/                           heatmaps (stage x sowing), maps, zone curves
Exit code 3 = nothing to analyse (status.json says why).

Usage
-----
  python v9_04_sowing_risk.py --region ci_nga --iso3 NGA
  python v9_04_sowing_risk.py --region ci_nga --bbox 7 10 9 12 --name kano_box --zones koppen
  python v9_04_sowing_risk.py --region ssa --polygon states.gpkg --polygon_field NAME \\
         --polygon_value Kano --name kano
  python v9_04_sowing_risk.py --region ci_nga --point 12.0 8.5
"""

import os
for _v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse
import gc
import logging
import multiprocessing as mp
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v9_common as C

warnings.filterwarnings("ignore", category=RuntimeWarning)
logger = logging.getLogger("dryspell_v9")

# all settings live in v9_config.py (section I and J)
CROPS = C.CROPS
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948",
          "#6b8e23", "#8c564b", "#17becf", "#bcbd22", "#7f7f7f", "#d62728", "#9467bd", "#ff9896"]
GREY_IMPOSSIBLE = "#b5b5b5"
GREY_NODATA = "#e3e3e3"
SKIP_EXIT = 3      # exit code for "nothing to analyse" (run_all treats it as skipped)

_G = {}

# =============================================================================
# STAGES
# =============================================================================

def stage_onsets(crop, cycle):
    """Onset (DAS) of every stage of CROPS[crop] for a cultivar of `cycle` days (see v9_config.py)."""
    spec = CROPS[crop]
    Lr, E = spec["reference_cycle"], spec["emergence_das"]
    codes = [s[0] for s in spec["stages"]]
    ref = np.array([s[2] for s in spec["stages"]], float)
    Ar = ref[codes.index(spec["anchor"])]
    if "post_anchor_exponent" in spec:
        A = cycle - (Lr - Ar) * (cycle / Lr) ** spec["post_anchor_exponent"]
    else:
        A = E + (Ar - E) * (cycle / Lr) ** spec["pre_anchor_exponent"]
    d = np.where(ref <= Ar, E + (ref - E) * (A - E) / (Ar - E), A + (ref - Ar) * (cycle - A) / (Lr - Ar))
    d = np.round(d).astype(int)
    for k in range(1, len(d)):                          # strictly increasing, inside the cycle
        d[k] = max(d[k], d[k - 1] + 1)
    if d[-1] > cycle - 1:
        raise ValueError(f"{crop}: stages do not fit a {cycle}-day cycle")
    return dict(zip(codes, d.tolist()))


def stage_das(crop, cycle):
    """[(code, name, das_start, das_end)] and (win_start, win_end) in DAS (inclusive)."""
    spec = CROPS[crop]
    on = stage_onsets(crop, cycle)
    starts = [0] + [on[c] for c, _, _ in spec["stages"]]
    codes = ["SOW"] + [c for c, _, _ in spec["stages"]]
    names = ["sowing to emergence"] + [n for _, n, _ in spec["stages"]]
    out = []
    for i in range(len(starts)):
        a = starts[i]
        b = (starts[i + 1] - 1) if i + 1 < len(starts) else cycle - 1
        out.append((codes[i], names[i], a, max(a, b)))
    (c0, o0), (c1, o1) = spec["window"]
    win = (max(0, on[c0] + o0), min(cycle - 1, on[c1] + o1))
    return out, win


def stage_table(crops, cycles):
    rows = []
    for crop in crops:
        for L in cycles:
            stages, (w0, w1) = stage_das(crop, L)
            s_in = [s for s in stages if s[3] >= w0 and s[2] <= w1]
            wlab = f"{s_in[0][0]} ({s_in[0][1]}) -> {s_in[-1][0]} ({s_in[-1][1]})"
            for k, (code, name, a, b) in enumerate(stages):
                rows.append({"crop": crop, "cycle": L, "stage_idx": k, "stage": code, "stage_name": name,
                             "das_start": a, "das_end": b, "length": b - a + 1,
                             "overlaps_window": bool(b >= w0 and a <= w1),
                             "window_das_start": w0, "window_das_end": w1, "window_stages": wlab})
    return pd.DataFrame(rows)


# =============================================================================
# WORKER
# =============================================================================

def _date_to_index(col):
    """pyarrow date32 column -> int64 day index since ORIGIN (null -> SENT)."""
    import pyarrow as pa
    import pyarrow.compute as pc
    epoch = int((C.ORIGIN - np.datetime64("1970-01-01", "D")).astype(int))
    v = pc.fill_null(pc.cast(col, pa.int32()), np.iinfo(np.int32).min).to_numpy().astype(np.int64)
    return np.where(v == np.iinfo(np.int32).min, np.iinfo(np.int64).min, v - epoch)


def _pair_spells(sp_cell, sp_s, sp_e, se_cell, on, span_end):
    """(spell index, season index) for every spell overlapping [onset, span_end] of a season."""
    if len(sp_cell) == 0 or len(on) == 0:
        e = np.zeros(0, dtype=np.int64)
        return e, e
    BIG = np.int64(1) << 24
    key = se_cell * BIG + on                    # seasons sorted by (cell, onset)
    last = np.searchsorted(key, sp_cell * BIG + sp_e, side="right") - 1
    pi, qi = [], []
    for pos in (last, last - 1):                # spans never overlap -> 2 candidates suffice
        ok = pos >= 0
        p = np.where(ok, pos, 0)
        ok &= (se_cell[p] == sp_cell) & (sp_s <= span_end[p]) & (sp_e >= on[p])
        pi.append(np.nonzero(ok)[0])
        qi.append(p[ok])
    return np.concatenate(pi), np.concatenate(qi)


def process_rows(r0, r1):
    import pyarrow.parquet as pq

    g = _G
    nlon = g["nlon"]
    nr = r1 - r0
    ncell = nr * nlon
    mask = g["mask"][r0:r1].ravel()
    crops, cycles, sows = g["crops"], g["cycles"], g["sows"]
    nC, nS = len(cycles), len(sows)

    # ---- seasons (valid only, inside the country)
    t = pq.read_table(Path(g["season_dir"]) / f"part_r{r0:05d}.parquet",
                      columns=["row", "col", "year", "onset_date", "demise_date", "valid"])
    valid = t["valid"].to_numpy().astype(bool)
    se_cell = (t["row"].to_numpy().astype(np.int64) - r0) * nlon + t["col"].to_numpy()
    on = _date_to_index(t["onset_date"])
    de = _date_to_index(t["demise_date"])
    keep = valid & mask[se_cell]
    se_cell, on, de = se_cell[keep], on[keep], de[keep]
    o = np.lexsort((on, se_cell))
    se_cell, on, de = se_cell[o], on[o], de[o]
    n_seasons = np.bincount(se_cell, minlength=ncell)
    del t

    # ---- spells (>= smallest crop minimum, inside the country)
    t = pq.read_table(Path(g["spell_dir"]) / f"part_r{r0:05d}.parquet",
                      columns=["row", "col", "start", "end", "length"])
    sp_cell = (t["row"].to_numpy().astype(np.int64) - r0) * nlon + t["col"].to_numpy()
    sp_s = t["start"].to_numpy().astype(np.int64)
    sp_e = t["end"].to_numpy().astype(np.int64)
    k = (t["length"].to_numpy() >= g["min_spell_all"]) & mask[sp_cell]
    sp_cell, sp_s, sp_e = sp_cell[k], sp_s[k], sp_e[k]
    del t

    span_end = on + g["day0"] + max(sows) + max(cycles) - 1
    pi, qi = _pair_spells(sp_cell, sp_s, sp_e, se_cell, on, span_end)
    ps, pe = sp_s[pi], sp_e[pi]

    gaps = g["gaps"]
    n_days = len(gaps) - 1
    nq = len(on)
    out = {}
    for crop in crops:
        minc = g["min_spell"][crop]
        nst = len(g["stages"][crop][cycles[0]][0])
        r = {
            "p_feasible": np.full((nC, nS, ncell), np.nan, np.float32),
            "impossible": np.zeros((nC, nS, ncell), np.int8),
            "p_spell": np.full((nC, nS, ncell), np.nan, np.float32),
            "p_hit_window": np.full((nC, nS, ncell), np.nan, np.float32),
            "window_overlap_mean": np.full((nC, nS, ncell), np.nan, np.float32),
            "longest_len_median": np.full((nC, nS, ncell), np.nan, np.float32),
            "longest_start_das_median": np.full((nC, nS, ncell), np.nan, np.float32),
            "longest_end_das_median": np.full((nC, nS, ncell), np.nan, np.float32),
            "p_hit_stage": np.full((nC, nS, nst, ncell), np.nan, np.float32),
        }
        for ic, L in enumerate(cycles):
            stages, (w0, w1) = g["stages"][crop][L]
            sa = np.array([s[2] for s in stages])
            sb = np.array([s[3] for s in stages])
            for isw, sw in enumerate(sows):
                S = on + g["day0"] + sw
                M = S + L - 1
                inside = (S >= 0) & (M < n_days)
                Sc, Mc = np.clip(S, 0, n_days - 1), np.clip(M, 0, n_days - 1)
                full = inside & (gaps[Mc + 1] - gaps[Sc] == 0)
                feas = full & (M <= de + g["grace"])
                n_feas = np.bincount(se_cell, weights=feas, minlength=ncell)
                with np.errstate(invalid="ignore", divide="ignore"):
                    pf = np.where(n_seasons > 0, n_feas / np.maximum(n_seasons, 1), np.nan)
                r["p_feasible"][ic, isw] = pf
                r["impossible"][ic, isw] = (n_seasons > 0) & (pf < g["feasible_min_frac"])
                enough = (n_feas >= g["min_feasible_seasons"]) & ~r["impossible"][ic, isw].astype(bool)

                # clip spells to [S, M] of their season, keep >= crop minimum
                cs = np.maximum(ps, S[qi])
                ce = np.minimum(pe, M[qi])
                cl = ce - cs + 1
                kk = (cl >= minc) & feas[qi]
                q_k, cs_k, ce_k, cl_k = qi[kk], cs[kk], ce[kk], cl[kk]
                # longest per season, ties -> earliest
                oo = np.lexsort((cs_k, -cl_k, q_k))
                q_k, cs_k, ce_k, cl_k = q_k[oo], cs_k[oo], ce_k[oo], cl_k[oo]
                first = np.r_[True, q_k[1:] != q_k[:-1]] if len(q_k) else np.zeros(0, bool)
                lq = q_k[first]
                l_s = (cs_k[first] - S[lq])                     # DAS
                l_e = (ce_k[first] - S[lq])
                l_len = cl_k[first]
                lc = se_cell[lq]

                def cnt(w):
                    return np.bincount(lc, weights=w, minlength=ncell)

                def prob(x):
                    with np.errstate(invalid="ignore", divide="ignore"):
                        v = x / np.maximum(n_feas, 1)
                    return np.where(enough, v, np.nan).astype(np.float32)

                r["p_spell"][ic, isw] = prob(cnt(np.ones(len(lq))))
                ov_w = np.maximum(0, np.minimum(l_e, w1) - np.maximum(l_s, w0) + 1)
                r["p_hit_window"][ic, isw] = prob(cnt(ov_w >= 1))
                r["window_overlap_mean"][ic, isw] = prob(cnt(ov_w))     # mean over feasible seasons
                for j in range(len(stages)):
                    ov = np.minimum(l_e, sb[j]) - np.maximum(l_s, sa[j]) + 1
                    r["p_hit_stage"][ic, isw, j] = prob(cnt(ov >= 1))
                if len(lq):
                    df = pd.DataFrame({"c": lc, "len": l_len, "s": l_s, "e": l_e}).groupby("c").median()
                    idx = df.index.to_numpy()
                    for col, name in (("len", "longest_len_median"), ("s", "longest_start_das_median"),
                                      ("e", "longest_end_das_median")):
                        a = r[name][ic, isw]
                        a[idx] = df[col].to_numpy()
                        a[~enough] = np.nan
        out[crop] = {kname: v.reshape(v.shape[:-1] + (nr, nlon)) for kname, v in r.items()}
    gc.collect()
    return r0, r1, out, n_seasons.reshape(nr, nlon), len(pi)



# =============================================================================
# ZONES
# =============================================================================

RASTER_EXT = (".tif", ".tiff", ".asc", ".img", ".nc", ".zip")


def _raster_uri(p):
    """GDAL path for a raster file, or for the first raster inside a .zip."""
    if p.suffix.lower() != ".zip":
        return str(p)
    import zipfile
    with zipfile.ZipFile(p) as z:
        names = [n for n in z.namelist() if n.lower().endswith((".asc", ".tif", ".tiff", ".img"))]
        if not names:                       # e.g. an ESRI ASCII grid saved as .txt
            side = (".prj", ".xml", ".aux", ".ovr", ".lyr", ".dbf", ".shp", ".shx", ".cpg", ".pdf", ".doc", "/")
            names = [n for n in z.namelist() if not n.lower().endswith(side)]
    if not names:
        sys.exit(f"no raster inside {p}")
    return f"zip://{p.resolve()}!{names[0]}"


def _read_legend(path):
    """CSV with columns code,label -> {int: str}."""
    d = pd.read_csv(path)
    return {int(c): str(l) for c, l in zip(d.iloc[:, 0], d.iloc[:, 1])}


def _read_ascii_grid(raw, bounds, margin=0.5):
    """
    ESRI ASCII grid (bytes) -> (array, transform, nodata) cropped to bounds + margin.
    Parsed here instead of by GDAL because real files are not always regular: the
    HarvestChoice Africa AEZ grid wraps rows over several lines and holds 275 values
    fewer than its header says, which GDAL rejects ("File short").
    """
    from rasterio.transform import from_origin
    lines = raw.split(b"\n", 6)
    hdr = {}
    for ln in lines[:6]:
        k, v = ln.split()[:2]
        hdr[k.decode().lower()] = float(v)
    nc, nr, cs = int(hdr["ncols"]), int(hdr["nrows"]), hdr["cellsize"]
    x0 = hdr.get("xllcorner", hdr.get("xllcenter", 0) - cs / 2)
    y0 = hdr.get("yllcorner", hdr.get("yllcenter", 0) - cs / 2)
    nod = hdr.get("nodata_value", -9999)
    body = lines[6]
    del raw, lines
    import re
    bad = re.search(rb"[^0-9eE+\-.\s]", body)
    if bad:
        # corrupted bytes: keep only the clean part before them (cut at the last separator so a
        # half-written number is dropped); everything after becomes no-data - the token count
        # after a corrupted block cannot be trusted
        cut = max(body.rfind(b" ", 0, bad.start()), body.rfind(b"\n", 0, bad.start()))
        body = body[:max(cut, 0)]
    vals = np.fromstring(body.decode("ascii"), dtype=np.int32, sep=" ")   # any whitespace separates
    del body
    n = nr * nc
    if bad:
        r_ok = vals.size // nc
        logger.warning(f"ASCII grid is corrupted from row {r_ok} (lat ~{y0 + (nr - r_ok) * cs:.2f}); "
                       f"rows from there on are treated as no-data")
    elif vals.size != n:
        logger.warning(f"ASCII grid holds {vals.size:,} values, header says {n:,} - "
                       f"{'padding the end with no-data' if vals.size < n else 'ignoring the excess'}")
    vals = np.r_[vals, np.full(max(0, n - vals.size), int(nod), np.int32)][:n]
    a = vals.reshape(nr, nc)
    top = y0 + nr * cs
    c0 = max(0, int(np.floor((bounds[0] - margin - x0) / cs)))
    c1 = min(nc, int(np.ceil((bounds[2] + margin - x0) / cs)))
    r0 = max(0, int(np.floor((top - bounds[3] - margin) / cs)))
    r1 = min(nr, int(np.ceil((top - bounds[1] + margin) / cs)))
    if c0 >= c1 or r0 >= r1:
        sys.exit("zone grid does not cover the target")
    return a[r0:r1, c0:c1].copy(), from_origin(x0 + c0 * cs, top - r0 * cs, cs, cs), nod


def _read_class_raster(p, bounds):
    """Class raster (file or first raster inside a .zip) -> (array, transform, crs, nodata, label)."""
    import rasterio
    from rasterio.windows import from_bounds
    uri = _raster_uri(p)
    name = uri.split("!")[-1]
    if name.lower().endswith(".asc") or (p.suffix.lower() == ".asc"):
        if uri.startswith("zip://"):
            import zipfile
            with zipfile.ZipFile(p) as z:
                raw = z.read(name)
        else:
            raw = p.read_bytes()
        a, tr, nod = _read_ascii_grid(raw, bounds)
        return a, tr, "EPSG:4326", nod, uri                  # ESRI .asc usually ships without CRS
    with rasterio.open(uri) as src:
        crs = src.crs or "EPSG:4326"
        if crs == "EPSG:4326" or (hasattr(crs, "to_epsg") and crs.to_epsg() == 4326):
            w = from_bounds(bounds[0] - 0.5, bounds[1] - 0.5, bounds[2] + 0.5, bounds[3] + 0.5,
                            transform=src.transform).round_offsets().round_lengths()
            w = w.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
            return src.read(1, window=w), src.window_transform(w), crs, src.nodata, uri
        return src.read(1), src.transform, crs, src.nodata, uri


def _mode_to_grid(band, src_tr, src_crs, nod, lon, lat):
    """Class raster -> analysis grid by MAJORITY (mode) of the source pixels in each cell."""
    from rasterio.warp import reproject, Resampling
    dst = np.full((len(lat), len(lon)), -1, dtype=np.int32)
    reproject(band.astype(np.int32), dst, src_transform=src_tr, src_crs=src_crs,
              src_nodata=(int(nod) if nod is not None and np.isfinite(nod) else -9999),
              dst_transform=C.grid_transform(lon, lat), dst_crs="EPSG:4326",
              dst_nodata=-1, resampling=Resampling.mode)
    return dst[::-1]                                   # north-up -> ascending lat


def load_zones(zones, lon, lat, tmask, regime, field=None, legend=None):
    """Return (codes int16 grid, {code: label}, source description); -1 = no zone."""
    bounds = (lon.min(), lat.min(), lon.max(), lat.max())

    def finish(codes, lab, src):
        codes = np.where(tmask & (codes > 0), codes, -1).astype(np.int16)
        present = sorted(int(c) for c in np.unique(codes) if c >= 0)
        return codes, {c: lab.get(c, f"zone {c}") for c in present}, src

    if zones == "regime":
        return finish(regime.astype(np.int16), {k: v for k, v in C.REGIME_LABELS.items() if k},
                      "rainfall regime (step 3)")
    if zones in ("aez", "aez8"):
        p = C.data_dir("aez", "afr_aez09.tif")
        if not p.exists():
            logger.warning(f"{p} not found (run v9_01_download.py --only aez) - zones = rainfall regime")
            return load_zones("regime", lon, lat, tmask, regime)
        band, tr, crs, nod, _ = _read_class_raster(p, bounds)
        band = np.where(band == nod, -1, band)
        if zones == "aez8":                          # fold to 8 classes BEFORE the majority
            return finish(_mode_to_grid(C.aez8_from_code(band), tr, crs, -1, lon, lat), C.AEZ8_LABELS,
                          "HarvestChoice AEZ (Sebastian 2009), 8 classes, majority per cell")
        return finish(_mode_to_grid(band, tr, crs, -1, lon, lat), C.HARVESTCHOICE_AEZ,
                      "HarvestChoice AEZ (Sebastian 2009), majority per cell")
    if zones == "koppen":
        p = C.data_dir("koppen", f"koppen_{C.KOPPEN_PERIOD}.tif")
        if not p.exists():
            logger.warning(f"{p} not found (run v9_01_download.py --only koppen) - zones = rainfall regime")
            return load_zones("regime", lon, lat, tmask, regime)
        band, tr, crs, nod, _ = _read_class_raster(p, bounds)
        leg = C.data_dir("koppen", "legend.txt")
        lab = C.koppen_labels(leg.read_text()) if leg.exists() else {}
        return finish(_mode_to_grid(band, tr, crs, nod if nod is not None else 0, lon, lat), lab,
                      f"Koppen-Geiger {C.KOPPEN_PERIOD} (Beck et al. 2023), majority per cell")
    p = Path(zones)
    if not p.exists():
        sys.exit(f"--zones {zones!r}: not aez8/aez/koppen/regime and not a file")
    if p.suffix.lower() in RASTER_EXT:
        band, tr, crs, nod, uri = _read_class_raster(p, bounds)
        lab = _read_legend(legend) if legend else {}
        return finish(_mode_to_grid(band, tr, crs, nod, lon, lat), lab, f"raster {uri} (majority per cell)")
    import geopandas as gpd
    from rasterio.features import rasterize
    gdf = gpd.read_file(p).to_crs("EPSG:4326")
    if field not in gdf.columns:
        sys.exit(f"--zone_field {field!r} not in {list(gdf.columns)}")
    cats = sorted(gdf[field].dropna().astype(str).unique())
    labels = {i + 1: c for i, c in enumerate(cats)}
    inv = {v: k for k, v in labels.items()}
    shapes = [(geom, inv[str(v)]) for geom, v in zip(gdf.geometry, gdf[field]) if v is not None and geom is not None]
    r = rasterize(shapes, out_shape=(len(lat), len(lon)), transform=C.grid_transform(lon, lat),
                  fill=-1, dtype="int16")[::-1]
    return finish(r, labels, f"vector {p} field {field}")


# =============================================================================
# TARGET
# =============================================================================

def target_mask(a, lon, lat, bbox_region):
    """-> (mask on the region grid, boundaries GeoDataFrame for plots or None, target dict)."""
    from rasterio.features import geometry_mask
    shape = (len(lat), len(lon))
    tr = C.grid_transform(lon, lat)
    LON, LAT = np.meshgrid(lon, lat)
    if a.iso3:
        bnd_all = C.load_boundaries(bbox_region)
        if bnd_all is None:
            sys.exit("country boundaries are required - run v9_01_download.py --only boundaries")
        bnd = bnd_all[bnd_all["iso_a3"] == a.iso3]
        if not len(bnd):
            return np.zeros(shape, bool), None, {"kind": "country", "iso3": a.iso3}
        m = geometry_mask(bnd.geometry, out_shape=shape, transform=tr, invert=True)[::-1]
        return m, bnd, {"kind": "country", "iso3": a.iso3}
    if a.bbox:
        w, s, e, n = a.bbox
        m = (LON >= w) & (LON <= e) & (LAT >= s) & (LAT <= n)
        return m, C.load_boundaries((w - 1, s - 1, e + 1, n + 1)), {"kind": "bbox", "bbox": list(a.bbox)}
    if a.polygon:
        import geopandas as gpd
        g = gpd.read_file(a.polygon).to_crs("EPSG:4326")
        if a.polygon_field:
            if a.polygon_field not in g.columns:
                sys.exit(f"--polygon_field {a.polygon_field!r} not in {list(g.columns)}")
            g = g[g[a.polygon_field].astype(str) == str(a.polygon_value)]
            if not len(g):
                sys.exit(f"no feature with {a.polygon_field} == {a.polygon_value!r} in {a.polygon}")
        m = geometry_mask(g.geometry, out_shape=shape, transform=tr, invert=True)[::-1]
        if not m.any():                                  # polygon smaller than a cell
            m = geometry_mask(g.geometry, out_shape=shape, transform=tr, invert=True, all_touched=True)[::-1]
        return m, g, {"kind": "polygon", "file": str(a.polygon), "field": a.polygon_field,
                      "value": a.polygon_value, "n_features": int(len(g))}
    plat, plon = a.point
    m = np.zeros(shape, bool)
    i, j = int(np.abs(lat - plat).argmin()), int(np.abs(lon - plon).argmin())
    res = abs(lat[1] - lat[0]) if len(lat) > 1 else 0.05
    if abs(lat[i] - plat) <= res / 2 + 1e-9 and abs(lon[j] - plon) <= res / 2 + 1e-9:
        m[i, j] = True
    return m, C.load_boundaries((plon - 1, plat - 1, plon + 1, plat + 1)), \
        {"kind": "point", "lat": plat, "lon": plon, "cell_lat": float(lat[i]), "cell_lon": float(lon[j])}


def season_detail(cells, a, cycles, sows, stages, min_spell, has, s3, lat, lon):
    """--point: every valid season x crop x cycle x sow of the given (row, col) cells."""
    import pyarrow.parquet as pq
    meta = C.read_json(s3 / "meta.json")
    gaps = np.r_[0, np.cumsum(~has)]
    n_days = len(has)
    rows = []
    for (i, j) in cells:
        r0 = next(c[0] for c in meta["chunks"] if c[0] <= i < c[1])
        se = pq.read_table(s3 / "seasons" / f"part_r{r0:05d}.parquet",
                           filters=[("row", "=", int(i)), ("col", "=", int(j))]).to_pandas()
        sp = pq.read_table(s3 / "spells" / f"part_r{r0:05d}.parquet",
                           filters=[("row", "=", int(i)), ("col", "=", int(j))]).to_pandas()
        se = se[se["valid"].astype(bool)].sort_values("onset_date")
        sps, spe = sp["start"].to_numpy(np.int64), sp["end"].to_numpy(np.int64)
        for s in se.itertuples():
            on = int(C.day_index(np.array([s.onset_date], dtype="datetime64[D]"))[0])
            de = int(C.day_index(np.array([s.demise_date], dtype="datetime64[D]"))[0])
            base = {"lat": float(lat[i]), "lon": float(lon[j]), "year": int(s.year),
                    "onset": str(s.onset_date), "demise": str(s.demise_date)}
            for extra in ("demise_rain_date", "ndvi_eos_date", "demise_shift", "false_start", "false_demise"):
                if extra in se.columns:
                    v = getattr(s, extra)
                    base[extra] = None if pd.isna(v) else (str(v) if "date" in extra else v)
            for crop in a.crops:
                for L in cycles:
                    st, (w0, w1) = stages[crop][L]
                    for sw in sows:
                        S = on + a.day0 + sw
                        M = S + L - 1
                        full = S >= 0 and M < n_days and gaps[M + 1] - gaps[S] == 0
                        feas = bool(full and M <= de + a.grace)
                        d = dict(base, crop=crop, cycle=L, sow=a.day0 + sw,
                                 sow_date=str(C.index_to_date(S)), maturity_date=str(C.index_to_date(M)),
                                 feasible=feas, longest_len=0, longest_start_das=None, longest_end_das=None,
                                 hits_window=False, window_overlap_days=0, stages_hit="")
                        if feas and len(sps):
                            cs, ce = np.maximum(sps, S), np.minimum(spe, M)
                            cl = ce - cs + 1
                            k = np.nonzero(cl >= min_spell[crop])[0]
                            if len(k):
                                b = k[np.lexsort((cs[k], -cl[k]))[0]]
                                ls, le = int(cs[b] - S), int(ce[b] - S)
                                ov = max(0, min(le, w1) - max(ls, w0) + 1)
                                d.update(longest_len=int(cl[b]), longest_start_das=ls, longest_end_das=le,
                                         hits_window=ov >= 1, window_overlap_days=ov,
                                         stages_hit=";".join(x[0] for x in st if min(le, x[3]) >= max(ls, x[2])))
                        rows.append(d)
    return pd.DataFrame(rows)


# =============================================================================
# PLOTS
# =============================================================================

def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def plot_stage_heatmaps(path, crop, st_df, hits, cycles, sows, day0, title_extra):
    """hits: DataFrame (cycle, sow, stage_idx, p) for one zone. One panel per cycle."""
    plt = _plt()
    from matplotlib.patches import Rectangle
    n = len(cycles)
    fig, axes = plt.subplots(1, n, figsize=(3.6 * n + 1.2, 3.9), sharey=True)
    axes = np.atleast_1d(axes)
    im = None
    for ax, L in zip(axes, cycles):
        sdf = st_df[(st_df.crop == crop) & (st_df.cycle == L)].sort_values("stage_idx")
        h = hits[hits.cycle == L].pivot(index="sow", columns="stage_idx", values="p") \
            .reindex(index=sows, columns=sdf.stage_idx.tolist())
        im = ax.imshow(h.values, cmap="Oranges", vmin=0, vmax=1, aspect="auto", interpolation="nearest")
        for i in range(h.shape[0]):
            for j in range(h.shape[1]):
                v = h.values[i, j]
                if np.isfinite(v):
                    ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=6,
                            color="white" if v > 0.6 else "#333333")
        win = sdf.overlaps_window.to_numpy()
        if win.any():
            j0, j1 = np.where(win)[0][[0, -1]]
            ax.add_patch(Rectangle((j0 - 0.5, -0.5), j1 - j0 + 1, len(sows), fill=False,
                                   edgecolor="#222222", linewidth=1.4))
        ax.set_xticks(range(len(sdf)))
        ax.set_xticklabels([f"{c}  {a}-{b}" for c, a, b in zip(sdf.stage, sdf.das_start, sdf.das_end)],
                           fontsize=6, rotation=90)
        ax.set_yticks(range(len(sows)))
        ax.set_yticklabels([f"+{day0 + s}" for s in sows], fontsize=7)
        ax.set_title(f"{L}-day cycle", loc="left", fontsize=9)
        ax.set_xlabel("stage (DAS range)", fontsize=7)
        for s in ax.spines.values():
            s.set_visible(False)
    axes[0].set_ylabel("sowing, days after onset", fontsize=8)
    cb = fig.colorbar(im, ax=axes, shrink=0.8, pad=0.01)
    cb.set_label("P(longest dry spell hits stage)", fontsize=8)
    cb.outline.set_visible(False)
    fig.suptitle(f"{CROPS[crop]['label']} - {title_extra}   (box = most vulnerable window)",
                 x=0.01, ha="left", fontsize=10)
    fig.savefig(path, dpi=C.FIG_DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_window_maps(path, crop, ds, cycles, sows, day0, lon, lat, bnd, analysed):
    plt = _plt()
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch
    nC, nS = len(cycles), len(sows)
    extent = [lon.min() - 0.025, lon.max() + 0.025, lat.min() - 0.025, lat.max() + 0.025]
    aspect = (extent[3] - extent[2]) / (extent[1] - extent[0])
    fig, axes = plt.subplots(nC, nS, figsize=(2.6 * nS + 1, 2.6 * nC * aspect + 0.8), squeeze=False)
    im = None
    for ic, L in enumerate(cycles):
        for isw, sw in enumerate(sows):
            ax = axes[ic, isw]
            ax.imshow(np.where(~analysed, 1.0, np.nan)[::-1], extent=extent,
                      cmap=ListedColormap([GREY_NODATA]), interpolation="nearest")
            imp = ds["impossible"].values[ic, isw].astype(bool) & analysed
            ax.imshow(np.where(imp, 1.0, np.nan)[::-1], extent=extent,
                      cmap=ListedColormap([GREY_IMPOSSIBLE]), interpolation="nearest")
            im = ax.imshow(ds["p_hit_window"].values[ic, isw][::-1], extent=extent, cmap="Purples",
                           vmin=0, vmax=1, interpolation="nearest")
            if bnd is not None and len(bnd):
                bnd.boundary.plot(ax=ax, color="#333333", linewidth=0.3)
            ax.set_xlim(extent[:2])
            ax.set_ylim(extent[2:])
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_xlabel("")
            ax.set_ylabel("")
            for s in ax.spines.values():
                s.set_visible(False)
            if ic == 0:
                ax.set_title(f"sow onset+{day0 + sw}", fontsize=8)
            if isw == 0:
                ax.set_ylabel(f"{L} d", fontsize=8)
    cb = fig.colorbar(im, ax=axes, shrink=0.6, pad=0.01)
    cb.set_label("P(longest dry spell hits the vulnerable window)", fontsize=8)
    cb.outline.set_visible(False)
    fig.legend(handles=[Patch(facecolor=GREY_IMPOSSIBLE, label="impossible (cycle does not fit the season)"),
                        Patch(facecolor=GREY_NODATA, label="no season (arid, too few valid seasons) / no data")],
               loc="lower left", frameon=False, fontsize=7, ncol=2)
    fig.suptitle(f"{CROPS[crop]['label']} - rows: cycle length, columns: sowing date", x=0.01,
                 ha="left", fontsize=10)
    fig.savefig(path, dpi=C.FIG_DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_zone_curves(path, crop, summ, cycles, sows, day0, zone_order):
    """P(hit window) vs sowing date, one line per zone, one panel per cycle."""
    plt = _plt()
    n = len(cycles)
    fig, axes = plt.subplots(1, n, figsize=(3.0 * n + 2.6, 3.2), sharey=True)
    axes = np.atleast_1d(axes)
    x = [day0 + s for s in sows]
    for ax, L in zip(axes, cycles):
        for k, a in enumerate(zone_order):
            d = summ[(summ.crop == crop) & (summ.cycle == L) & (summ.zone == a)].set_index("sow").reindex(sows)
            col = "#222222" if a == "ALL" else SERIES[k % len(SERIES)]
            ax.plot(x, d["p_hit_window_mean"], color=col, linewidth=2.4 if a == "ALL" else 2,
                    linestyle="--" if a == "ALL" else "-", marker="o", markersize=4,
                    label=a if ax is axes[0] else None)
        ax.set_title(f"{L}-day cycle", loc="left", fontsize=9)
        ax.set_xticks(x)
        ax.set_xlabel("sowing, days after onset", fontsize=8)
        ax.set_ylim(0, 1)
        ax.grid(True, color="#e5e5e5", linewidth=0.6)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[0].set_ylabel("P(longest spell hits window)\nmean over possible cells", fontsize=8)
    fig.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False, fontsize=7)
    fig.suptitle(f"{CROPS[crop]['label']} - by zone (missing point = all cells impossible)", x=0.01,
                 ha="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=C.FIG_DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)



# =============================================================================
# MAIN
# =============================================================================

def _palette(n):
    if n <= len(SERIES):
        return SERIES[:n]
    import matplotlib
    cm = matplotlib.colormaps["tab20"]
    return [matplotlib.colors.to_hex(cm(i % 20)) for i in range(n)]


def default_name(a):
    if a.name:
        return a.name
    if a.iso3:
        return a.iso3
    if a.bbox:
        return "bbox_" + "_".join(f"{v:g}" for v in a.bbox)
    if a.polygon:
        return _slug(Path(a.polygon).stem + (f"_{a.polygon_value}" if a.polygon_value else ""))
    return f"pt_{a.point[0]:g}_{a.point[1]:g}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", default="ci_nga", help="region processed by steps 1-3")
    tg = ap.add_mutually_exclusive_group()
    tg.add_argument("--iso3", default=None, help="country (ISO3), default NGA if no other target")
    tg.add_argument("--bbox", nargs=4, type=float, default=None, metavar=("W", "S", "E", "N"))
    tg.add_argument("--polygon", default=None, help="polygon file (.gpkg/.shp/.geojson)")
    tg.add_argument("--point", nargs=2, type=float, default=None, metavar=("LAT", "LON"))
    ap.add_argument("--polygon_field", default=None, help="attribute selecting one feature of --polygon")
    ap.add_argument("--polygon_value", default=None)
    ap.add_argument("--name", default=None, help="output folder name (default ISO3 / bbox_... / pt_...)")
    ap.add_argument("--crops", nargs="+", default=list(CROPS), choices=list(CROPS))
    ap.add_argument("--cycles", nargs="+", type=int, default=C.CYCLES)
    ap.add_argument("--sow", nargs="+", type=int, default=C.SOW_OFFSETS, help="sowing offsets after DAY0")
    ap.add_argument("--day0", type=int, default=C.DAY0, choices=[0, 1], help="first sowing = onset + day0")
    ap.add_argument("--grace", type=int, default=C.DEMISE_GRACE, help="days maturity may exceed demise")
    ap.add_argument("--feasible_min_frac", type=float, default=C.FEASIBLE_MIN_FRAC)
    ap.add_argument("--min_feasible_seasons", type=int, default=C.MIN_FEASIBLE_SEASONS)
    ap.add_argument("--min_spell", nargs="*", default=[], metavar="CROP=DAYS",
                    help="override MIN_SPELL_CROP, e.g. pearl_millet=12")
    ap.add_argument("--zones", default=C.SUMMARY_ZONES,
                    help="aez8 | aez | koppen | regime | class raster / vector file (default SUMMARY_ZONES)")
    ap.add_argument("--zone_legend", default=None, help="CSV code,label for a raster --zones file")
    ap.add_argument("--zone_field", default="zone", help="attribute with the zone name (vector --zones)")
    ap.add_argument("--workers", type=int, default=max(1, min(32, mp.cpu_count() - 4)))
    ap.add_argument("--out_dir", default=None, help="default: dryspell_v9/<region>/step04/<name>")
    a = ap.parse_args()
    if not (a.iso3 or a.bbox or a.polygon or a.point):
        a.iso3 = "NGA"
    if a.polygon_field and a.polygon_value is None:
        sys.exit("--polygon_field needs --polygon_value")

    min_spell = dict(C.MIN_SPELL_CROP)
    for s in a.min_spell:
        k, v = s.split("=")
        if k not in CROPS:
            sys.exit(f"--min_spell: unknown crop {k}")
        min_spell[k] = int(v)
    if min(min_spell[c] for c in a.crops) < C.STEP1_MIN_SPELL:
        sys.exit(f"minimum spell must be >= {C.STEP1_MIN_SPELL} (step 3 only stores spells >= that)")
    cycles, sows = sorted(a.cycles), sorted(a.sow)

    rdir = C.region_dir(a.region)
    s3 = rdir / "step03"
    name = default_name(a)
    out = Path(a.out_dir) if a.out_dir else rdir / "step04" / name
    C.setup_logging(out / "step04.log")
    t0 = time.time()
    if not (s3 / "seasons").exists():
        sys.exit(f"{s3 / 'seasons'} not found - run v9_03_spells_seasons.py first")
    meta = C.read_json(s3 / "meta.json")
    with xr.open_dataset(s3 / "grid_meta.nc") as d:
        gm = d.load()
    lon, lat = gm.lon.values, gm.lat.values
    has = np.load(s3 / "day_has_data.npy")

    logger.info("=" * 70)
    logger.info(f"v9 STEP4  region={a.region} target={name} crops={a.crops} zones={a.zones}")
    logger.info(f"  sowing = onset + {a.day0} + {sows}   cycles = {cycles} d   grace = {a.grace} d")
    logger.info(f"  min spell (d) = { {c: min_spell[c] for c in a.crops} }   impossible if "
                f"P(feasible) < {a.feasible_min_frac}")
    logger.info("=" * 70)

    # ---- target mask on the step 3 grid
    tmask, bnd, target = target_mask(a, lon, lat, meta["bbox"])
    if not tmask.any():
        skip(out, name, target, "target not found or no grid cell of the region inside it")
    cell_ok = gm["valid"].values.astype(bool)
    rows = np.where(tmask.any(1))[0]
    cols = np.where(tmask.any(0))[0]
    i0, i1, j0, j1 = rows.min(), rows.max() + 1, cols.min(), cols.max() + 1
    logger.info(f"  {name} ({target['kind']}): {tmask.sum():,} grid cells, {(tmask & cell_ok).sum():,} usable")

    stages = {c: {L: stage_das(c, L) for L in cycles} for c in a.crops}
    st_df = stage_table(a.crops, cycles)
    out.mkdir(parents=True, exist_ok=True)
    st_df.to_csv(out / "stage_windows.csv", index=False)
    for (c, L), d in st_df.groupby(["crop", "cycle"]):
        r = d.iloc[0]
        logger.info(f"  {c:<13}{L:>4} d: vulnerable window DAS {r.window_das_start}-{r.window_das_end} "
                    f"= {r.window_stages}")

    _G.update(nlon=len(lon), mask=tmask & cell_ok, crops=a.crops, cycles=cycles, sows=sows,
              day0=a.day0, grace=a.grace, feasible_min_frac=a.feasible_min_frac,
              min_feasible_seasons=a.min_feasible_seasons, min_spell=min_spell,
              min_spell_all=min(min_spell[c] for c in a.crops), stages=stages,
              gaps=np.r_[0, np.cumsum(~has)], spell_dir=str(s3 / "spells"), season_dir=str(s3 / "seasons"))

    chunks = [tuple(c) for c in meta["chunks"] if c[1] > i0 and c[0] < i1]
    nC, nS = len(cycles), len(sows)
    bh, bw = i1 - i0, j1 - j0                      # arrays cover the target box only
    full = {}
    for c in a.crops:
        nst = len(stages[c][cycles[0]][0])
        full[c] = {k: np.full((nC, nS, bh, bw), np.nan, np.float32)
                   for k in ("p_feasible", "p_spell", "p_hit_window", "window_overlap_mean",
                             "longest_len_median", "longest_start_das_median", "longest_end_das_median")}
        full[c]["impossible"] = np.zeros((nC, nS, bh, bw), np.int8)
        full[c]["p_hit_stage"] = np.full((nC, nS, nst, bh, bw), np.nan, np.float32)
    n_seas = np.zeros((bh, bw), np.int32)
    logger.info(f"Processing {len(chunks)} row chunks")
    n_pairs = 0
    with ProcessPoolExecutor(max_workers=max(1, min(a.workers, len(chunks))),
                             mp_context=mp.get_context("fork")) as pool:
        futs = [pool.submit(process_rows, r0, r1) for r0, r1 in chunks]
        for i, f in enumerate(as_completed(futs), 1):
            r0, r1, res, ns, npair = f.result()
            ra, rb = max(r0, i0), min(r1, i1)
            n_seas[ra - i0:rb - i0] = ns[ra - r0:rb - r0, j0:j1]
            n_pairs += npair
            for c in a.crops:
                for k, v in res[c].items():
                    full[c][k][..., ra - i0:rb - i0, :] = v[..., ra - r0:rb - r0, j0:j1]
            del res
            if i % 10 == 0 or i == len(chunks):
                logger.info(f"  {i}/{len(chunks)} chunks")
    logger.info(f"  spell x season pairs examined: {n_pairs:,}")

    # ---- target box
    sl = (slice(i0, i1), slice(j0, j1))
    lon_c, lat_c = lon[j0:j1], lat[i0:i1]
    cm_c = tmask[sl]
    analysed = cm_c & cell_ok[sl] & (n_seas >= a.min_feasible_seasons)
    n_few = int((cm_c & cell_ok[sl] & (n_seas < a.min_feasible_seasons)).sum())
    logger.info(f"  cells analysed: {analysed.sum():,}; no/too few valid seasons (arid, failed seasons): "
                f"{n_few:,}; no usable CHIRPS: {(cm_c & ~cell_ok[sl]).sum():,}")

    if target["kind"] == "point":
        cells_ij = [(int(i + i0), int(j + j0)) for i, j in zip(*np.nonzero(cm_c & cell_ok[sl]))]
        det = season_detail(cells_ij, a, cycles, sows, stages, min_spell, has, s3, lat, lon)
        det.to_csv(out / "season_detail.csv", index=False)
        logger.info(f"Written season_detail.csv ({len(det):,} rows)")
    if not analysed.any():
        skip(out, name, target, "no cell with enough valid seasons (arid, no CHIRPS)",
             n_cells=int(cm_c.sum()), n_few_seasons=n_few)

    regime_c = gm["regime"].values[sl].astype(np.int8)
    for code, lab in C.REGIME_LABELS.items():
        if code:
            logger.info(f"    regime {lab:<12} {(analysed & (regime_c == code)).sum():>8,} analysed cells")
    zone, zone_lab, zone_src = load_zones(a.zones, lon_c, lat_c, cm_c, regime_c, a.zone_field, a.zone_legend)
    logger.info(f"  zones: {zone_src}")
    scheme = ("regime" if zone_src.startswith("rainfall regime") else a.zones) \
        if a.zones in ("aez8", "aez", "koppen", "regime") else Path(a.zones).name
    for code, lab in zone_lab.items():
        logger.info(f"    {code:>3} {lab:<50} {(analysed & (zone == code)).sum():>8,} analysed cells")
    n_unz = int((analysed & (zone < 0)).sum())
    if n_unz:
        logger.warning(f"    {n_unz:,} analysed cells without a zone ('unassigned'; e.g. the HarvestChoice "
                       f"AEZ grid is damaged south of ~3.8N - use --zones koppen there)")

    # ---- NetCDF per crop
    reason = np.full(cm_c.shape, 0, np.uint8)       # 0 ok, 1 outside target, 2 no CHIRPS, 3 no/too few seasons
    reason[~cm_c] = 1
    reason[cm_c & ~cell_ok[sl]] = 2
    reason[cm_c & cell_ok[sl] & ~analysed] = 3
    sets = {}
    for c in a.crops:
        st0 = stages[c][cycles[0]][0]
        dv = {}
        for k, v in full[c].items():
            dv[k] = ((("cycle", "sow", "stage") if k == "p_hit_stage" else ("cycle", "sow")) + ("lat", "lon"), v)
        dv["zone"] = (("lat", "lon"), zone)
        dv["reason"] = (("lat", "lon"), reason)
        dv["n_valid_seasons"] = (("lat", "lon"), n_seas)
        dv["regime"] = (("lat", "lon"), regime_c)
        ds = xr.Dataset(dv, coords={"cycle": cycles, "sow": [a.day0 + sw for sw in sows],
                                    "stage": [s[0] for s in st0], "lat": lat_c, "lon": lon_c},
                        attrs={"crop": c, "target": name, "target_kind": target["kind"],
                               "min_spell_days": min_spell[c], "dry_mm": C.DRY_MM, "demise_grace": a.grace,
                               "demise_adjust": C.DEMISE_ADJUST, "feasible_min_frac": a.feasible_min_frac,
                               "sow": "days after onset (major season)", "zone_source": zone_src,
                               "zone_labels": str(zone_lab),
                               "reason": "0 ok, 1 outside target, 2 no usable CHIRPS, 3 no/too few valid seasons",
                               "note": "probabilities over feasible seasons; longest_* medians over seasons "
                                       "with a qualifying spell"})
        ds.to_netcdf(out / f"cells_{c}.nc", encoding={v: {"zlib": True, "complevel": 4} for v in ds.data_vars})
        sets[c] = ds
    del full
    logger.info("Written cells_<crop>.nc")

    # ---- per-cell tables (strings as categoricals: large countries have millions of rows)
    ii, jj = np.nonzero(analysed)
    zone_name = pd.Categorical([zone_lab.get(int(x), "unassigned") for x in zone[ii, jj]])
    regime_name = pd.Categorical([C.REGIME_LABELS[int(x)] for x in regime_c[ii, jj]])
    cell_rows, sh_parts = [], []
    keys = ["crop", "cycle", "sow"]
    for c in a.crops:
        ds = sets[c]
        stage_codes = [str(x) for x in ds.stage.values]
        wide_rows = []
        for ic, L in enumerate(cycles):
            for isw, sw in enumerate(sows):
                d = {"crop": c, "cycle": L, "sow": a.day0 + sw, "row": (ii + i0).astype(np.int16),
                     "col": (jj + j0).astype(np.int16), "lat": lat_c[ii].astype(np.float32),
                     "lon": lon_c[jj].astype(np.float32), "zone": zone_name, "regime": regime_name}
                for k in ("p_feasible", "impossible", "p_spell", "p_hit_window", "window_overlap_mean",
                          "longest_len_median", "longest_start_das_median", "longest_end_das_median"):
                    d[k] = ds[k].values[ic, isw][ii, jj]
                ph = ds["p_hit_stage"].values[ic, isw][:, ii, jj]          # (stage, n)
                with np.errstate(invalid="ignore"):
                    best = np.where(np.all(np.isnan(ph), 0), -1, np.nanargmax(np.where(np.isnan(ph), -1, ph), 0))
                d["most_hit_stage"] = pd.Categorical(np.where(best >= 0, np.array(stage_codes + [""])[best], ""))
                cell_rows.append(pd.DataFrame(d))
                w = pd.DataFrame({"crop": c, "cycle": L, "sow": a.day0 + sw, "row": d["row"], "col": d["col"],
                                  "zone": zone_name, "impossible": d["impossible"]})
                for j, code in enumerate(stage_codes):
                    w[f"p_hit_{code}"] = ph[j]
                wide_rows.append(w)
        wide = pd.concat(wide_rows, ignore_index=True)
        wide.to_parquet(out / f"cell_stage_hits_{c}.parquet", index=False)
        # mean P(hit stage) over possible cells + the number of cells behind each mean
        pc = [f"p_hit_{code}" for code in stage_codes]
        wp = wide[wide.impossible == 0]
        for grp, extra in ((keys + ["zone"], {}), (keys, {"zone": "ALL"})):
            g = wp.groupby(grp, observed=True)[pc]
            m = g.mean().reset_index().melt(id_vars=grp, var_name="stage", value_name="p")
            n = g.count().reset_index().melt(id_vars=grp, var_name="stage", value_name="n_cells")
            mm = m.merge(n, on=grp + ["stage"]).assign(**extra)
            mm["stage"] = mm["stage"].str.replace("p_hit_", "", regex=False)
            mm["stage_idx"] = mm["stage"].map({code: j for j, code in enumerate(stage_codes)})
            sh_parts.append(mm)
        del wide, wide_rows, wp
    cells = pd.concat(cell_rows, ignore_index=True)
    for col in ("crop", "zone", "regime", "most_hit_stage"):
        cells[col] = cells[col].astype("category")
    cells.to_parquet(out / "cell_summary.parquet", index=False)
    del cell_rows

    # ---- zone summaries (+ "ALL"); probabilities averaged over POSSIBLE cells (per-cell
    # probabilities are NaN where the cell is impossible). n_* columns carry the number of
    # cells behind each mean so step 5 can pool countries.
    agg = dict(n_cells=("impossible", "size"), n_cells_possible=("possible", "sum"),
               pct_cells_impossible=("impossible", "mean"), p_feasible_mean=("p_feasible", "mean"),
               p_spell_mean=("p_spell", "mean"), p_hit_window_mean=("p_hit_window", "mean"),
               n_cells_with_p=("p_hit_window", "count"),
               window_overlap_days_mean=("window_overlap_mean", "mean"),
               longest_len_median=("longest_len_median", "median"),
               n_cells_with_spell=("longest_len_median", "count"),
               longest_start_das_median=("longest_start_das_median", "median"),
               longest_end_das_median=("longest_end_das_median", "median"))
    cz = cells.assign(possible=(cells.impossible == 0).astype(int))
    summ = pd.concat([cz.groupby(keys + ["zone"], observed=True).agg(**agg).reset_index(),
                      cz.groupby(keys, observed=True).agg(**agg).reset_index().assign(zone="ALL")],
                     ignore_index=True)
    summ["zone"] = summ["zone"].astype(str)
    summ["pct_cells_impossible"] *= 100
    rsum = cz.groupby(keys + ["regime"], observed=True).agg(**agg).reset_index()
    rsum["regime"] = rsum["regime"].astype(str)
    rsum["pct_cells_impossible"] *= 100
    rsum.insert(0, "unit", name)
    rsum.to_csv(out / "regime_summary.csv", index=False)
    del cz
    sh = pd.concat(sh_parts, ignore_index=True)
    sh["zone"] = sh["zone"].astype(str)
    sh = sh.merge(st_df[["crop", "cycle", "stage_idx", "stage_name", "das_start", "das_end", "overlaps_window"]],
                  on=["crop", "cycle", "stage_idx"], how="left")
    # most hit stage: highest p (rounded to 1e-9, so that platform rounding never decides), ties -> earliest stage
    top = sh.assign(_p=sh.p.round(9)).sort_values(["_p", "stage_idx"], ascending=[False, True], kind="mergesort") \
        .drop(columns="_p").groupby(keys + ["zone"]).head(1)
    top = top[keys + ["zone", "stage", "stage_name", "das_start", "das_end", "p"]].rename(
        columns={"stage": "most_hit_stage", "stage_name": "most_hit_stage_name", "das_start": "most_hit_das_start",
                 "das_end": "most_hit_das_end", "p": "most_hit_p"})
    summ = summ.merge(top, on=keys + ["zone"], how="left").merge(
        st_df.groupby(["crop", "cycle"]).first()[["window_das_start", "window_das_end", "window_stages"]].reset_index(),
        on=["crop", "cycle"], how="left")
    for df in (summ, sh):
        df.insert(0, "zone_scheme", scheme)
        df.insert(0, "unit", name)
    summ.to_csv(out / "zone_summary.csv", index=False)
    sh.to_csv(out / "zone_stage_hits.csv", index=False)
    logger.info("Written zone_summary.csv, zone_stage_hits.csv, cell_summary.parquet, cell_stage_hits_<crop>.parquet")

    # ---- figures
    png = out / "png"
    png.mkdir(exist_ok=True)
    zone_order = [zone_lab[k] for k in sorted(zone_lab)] + ["unassigned", "ALL"]
    zone_order = [x for x in zone_order if x in set(summ.zone)]
    for c in a.crops:
        for az in zone_order:
            h = sh[(sh.crop == c) & (sh.zone == az)].rename(columns={"sow": "sow_abs"})
            h = h.assign(sow=h.sow_abs - a.day0)
            tag = "all cells" if az == "ALL" else az
            plot_stage_heatmaps(png / f"stage_hits_{c}_{_slug('ALL' if az == 'ALL' else az)}.png", c, st_df, h,
                                cycles, sows, a.day0,
                                f"{name} {tag}: P(longest dry spell >= {min_spell[c]} d hits stage), "
                                f"mean over possible cells")
        if analysed.sum() >= 4:
            plot_window_maps(png / f"map_window_hit_{c}.png", c, sets[c], cycles, sows, a.day0, lon_c, lat_c,
                             bnd, analysed)
        plot_zone_curves(png / f"zone_window_hit_{c}.png", c, summ.assign(sow=summ.sow - a.day0), cycles, sows,
                         a.day0, zone_order)
    codes = sorted(zone_lab)
    if codes and analysed.sum() >= 4:
        cols_ = _palette(len(codes))
        C.plot_map(png / "zones.png", np.where(analysed & (zone >= 0), zone, np.nan).astype(float), lon_c, lat_c,
                   f"zones used for the summary - {zone_src}", boundaries=bnd,
                   categorical=[(k, cols_[i], zone_lab[k]) for i, k in enumerate(codes)])

    # ---- console digest: most hit stage, all cells
    nat = summ[summ.zone == "ALL"]
    for c in a.crops:
        logger.info(f"--- {c} (all cells of {name}, possible cells) ---")
        for r in nat[nat.crop == c].itertuples():
            logger.info(f"  {r.cycle:>3} d  sow +{r.sow:<3} impossible {r.pct_cells_impossible:5.1f}%  "
                        f"P(hit window) {r.p_hit_window_mean:.2f}  most hit: {r.most_hit_stage} "
                        f"({r.most_hit_stage_name}, DAS {r.most_hit_das_start:.0f}-{r.most_hit_das_end:.0f}) "
                        f"p={r.most_hit_p:.2f}")
    C.write_json(out / "status.json", {"unit": name, "iso3": a.iso3, "target": target, "status": "ok",
                                       "n_cells": int(cm_c.sum()), "n_analysed": int(analysed.sum()),
                                       "n_few_seasons": n_few, "zones": scheme, "zone_source": zone_src,
                                       "minutes": round((time.time() - t0) / 60, 2)})
    logger.info(f"STEP4 done in {(time.time() - t0) / 60:.1f} min -> {out}")


def skip(out, name, target, why, **extra):
    """Record why a target has no results and exit with SKIP_EXIT."""
    logger.warning(f"{name}: skipped - {why}")
    C.write_json(Path(out) / "status.json", {"unit": name, "iso3": target.get("iso3"), "target": target,
                                             "status": "skipped", "reason": why, **extra})
    sys.exit(SKIP_EXIT)


def _slug(s):
    return "".join(ch if ch.isalnum() else "_" for ch in str(s)).strip("_")[:60]


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v7 STEP 3 - bbox zoning with k-means (GeoTIFF + GeoPackage polygons + PNG)
=========================================================================

Reads step2 metrics.nc, crops to a bbox (default: West Africa + Cameroon, Chad,
CAR, Sudan, South Sudan), applies the masks and builds two zonings:

  1. zones_nb_spells          k-means on (median, mean) number of dry spells per season
                              (standardised). Zones ordered 1 = fewest spells.
  2. zones_first_spell_prob   k-means on the curve P(first dry spell starts <= X days
                              after onset), X = 20, 30, ... 90. Zones ordered 1 = lowest
                              mean probability (i.e. increasing early-season risk).

Masks (pixel hidden, reason kept in mask_reason.tif / 'mask' layer):
  outside study countries, no CHIRPS, missing rainfall, no RADS,
  bimodal regime (A2/A1 >= BIMODAL_RATIO), < STEP3_MIN_SEASONS valid seasons,
  median season length < STEP3_MIN_SEASON_LEN days.

Outputs (dryspell_v7/<region>/step3_<name>/)
  zones_nb_spells.tif, zones_first_spell_prob.tif, mask_reason.tif,
  features_*.tif, zones.gpkg (3 layers), png/*.png, zone_summary_*.csv,
  k_scan_*.csv/png (elbow + silhouette to choose k)

Usage
-----
  python 2026-09-26.step3_bbox_zoning_v07.py --region study
  python 2026-09-26.step3_bbox_zoning_v07.py --region study --k_nb 4 --k_prob 6
  python 2026-09-26.step3_bbox_zoning_v07.py --region study --bbox -18 4 16 18 --name wa_core --no_clip
"""

import os
for _v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(_v, "8")

import argparse
import logging
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dryspell_v7_common as C

warnings.filterwarnings("ignore", category=RuntimeWarning)
logger = logging.getLogger("dryspell_v7")


# =============================================================================
# K-MEANS (sklearn if available, scipy fallback)
# =============================================================================

def kmeans(X, k, seed=0, n_init=10):
    """Returns labels, centers, inertia."""
    try:
        from sklearn.cluster import KMeans
        km = KMeans(n_clusters=k, n_init=n_init, random_state=seed).fit(X)
        return km.labels_, km.cluster_centers_, float(km.inertia_)
    except ImportError:
        from scipy.cluster.vq import kmeans2
        best = None
        for i in range(n_init):
            cen, lab = kmeans2(X, k, minit="++", seed=seed + i)
            inert = float(((X - cen[lab]) ** 2).sum())
            if best is None or inert < best[2]:
                best = (lab, cen, inert)
        return best


def silhouette(X, labels, n=20000, seed=0):
    try:
        from sklearn.metrics import silhouette_score
    except ImportError:
        return np.nan
    if len(np.unique(labels)) < 2:
        return np.nan
    return float(silhouette_score(X, labels, sample_size=min(n, len(X)), random_state=seed))


def order_clusters(labels, centers, score):
    """Relabel 1..k by increasing score(centers)."""
    order = np.argsort(score(centers))
    remap = np.empty(len(order), dtype=np.int32)
    remap[order] = np.arange(1, len(order) + 1)
    return remap[labels], centers[order]


def k_scan(X, out_csv, out_png, title):
    rows = []
    for k in C.K_SCAN:
        lab, _, inert = kmeans(X, k, n_init=4)
        rows.append({"k": k, "inertia": inert, "silhouette": silhouette(X, lab)})
    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))
    for ax, col in zip(axes, ("inertia", "silhouette")):
        ax.plot(df["k"], df[col], color="#3b6fb6", linewidth=2, marker="o", markersize=5)
        ax.set_xlabel("k")
        ax.set_title(col, loc="left", fontsize=10)
        ax.grid(True, color="#e5e5e5", linewidth=0.6)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    fig.suptitle(title, x=0.01, ha="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)
    return df


# =============================================================================
# RASTER / VECTOR HELPERS
# =============================================================================

def country_mask(bnd, iso3, lon, lat):
    """True inside the selected countries (ascending-lat array)."""
    from rasterio.features import geometry_mask
    sel = bnd[bnd["iso_a3"].isin(iso3)]
    missing = sorted(set(iso3) - set(sel["iso_a3"]))
    if missing:
        logger.warning(f"Countries not found in boundaries: {missing}")
    m = geometry_mask(sel.geometry, out_shape=(len(lat), len(lon)),
                      transform=C.grid_transform(lon, lat), invert=True, all_touched=False)
    return m[::-1]


def sieve(zones, valid, lon, lat, size):
    from rasterio.features import sieve as rio_sieve
    if size <= 1:
        return zones
    z = zones[::-1].astype(np.int32)
    m = valid[::-1]
    s = rio_sieve(z, size=size, mask=m, connectivity=8)
    s = np.where(m, s, 0)
    return s[::-1].astype(np.uint8)


def polygonize(zones, lon, lat, attrs=None, name="zone"):
    import geopandas as gpd
    from rasterio.features import shapes
    from shapely.geometry import shape
    z = zones[::-1].astype(np.int32)
    geoms, vals = [], []
    for g, v in shapes(z, mask=z > 0, transform=C.grid_transform(lon, lat), connectivity=8):
        geoms.append(shape(g))
        vals.append(int(v))
    if not geoms:
        return None
    gdf = gpd.GeoDataFrame({name: vals}, geometry=geoms, crs="EPSG:4326").dissolve(by=name, as_index=False)
    gdf["area_km2"] = gdf.to_crs("EPSG:6933").area / 1e6
    if attrs is not None:
        gdf = gdf.merge(attrs, on=name, how="left")
    return gdf


def ramp(cmap_name, k):
    import matplotlib
    cm = matplotlib.colormaps[cmap_name]
    return [matplotlib.colors.to_hex(cm(v)) for v in np.linspace(0.28, 0.92, k)]


# =============================================================================
# MAIN
# =============================================================================

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", default="study", help="step2 region to read")
    ap.add_argument("--bbox", nargs=4, type=float, default=None,
                    help="lon_min lat_min lon_max lat_max (default: REGIONS['study'])")
    ap.add_argument("--name", default="bbox", help="output sub-folder suffix")
    ap.add_argument("--k_nb", type=int, default=C.K_NB)
    ap.add_argument("--k_prob", type=int, default=C.K_PROB)
    ap.add_argument("--bimodal_ratio", type=float, default=C.BIMODAL_RATIO)
    ap.add_argument("--min_seasons", type=int, default=C.STEP3_MIN_SEASONS)
    ap.add_argument("--min_season_len", type=float, default=C.STEP3_MIN_SEASON_LEN)
    ap.add_argument("--sieve", type=int, default=C.SIEVE_PIXELS)
    ap.add_argument("--no_clip", action="store_true", help="keep the whole bbox (no country clip)")
    ap.add_argument("--no_kscan", action="store_true")
    a = ap.parse_args()

    bbox = tuple(a.bbox) if a.bbox else C.REGIONS["study"]
    out = C.region_dir(a.region) / f"step3_{a.name}"
    C.setup_logging(out / "step3.log")
    ds = xr.open_dataset(C.region_dir(a.region) / "step2" / "metrics.nc")
    lon_all, lat_all = ds.lon.values, ds.lat.values
    jj = np.where((lon_all >= bbox[0]) & (lon_all <= bbox[2]))[0]
    ii = np.where((lat_all >= bbox[1]) & (lat_all <= bbox[3]))[0]
    if len(ii) == 0 or len(jj) == 0:
        sys.exit(f"bbox {bbox} does not overlap step2 grid")
    ds = ds.isel(lat=slice(ii.min(), ii.max() + 1), lon=slice(jj.min(), jj.max() + 1)).load()
    lon, lat = ds.lon.values, ds.lat.values
    logger.info("=" * 70)
    logger.info(f"v7 STEP3  region={a.region} bbox={bbox} grid {len(lon)}x{len(lat)}")
    logger.info(f"  masks: bimodal ratio >= {a.bimodal_ratio}, >= {a.min_seasons} seasons, "
                f"median season >= {a.min_season_len} d, clip={'no' if a.no_clip else C.STEP3_CLIP_ISO3}")
    logger.info("=" * 70)

    # ------------------------------------------------------------------ masks
    reason = ds["reason"].values.astype(np.uint8).copy()
    base_ok = reason == C.REASON_OK
    nv = ds["n_valid_seasons"].values
    slen = ds["season_len_median"].values
    ratio = ds["bimodal_ratio"].values
    reason[base_ok & (ratio >= a.bimodal_ratio)] = C.REASON_BIMODAL
    ok = reason == C.REASON_OK
    reason[ok & ~(nv >= a.min_seasons)] = C.REASON_FEW_SEASONS
    ok = reason == C.REASON_OK
    reason[ok & ~(slen >= a.min_season_len)] = C.REASON_SHORT_SEASON
    bnd = C.load_boundaries(bbox)
    if not a.no_clip and C.STEP3_CLIP_ISO3 and bnd is not None:
        inside = country_mask(bnd, C.STEP3_CLIP_ISO3, lon, lat)
        reason[~inside] = C.REASON_OUTSIDE
        bnd_plot = bnd[bnd["iso_a3"].isin(C.STEP3_CLIP_ISO3)]
    else:
        bnd_plot = bnd
    valid = reason == C.REASON_OK
    cnt = pd.Series(reason.ravel()).value_counts().sort_index()
    for i, v in cnt.items():
        logger.info(f"  pixels {C.REASON_LABELS[int(i)]:<28} {v:>10,}")
    if valid.sum() < 100:
        sys.exit("fewer than 100 valid pixels - check masks")
    C.save_geotiff(out / "mask_reason.tif", reason, lon, lat, nodata=255, dtype="uint8")

    nb_med = ds["nb_spells_median"].values
    nb_mean = ds["nb_spells_mean"].values
    pfl = ds["p_first_le"].values                      # (x, lat, lon)
    xs = ds["x_days"].values.astype(int)
    feat_nb = np.where(valid, nb_med, np.nan).astype(np.float32)
    C.save_geotiff(out / "features_nb_spells_median.tif", feat_nb, lon, lat)
    C.save_geotiff(out / "features_nb_spells_mean.tif", np.where(valid, nb_mean, np.nan).astype(np.float32), lon, lat)
    C.save_geotiff(out / "features_p_first_le.tif", np.where(valid[None], pfl, np.nan).astype(np.float32),
                   lon, lat, band_names=[f"p_first_le_{x}" for x in xs])

    iv = np.where(valid.ravel())[0]
    zones_out = {}

    # ------------------------------------------------------------ zoning 1: nb
    X1 = np.column_stack([nb_med.ravel()[iv], nb_mean.ravel()[iv]]).astype(np.float64)
    mu, sd = X1.mean(0), X1.std(0)
    sd[sd == 0] = 1
    Z1 = (X1 - mu) / sd
    if not a.no_kscan:
        k_scan(Z1, out / "k_scan_nb_spells.csv", out / "k_scan_nb_spells.png",
               "k-means diagnostics - dry spells per season")
    lab, cen, _ = kmeans(Z1, a.k_nb)
    lab, cen = order_clusters(lab, cen * sd + mu, lambda c: c[:, 0] * 1000 + c[:, 1])
    z1 = np.zeros(valid.size, dtype=np.uint8)
    z1[iv] = lab
    z1 = sieve(z1.reshape(valid.shape), valid, lon, lat, a.sieve)
    zones_out["nb"] = z1

    rows = []
    for z in range(1, a.k_nb + 1):
        m = z1 == z
        rows.append({"zone": z, "n_pixels": int(m.sum()),
                     "nb_median_p10": float(np.nanpercentile(nb_med[m], 10)) if m.any() else np.nan,
                     "nb_median_p50": float(np.nanmedian(nb_med[m])) if m.any() else np.nan,
                     "nb_median_p90": float(np.nanpercentile(nb_med[m], 90)) if m.any() else np.nan,
                     "nb_mean_avg": float(np.nanmean(nb_mean[m])) if m.any() else np.nan})
    s1 = pd.DataFrame(rows)
    s1["label"] = [f"Z{r.zone}: median {r.nb_median_p10:g}-{r.nb_median_p90:g} spells/season "
                   f"(mean {r.nb_mean_avg:.1f})" for r in s1.itertuples()]
    s1.to_csv(out / "zone_summary_nb_spells.csv", index=False)

    # ---------------------------------------------------------- zoning 2: prob
    X2 = pfl.reshape(len(xs), -1)[:, iv].T.astype(np.float64)
    if not a.no_kscan:
        k_scan(X2, out / "k_scan_first_spell_prob.csv", out / "k_scan_first_spell_prob.png",
               "k-means diagnostics - P(first spell <= X d)")
    lab, cen, _ = kmeans(X2, a.k_prob)
    lab, cen = order_clusters(lab, cen, lambda c: c.mean(1))
    z2 = np.zeros(valid.size, dtype=np.uint8)
    z2[iv] = lab
    z2 = sieve(z2.reshape(valid.shape), valid, lon, lat, a.sieve)
    zones_out["prob"] = z2

    rows = []
    for z in range(1, a.k_prob + 1):
        m = z2 == z
        r = {"zone": z, "n_pixels": int(m.sum())}
        for k, x in enumerate(xs):
            r[f"p_le_{x}"] = float(np.nanmean(pfl[k][m])) if m.any() else np.nan
        rows.append(r)
    s2 = pd.DataFrame(rows)
    x60 = 60 if 60 in xs else xs[len(xs) // 2]
    s2["label"] = [f"Z{r['zone']}: P(<= {x60} d) = {r[f'p_le_{x60}']:.2f}" for _, r in s2.iterrows()]
    s2.to_csv(out / "zone_summary_first_spell_prob.csv", index=False)

    # ---------------------------------------------------------------- outputs
    C.save_geotiff(out / "zones_nb_spells.tif", z1, lon, lat, nodata=0, dtype="uint8")
    C.save_geotiff(out / "zones_first_spell_prob.tif", z2, lon, lat, nodata=0, dtype="uint8")

    gpkg = out / "zones.gpkg"
    if gpkg.exists():
        gpkg.unlink()
    g1 = polygonize(z1, lon, lat, s1)
    g2 = polygonize(z2, lon, lat, s2)
    mask_codes = np.where(np.isin(reason, [C.REASON_BIMODAL, C.REASON_FEW_SEASONS, C.REASON_SHORT_SEASON,
                                           C.REASON_NO_RADS, C.REASON_MISSING]), reason, 0).astype(np.uint8)
    g3 = polygonize(mask_codes, lon, lat, name="reason")
    if g3 is not None:
        g3["label"] = g3["reason"].map(C.REASON_LABELS)
    for g, layer in ((g1, "zones_nb_spells"), (g2, "zones_first_spell_prob"), (g3, "mask")):
        if g is not None:
            g.to_file(gpkg, layer=layer, driver="GPKG")
    logger.info(f"Written {gpkg}")

    col1 = ramp("Oranges", a.k_nb)
    col2 = ramp("Purples", a.k_prob)
    disp_reason = np.where(reason == C.REASON_OUTSIDE, 255, reason)
    C.plot_map(out / "png" / "zones_nb_spells.png", np.where(z1 > 0, z1, np.nan).astype(float), lon, lat,
               f"Zones - number of dry spells per season (k-means, k={a.k_nb})", boundaries=bnd_plot,
               reason=disp_reason, categorical=[(z, col1[z - 1], s1.loc[z - 1, "label"]) for z in range(1, a.k_nb + 1)])
    C.plot_map(out / "png" / "zones_first_spell_prob.png", np.where(z2 > 0, z2, np.nan).astype(float), lon, lat,
               f"Zones - P(first dry spell starts <= X d after onset) (k-means, k={a.k_prob})",
               boundaries=bnd_plot, reason=disp_reason,
               categorical=[(z, col2[z - 1], s2.loc[z - 1, "label"]) for z in range(1, a.k_prob + 1)])
    C.plot_map(out / "png" / "nb_spells_median.png", feat_nb, lon, lat,
               "Median number of dry spells per season (>=10 d, <1 mm)", "spells/season", cmap="Oranges",
               vmin=0, boundaries=bnd_plot, reason=disp_reason)
    k60 = list(xs).index(x60)
    C.plot_map(out / "png" / f"p_first_le_{x60}.png", np.where(valid, pfl[k60], np.nan), lon, lat,
               f"P(first dry spell starts <= {x60} d after onset)", "probability", cmap="Purples",
               vmin=0, vmax=1, boundaries=bnd_plot, reason=disp_reason)

    # zone curves
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for z in range(1, a.k_prob + 1):
        ys = [s2.loc[z - 1, f"p_le_{x}"] for x in xs]
        ax.plot(xs, ys, color=col2[z - 1], linewidth=2, marker="o", markersize=5, label=s2.loc[z - 1, "label"])
        ax.annotate(f"Z{z}", (xs[-1], ys[-1]), xytext=(6, 0), textcoords="offset points",
                    va="center", fontsize=8, color="#333333")
    ax.set_xlabel("X, days after RADS onset")
    ax.set_ylabel("P(first dry spell starts <= X)")
    ax.set_ylim(0, 1)
    ax.set_xticks(xs)
    ax.grid(True, color="#e5e5e5", linewidth=0.6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, fontsize=7, loc="upper left")
    ax.set_title("Mean curve per zone", loc="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(out / "png" / "zone_curves_first_spell_prob.png", dpi=180)
    plt.close(fig)

    logger.info(f"valid pixels zoned: {valid.sum():,}")
    logger.info(f"STEP3 done -> {out}")


if __name__ == "__main__":
    main()

"""
Benin + Togo friction maps for 2020 and 2026 (run by .github/workflows/accessibility.yml).

Expects in data/ (same files as run_benin_togo.py, plus the country outlines):
  benin-200101.osm.pbf  togo-200101.osm.pbf   benin-260901.osm.pbf  togo-260901.osm.pbf
  Western_Africa.zip    benin.poly  togo.poly  (https://download.geofabrik.de/africa/<c>.poly)

Land cover (ESA WorldCover 2021, used for both dates so that only roads change)
and elevation (Copernicus GLO-30) are read directly from their public S3
buckets; pass local tiles to friction.py instead if you have them.

Large rasters go to output/friction/, small QA files to results/friction/.
"""
import time
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, TwoSlopeNorm

import friction as fr

ROOT = Path(__file__).resolve().parents[1]   # accessibility_update/
DATA = ROOT / "data"
OUT, RES = ROOT / "output" / "friction", ROOT / "results" / "friction"
T1, T2 = "200101", "260901"
COUNTRIES = ["benin", "togo"]
OSM_EXT = ".osm.pbf"            # tests swap in ".osm" (XML) files
# 20 x 20 km zooms (lon, lat) on areas with many new OSM roads in the roads run
ZOOMS = {"Dapaong_TGO": (0.20, 10.86), "Kandi_BEN": (2.94, 11.13)}


def pool(a, step, how):
    """Block-reduce a masked array (min keeps thin roads visible in friction maps)."""
    h, w = (a.shape[0] // step) * step, (a.shape[1] // step) * step
    b = a[:h, :w].reshape(h // step, step, w // step, step)
    return getattr(b, how)(axis=(1, 3))


def quicklook(tifs, titles, path, norm=None, cmap="magma_r", step=10, label="", how="min"):
    fig, axes = plt.subplots(1, len(tifs), figsize=(5 * len(tifs), 7))
    for ax, tif, title in zip(np.atleast_1d(axes), tifs, titles):
        with rasterio.open(tif) as r:
            a = pool(r.read(1, masked=True), step, how)
        im = ax.imshow(a, norm=norm, cmap=cmap, interpolation="nearest")
        ax.set_title(title); ax.set_xticks([]); ax.set_yticks([])
    fig.colorbar(im, ax=axes, shrink=0.6, label=label)
    fig.savefig(path, dpi=100, bbox_inches="tight"); plt.close(fig)


def zoom(tifs, titles, lonlat, path, norm, half_m=10_000):
    from pyproj import Transformer
    fig, axes = plt.subplots(1, len(tifs), figsize=(5 * len(tifs), 5))
    for ax, tif, title in zip(axes, tifs, titles):
        with rasterio.open(tif) as r:
            x, y = Transformer.from_crs(4326, r.crs, always_xy=True).transform(*lonlat)
            win = rasterio.windows.from_bounds(x - half_m, y - half_m, x + half_m, y + half_m,
                                               r.transform)
            a = r.read(1, window=win, masked=True)
        im = ax.imshow(a, norm=norm, cmap="magma_r", interpolation="nearest")
        ax.set_title(title); ax.set_xticks([]); ax.set_yticks([])
    fig.colorbar(im, ax=axes, shrink=0.8, label="friction (min/m, log)")
    fig.savefig(path, dpi=100, bbox_inches="tight"); plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True); RES.mkdir(parents=True, exist_ok=True)
    pbf = lambda t: [str(DATA / f"{c}-{t}{OSM_EXT}") for c in COUNTRIES]
    t = time.time()
    fr.main(["--osm-pbf-t1", *pbf(T1), "--osm-pbf-t2", *pbf(T2),
             "--ms-roads", str(DATA / "Western_Africa.zip"), "--iso3", "BEN", "TGO",
             "--boundary", *[str(DATA / f"{c}.poly") for c in COUNTRIES],
             "--crs", "EPSG:32631", "--out-dir", str(OUT)])
    elapsed = time.time() - t

    s = pd.read_csv(OUT / "friction_summary.csv")
    s.to_csv(RES / "friction_summary.csv", index=False)
    (RES / "run_log.txt").write_text(f"friction.main: {elapsed:.0f}s\n\n{s.to_string(index=False)}\n")

    norm = LogNorm(vmin=0.06 / 100, vmax=0.06 / 0.5)   # 100 km/h .. 0.5 km/h
    tifs = [OUT / f"friction_{k}.tif" for k in ("t1", "t2", "t2_ml")]
    titles = ["OSM 2020-01-01", "OSM 2026-09-01", "OSM 2026 + ML roads"]
    quicklook(tifs, titles, RES / "friction_maps.png", norm=norm,
              label="friction (min/m, log)")
    # gains and losses in separate panels: one pooled value per block would hide one of them
    chg = OUT / "speed_change_t2_minus_t1_kmh.tif"
    fig, axes = plt.subplots(1, 2, figsize=(10, 7))
    with rasterio.open(chg) as r:
        a = r.read(1, masked=True)
    for ax, how, title in zip(axes, ["max", "min"], ["faster in 2026 (block max)",
                                                      "slower in 2026 (block min)"]):
        im = ax.imshow(pool(a, 10, how), cmap="RdBu", interpolation="nearest",
                       norm=TwoSlopeNorm(0, vmin=-20, vmax=20))
        ax.set_title(title); ax.set_xticks([]); ax.set_yticks([])
    fig.colorbar(im, ax=axes, shrink=0.6, label="speed change 2026 - 2020 (km/h)")
    fig.savefig(RES / "speed_change.png", dpi=100, bbox_inches="tight"); plt.close(fig)
    for name, ll in ZOOMS.items():
        zoom(tifs, titles, ll, RES / f"zoom_{name}.png", norm)
    print(f"done in {elapsed:.0f}s")


if __name__ == "__main__":
    main()

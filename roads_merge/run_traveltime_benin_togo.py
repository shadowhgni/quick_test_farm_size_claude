"""
Benin + Togo travel time to cities and ports, 2020 vs 2026
(run by .github/workflows/friction.yml after run_friction_benin_togo.py).

Four scenarios; the change between consecutive ones isolates one factor:
  2020    OSM 2020 roads            + GHSL 2020 settlements
  2026r   OSM 2026 roads            + GHSL 2020 settlements   -> effect of new roads
  2026    OSM 2026 roads            + GHSL 2025 settlements   -> + city growth
  2026ml  OSM 2026 + Microsoft ML   + GHSL 2025 settlements   -> + ML gap-fill roads

Layers: cities >= 50,000 (size 6, the headline), cities >= 5,000 (size 9),
medium-or-larger ports (size 2) and any port (size 5).

Expects in data/: GHS_SMOD_E2020/E2025 and GHS_POP_E2020/E2025 1 km zips (R2023A,
Mollweide) and UpdatedPub150.csv (World Port Index); friction rasters in
output_friction_benin_togo/.
"""
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
import rasterio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

import traveltime as tt

DATA, FRIC = Path("data"), Path("output_friction_benin_togo")
OUT, RES = Path("output_traveltime_benin_togo"), Path("results_traveltime_benin_togo")
SMOD = "GHS_SMOD_E{y}_GLOBE_R2023A_54009_1000_V2_0.zip"
POP = "GHS_POP_E{y}_GLOBE_R2023A_54009_1000_V1_0.zip"
SCENARIOS = {"2020": ("t1", 2020), "2026r": ("t2", 2020),
             "2026": ("t2", 2025), "2026ml": ("t2_ml", 2025)}
CITY_SIZES, PORT_SIZES = ["6", "9"], ["2", "5"]


def read(path, step=5):
    with rasterio.open(path) as r:
        return r.read(1, masked=True)[::step, ::step]


def main():
    OUT.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
    t = time.time()
    s = tt.main(["--friction", *[str(FRIC / f"friction_{f}.tif") for f, _ in SCENARIOS.values()],
                 "--labels", *SCENARIOS,
                 "--smod", *[str(DATA / SMOD.format(y=y)) for _, y in SCENARIOS.values()],
                 "--pop", *[str(DATA / POP.format(y=y)) for _, y in SCENARIOS.values()],
                 "--ports", str(DATA / "UpdatedPub150.csv"),
                 "--city-sizes", *CITY_SIZES, "--port-sizes", *PORT_SIZES,
                 "--out-dir", str(OUT)])
    elapsed = time.time() - t
    s.to_csv(RES / "traveltime_summary.csv", index=False)

    # settlement counts by class, 2020 vs 2025
    counts = []
    for label in ("2020", "2026"):
        c = gpd.read_file(OUT / f"cities_{label}.gpkg")
        counts.append(c.groupby("size_class").agg(n=("pop", "size"), pop=("pop", "sum"))
                      .assign(ghsl_epoch=2020 if label == "2020" else 2025).reset_index())
    pd.concat(counts).to_csv(RES / "settlements_by_class.csv", index=False)
    (RES / "run_log.txt").write_text(f"traveltime.main: {elapsed:.0f}s\n\n{s.to_string(index=False)}\n")

    # maps: travel time to cities >= 50k, 2020 and 2026, and the changes
    fig, axes = plt.subplots(1, 2, figsize=(10, 7))
    for ax, label in zip(axes, ["2020", "2026"]):
        im = ax.imshow(read(OUT / f"traveltime_{label}_city6.tif"), cmap="viridis",
                       vmin=0, vmax=240, interpolation="nearest")
        ax.set_title(f"to cities >= 50k, {label}"); ax.set_xticks([]); ax.set_yticks([])
    fig.colorbar(im, ax=axes, shrink=0.6, label="minutes (capped at 240)")
    fig.savefig(RES / "traveltime_city6.png", dpi=100, bbox_inches="tight"); plt.close(fig)

    pairs = [("2026r", "2020", "new roads"), ("2026", "2026r", "city growth"),
             ("2026ml", "2026", "ML gap-fill")]
    fig, axes = plt.subplots(1, 3, figsize=(15, 7))
    for ax, (b, a, what) in zip(axes, pairs):
        im = ax.imshow(read(OUT / f"traveltime_change_{b}_minus_{a}_city6.tif"), cmap="RdBu_r",
                       norm=TwoSlopeNorm(0, vmin=-60, vmax=60), interpolation="nearest")
        ax.set_title(f"{what}: {b} - {a}"); ax.set_xticks([]); ax.set_yticks([])
    fig.colorbar(im, ax=axes, shrink=0.6, label="change in minutes to cities >= 50k (blue = faster)")
    fig.savefig(RES / "traveltime_city6_change.png", dpi=100, bbox_inches="tight"); plt.close(fig)
    print(f"done in {elapsed:.0f}s")


if __name__ == "__main__":
    main()

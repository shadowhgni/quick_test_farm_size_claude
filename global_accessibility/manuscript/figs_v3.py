"""Figures of manuscript v3 (three reference years). Run from global_accessibility/test_results:
    python ../manuscript/figs_v3.py
Writes ../manuscript/figs_v3/*.png and ../manuscript/figs_v3/sizes.json."""
import json
import shutil
from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd
import rasterio

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import BoundaryNorm, ListedColormap  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

OUT = Path(__file__).resolve().parent / "figs_v3"
OUT.mkdir(exist_ok=True)
Y = [2015, 2020, 2026]
INK, MUTED = "#0b0b0b", "#52514e"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "font.family": "DejaVu Sans"})
TT_BINS = [0, 15, 30, 60, 120, 240, 480, 960, 65535]
TT_COL = ["#f7fbff", "#deebf7", "#c6dbef", "#9ecae1", "#6baed6", "#3182bd", "#08519c", "#08306b"]
CH_BINS = [-32767, -60, -30, -10, -2, 2, 10, 30, 60, 32767]
CH_COL = ["#2166ac", "#4393c3", "#92c5de", "#d1e5f0", "#e0e0e0", "#fddbc7", "#f4a582", "#d6604d", "#b2182b"]
borders = gpd.read_file("methods/african_borders.gpkg")
TTN, TTC = BoundaryNorm(TT_BINS, len(TT_COL)), ListedColormap(TT_COL)
CHN, CHC = BoundaryNorm(CH_BINS, len(CH_COL)), ListedColormap(CH_COL)


def band(path, b):
    with rasterio.open(path) as r:
        a = r.read(b).astype(float)
        ext = (r.bounds.left, r.bounds.right, r.bounds.bottom, r.bounds.top)
        return np.ma.masked_equal(a, r.nodata), ext


def panel(ax, a, ext, cmap, norm, title):
    im = ax.imshow(a, extent=ext, cmap=cmap.with_extremes(bad="white"), norm=norm, interpolation="nearest")
    borders.plot(ax=ax, color=INK, lw=0.5)
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3])
    ax.set_title(title, loc="left", fontsize=10)
    ax.tick_params(labelsize=7)
    return im


def years_and_changes(b, label, fname):
    """Row 1: the three years; row 2: changes 2020-2015, 2026-2020, 2026-2015."""
    fig, ax = plt.subplots(2, 3, figsize=(12, 11.2), constrained_layout=True)
    ext = None
    for i, y in enumerate(Y):
        a, ext = band(f"cog_1km/traveltime_{y}_1km.tif", b)
        im = panel(ax[0, i], a, ext, TTC, TTN, f"{'abc'[i]}  {y}")
    cb = fig.colorbar(im, ax=ax[0, :], orientation="horizontal", shrink=0.5, pad=0.02, ticks=TT_BINS[:-1])
    cb.set_label(f"travel time to {label} (minutes)")
    for i, (a0, a1) in enumerate([(2015, 2020), (2020, 2026), (2015, 2026)]):
        a, _ = band(f"cog_1km/traveltime_change_{a1}_minus_{a0}_1km.tif", b)
        im2 = panel(ax[1, i], a, ext, CHC, CHN, f"{'def'[i]}  change, {a1} − {a0}")
    cb2 = fig.colorbar(im2, ax=ax[1, :], orientation="horizontal", shrink=0.5, pad=0.02, ticks=CH_BINS[1:-1])
    cb2.set_label("change (minutes; blue = faster)")
    fig.savefig(OUT / fname, dpi=190); plt.close(fig)


years_and_changes(11, "the nearest settlement of ≥ 50,000 inhabitants", "fig2_cities50k.png")
years_and_changes(17, "the nearest port, any size", "figS_ports.png")

# friction as speed, three years
fig, ax = plt.subplots(1, 3, figsize=(12, 6.2), constrained_layout=True)
for i, y in enumerate(Y):
    f, ext = band(f"cog_1km/friction_{y}_1km.tif", 1)
    im = panel(ax[i], 60 / (1000 * f), ext, plt.get_cmap("Greys"),
               BoundaryNorm([0, 2, 4, 6, 15, 30, 45, 60, 100], 256), f"{'abc'[i]}  {y}")
cb = fig.colorbar(im, ax=ax, orientation="horizontal", shrink=0.5, pad=0.02)
cb.set_label("speed implied by the friction surface (km/h)")
fig.savefig(OUT / "figS_friction.png", dpi=190); plt.close(fig)

# Nelson difference maps (2015), rendered by the script
fig, ax = plt.subplots(1, 2, figsize=(12.7, 8.5), constrained_layout=True)
for a_, f, t in ((ax[0], "difference_cities_11_2015_minus_nelson2015.png", "a  settlements 50,000–50 million"),
                 (ax[1], "difference_ports_5_2015_minus_nelson2015.png", "b  ports, any size")):
    a_.imshow(plt.imread(f"nelson_comparison/{f}")); a_.axis("off"); a_.set_title(t, loc="left", fontsize=11)
fig.savefig(OUT / "fig3_nelson_difference.png", dpi=200); plt.close(fig)

# OSRM scatter by distance band
v = pd.read_csv("routing_validation/pairs_2026.csv")
ok = v.osrm_min.notna() & (v.snap_origin_m <= 1000) & (v.snap_city_m <= 1000) & (v.osrm_min > 0)
v = v[ok]
bands = [(10, 50), (50, 100), (100, 200), (200, 300)]
cols = ["#2a78d6", "#1baf7a", "#eda100", "#e34948"]
fig, ax = plt.subplots(figsize=(4.8, 4.8), constrained_layout=True)
for (lo, hi), c in zip(bands, cols):
    s = v[(v.great_circle_km >= lo) & (v.great_circle_km < hi)]
    ax.scatter(s.osrm_min, s.ours_min, s=13, color=c, edgecolor="white", lw=0.3, label=f"{lo}–{hi} km ({len(s)})")
lim = [5, max(v.osrm_min.max(), v.ours_min.max()) * 1.2]
ax.plot(lim, lim, color=MUTED, lw=0.8, label="1:1")
ax.plot(lim, [x * 1.3 for x in lim], color=MUTED, lw=0.6, ls="--", label="±30%")
ax.plot(lim, [x / 1.3 for x in lim], color=MUTED, lw=0.6, ls="--")
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("OSRM car, free flow (minutes)"); ax.set_ylabel("this study, 2026 (minutes)")
ax.legend(frameon=False, loc="upper left", fontsize=7.5); ax.grid(color="#e6e6e3", lw=0.5)
fig.savefig(OUT / "fig4_osrm.png", dpi=220); plt.close(fig)

shutil.copy("sensitivity/sensitivity.png", OUT / "fig5_sensitivity.png")

# workflow
W, H, XS, YS = 0.168, 0.2, [0.0, 0.205, 0.41, 0.615, 0.82], [0.64, 0.36, 0.08]
cells = {(0, 0): "OSM full history\ncut at 1 January\n2015 / 2020 / 2026", (0, 1): "Microsoft ML roads\n(last year only)",
         (0, 2): "Weiss et al. 2015 friction\n(OSM + Google roads)",
         (1, 0): "Road speed by class\n× unpaved factor\n× corruption factor", (1, 1): "Roads on open water\nremoved (bridges kept)",
         (1, 2): "Gaps filled (2015, 2020)\nwhere Weiss network\nand OSM 2026 agree",
         (2, 0): "WorldCover 2021 walking\nspeed × Tobler(slope)\n(Copernicus GLO-90)", (2, 1): "Friction surface\n(min/m), 30″ grid,\none per year",
         (2, 2): "African border\ncheckpoints: 15 min\n/ (1 − K·c̄)",
         (3, 0): "Destinations: GHSL urban\nclusters (12 layers),\nWorld Port Index (5)", (3, 1): "Geodesic 8-neighbour\nDijkstra: 17 layers\nper year",
         (3, 2): "Store of every grid\n(COGs + manifest)\nfor reuse",
         (4, 0): "Comparison with\nNelson et al. 2019\n(all years, 17 layers)", (4, 1): "Validation with\nOSRM per continent\n(last year)",
         (4, 2): "COGs 1 km / 10 km,\nchange maps, tables,\nmethods folder"}
fig, ax = plt.subplots(figsize=(10, 4.2)); ax.axis("off")
for (c, r), t in cells.items():
    x, y = XS[c], YS[r]
    ax.add_patch(FancyBboxPatch((x, y), W, H, boxstyle="round,pad=0.005,rounding_size=0.015", fc="#f3f6fb", ec="#2a78d6", lw=0.8))
    ax.text(x + W / 2, y + H / 2, t, ha="center", va="center", fontsize=7.4, color=INK, linespacing=1.25)
R = lambda c, r: (XS[c] + W, YS[r] + H / 2); L = lambda c, r: (XS[c], YS[r] + H / 2)
T = lambda c, r: (XS[c] + W / 2, YS[r] + H); B = lambda c, r: (XS[c] + W / 2, YS[r])
arrows = [(R(0, 0), L(1, 0)), (R(0, 1), L(1, 1)), (R(0, 2), L(1, 2)), (R(1, 0), L(2, 1)), (R(1, 1), L(2, 1)), (R(1, 2), L(2, 1)),
          (B(2, 0), T(2, 1)), (T(2, 2), B(2, 1)), (R(2, 1), L(3, 1)), (B(3, 0), T(3, 1)), (B(3, 1), T(3, 2)),
          (R(3, 1), L(4, 0)), (R(3, 1), L(4, 1)), (R(3, 1), L(4, 2))]
for a, b in arrows:
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=0.8, shrinkA=1, shrinkB=1))
ax.set_xlim(-0.01, 1.0); ax.set_ylim(0.05, 0.87)
fig.savefig(OUT / "fig1_workflow.png", dpi=220, bbox_inches="tight"); plt.close(fig)

sizes = {}
for f in OUT.glob("*.png"):
    with rasterio.open(f) as r:
        sizes[f.name] = [r.width, r.height]
(OUT / "sizes.json").write_text(json.dumps(sizes))
print("figures:", sorted(sizes))

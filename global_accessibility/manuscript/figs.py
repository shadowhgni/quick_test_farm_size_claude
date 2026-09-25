import numpy as np, rasterio, geopandas as gpd, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import FancyBboxPatch
OUT = "/tmp/claude-0/-home-user-quick-test-farm-size-claude/7b8a0082-c0a1-5c1e-a2ea-1788c7b9a0f8/scratchpad/paper/figs/"
INK, MUTED = "#0b0b0b", "#52514e"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "font.family": "DejaVu Sans"})
TT_BINS = [0, 15, 30, 60, 120, 240, 480, 960, 65535]
TT_COL = ["#f7fbff", "#deebf7", "#c6dbef", "#9ecae1", "#6baed6", "#3182bd", "#08519c", "#08306b"]
CH_BINS = [-32767, -60, -30, -10, -2, 2, 10, 30, 60, 32767]
CH_COL = ["#2166ac", "#4393c3", "#92c5de", "#d1e5f0", "#e0e0e0", "#fddbc7", "#f4a582", "#d6604d", "#b2182b"]
borders = gpd.read_file("methods/african_borders.gpkg")

def band(path, b):
    with rasterio.open(path) as r:
        a = r.read(b).astype(float); nd = r.nodata; ext = (r.bounds.left, r.bounds.right, r.bounds.bottom, r.bounds.top)
    return np.ma.masked_equal(a, nd), ext

def panel(ax, a, ext, cmap, norm, title):
    im = ax.imshow(a, extent=ext, cmap=cmap.with_extremes(bad="white"), norm=norm, interpolation="nearest")
    borders.plot(ax=ax, color=INK, lw=0.5)
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3])
    ax.set_title(title, loc="left", fontsize=10)
    ax.set_xlabel("longitude (°)"); ax.set_ylabel("latitude (°)")
    return im

# Figure 2: cities >= 50k (band 11) 2015, 2026, change
tt15, ext = band("cog_1km/traveltime_2015_1km.tif", 11)
tt26, _ = band("cog_1km/traveltime_2026_1km.tif", 11)
ch, _ = band("cog_1km/traveltime_change_2026_minus_2015_1km.tif", 11)
fig, ax = plt.subplots(1, 3, figsize=(13, 6.2), constrained_layout=True)
n1 = BoundaryNorm(TT_BINS, len(TT_COL)); c1 = ListedColormap(TT_COL)
panel(ax[0], tt15, ext, c1, n1, "a  2015")
im = panel(ax[1], tt26, ext, c1, n1, "b  2026")
cb = fig.colorbar(im, ax=ax[:2], orientation="horizontal", shrink=0.6, pad=0.02, ticks=TT_BINS[:-1])
cb.set_label("travel time to the nearest settlement ≥ 50,000 inhabitants (minutes)")
im2 = panel(ax[2], ch, ext, ListedColormap(CH_COL), BoundaryNorm(CH_BINS, len(CH_COL)), "c  change, 2026 − 2015")
cb2 = fig.colorbar(im2, ax=ax[2], orientation="horizontal", shrink=0.9, pad=0.02, ticks=CH_BINS[1:-1])
cb2.set_label("change (minutes; blue = faster)")
fig.savefig(OUT + "fig2_cities50k.png", dpi=220); plt.close(fig)

# Figure 3: ports (band 17)
p15, _ = band("cog_1km/traveltime_2015_1km.tif", 17); p26, _ = band("cog_1km/traveltime_2026_1km.tif", 17)
pch, _ = band("cog_1km/traveltime_change_2026_minus_2015_1km.tif", 17)
fig, ax = plt.subplots(1, 3, figsize=(13, 6.2), constrained_layout=True)
panel(ax[0], p15, ext, c1, n1, "a  2015"); im = panel(ax[1], p26, ext, c1, n1, "b  2026")
cb = fig.colorbar(im, ax=ax[:2], orientation="horizontal", shrink=0.6, pad=0.02, ticks=TT_BINS[:-1]); cb.set_label("travel time to the nearest port, any size (minutes)")
im2 = panel(ax[2], pch, ext, ListedColormap(CH_COL), BoundaryNorm(CH_BINS, len(CH_COL)), "c  change, 2026 − 2015")
cb2 = fig.colorbar(im2, ax=ax[2], orientation="horizontal", shrink=0.9, pad=0.02, ticks=CH_BINS[1:-1]); cb2.set_label("change (minutes; blue = faster)")
fig.savefig(OUT + "figS_ports.png", dpi=200); plt.close(fig)

# Friction maps (supplementary)
f15, _ = band("cog_1km/friction_2015_1km.tif", 1); f26, _ = band("cog_1km/friction_2026_1km.tif", 1)
fig, ax = plt.subplots(1, 2, figsize=(9.5, 6.4), constrained_layout=True)
for a_, f, t in ((ax[0], f15, "a  2015"), (ax[1], f26, "b  2026")):
    sp = 60 / (1000 * f)
    im = panel(a_, sp, ext, plt.get_cmap("Greys"), BoundaryNorm([0, 2, 4, 6, 15, 30, 45, 60, 100], 256), t)
cb = fig.colorbar(im, ax=ax, orientation="horizontal", shrink=0.6, pad=0.02); cb.set_label("speed implied by the friction surface (km/h)")
fig.savefig(OUT + "figS_friction.png", dpi=200); plt.close(fig)

# Figure 4: Nelson difference (already rendered) + OSRM scatter re-drawn
v = pd.read_csv("routing_validation/pairs_2026.csv")
ok = v.osrm_min.notna() & (v.snap_origin_m <= 1000) & (v.snap_city_m <= 1000) & (v.osrm_min > 0)
fig, ax = plt.subplots(figsize=(4.6, 4.6), constrained_layout=True)
ax.scatter(v.osrm_min[ok], v.ours_min[ok], s=14, color="#2a78d6", edgecolor="white", lw=0.4, label=f"{ok.sum()} pairs")
lim = [10, 400]
ax.plot(lim, lim, color=MUTED, lw=0.8, label="1:1")
ax.plot(lim, [x * 1.3 for x in lim], color=MUTED, lw=0.6, ls="--", label="±30%")
ax.plot(lim, [x / 1.3 for x in lim], color=MUTED, lw=0.6, ls="--")
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("OSRM car, free flow (minutes)"); ax.set_ylabel("this study, 2026 (minutes)")
ax.legend(frameon=False, loc="upper left"); ax.grid(color="#e6e6e3", lw=0.5)
fig.savefig(OUT + "fig4_osrm.png", dpi=220); plt.close(fig)

# Figure 1: workflow
fig, ax = plt.subplots(figsize=(10, 4.4)); ax.axis("off")
boxes = [
 (0.01, 0.62, "OSM snapshots\n1 Jan 2015 / 2026\n(Geofabrik)"), (0.01, 0.34, "Microsoft ML roads\n(end year only)"),
 (0.01, 0.06, "Weiss et al. 2015\nfriction (OSM+Google)"),
 (0.22, 0.62, "Road speeds by class\n× unpaved factor\n× corruption factor"), (0.22, 0.34, "Roads on open water\nremoved (except bridges)"),
 (0.22, 0.06, "2015 gaps filled where\nWeiss network ∩ OSM 2026"),
 (0.43, 0.62, "WorldCover 2021 walking\nspeed × Tobler(slope)\n(Copernicus GLO-90)"), (0.43, 0.34, "Friction surface\n(min/m), 30″ grid"),
 (0.43, 0.06, "African border checkpoints\n+15 min / (1 − K·c̄)"),
 (0.64, 0.62, "Destinations: GHSL urban\nclusters (12 classes),\nWorld Port Index (5)"), (0.64, 0.34, "Geodesic 8-neighbour\nDijkstra → 17 layers\nper year"),
 (0.85, 0.62, "Nelson et al. 2019\ncomparison (2015)"), (0.85, 0.34, "OSRM validation\n(end year)"), (0.85, 0.06, "COGs 1 km / 10 km,\nmaps, tables, methods"),
]
for x, y, t in boxes:
    ax.add_patch(FancyBboxPatch((x, y), 0.14, 0.26, boxstyle="round,pad=0.01,rounding_size=0.02", fc="#f3f6fb", ec="#2a78d6", lw=0.8))
    ax.text(x + 0.07, y + 0.13, t, ha="center", va="center", fontsize=8, color=INK)
arrows = [((0.15, 0.75), (0.22, 0.75)), ((0.15, 0.47), (0.22, 0.47)), ((0.15, 0.19), (0.22, 0.19)),
          ((0.36, 0.75), (0.43, 0.47)), ((0.36, 0.47), (0.43, 0.47)), ((0.36, 0.19), (0.43, 0.47)),
          ((0.50, 0.62), (0.50, 0.60)), ((0.50, 0.32), (0.50, 0.34)), ((0.57, 0.47), (0.64, 0.47)),
          ((0.71, 0.62), (0.71, 0.60)), ((0.78, 0.47), (0.85, 0.75)), ((0.78, 0.47), (0.85, 0.47)), ((0.78, 0.47), (0.85, 0.19))]
for (x0, y0), (x1, y1) in arrows:
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=0.8))
ax.set_xlim(0, 1); ax.set_ylim(0, 0.9)
fig.savefig(OUT + "fig1_workflow.png", dpi=220, bbox_inches="tight"); plt.close(fig)
print("ok")

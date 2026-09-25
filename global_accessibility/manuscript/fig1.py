import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
W, H, XS, YS = 0.168, 0.2, [0.0, 0.205, 0.41, 0.615, 0.82], [0.64, 0.36, 0.08]
cells = {(0,0): "OSM snapshots\n1 Jan start / end year\n(Geofabrik)", (0,1): "Microsoft ML roads\n(end year only)",
 (0,2): "Weiss et al. 2015 friction\n(OSM + Google roads)",
 (1,0): "Road speed by class\n× unpaved factor\n× corruption factor", (1,1): "Roads on open water\nremoved (bridges kept)",
 (1,2): "2015 gaps filled where\nWeiss network and\nOSM end year agree",
 (2,0): "WorldCover 2021 walking\nspeed × Tobler(slope)\n(Copernicus GLO-90)", (2,1): "Friction surface\n(min/m), 30″ grid",
 (2,2): "African border\ncheckpoints: 15 min\n/ (1 − K·c̄)",
 (3,0): "Destinations: GHSL urban\nclusters (12 layers),\nWorld Port Index (5)", (3,1): "Geodesic 8-neighbour\nDijkstra: 17 layers\nper year",
 (4,0): "Comparison with\nNelson et al. 2019\n(2015)", (4,1): "Validation with\nOSRM (end year)", (4,2): "COGs 1 km / 10 km,\nmaps, tables,\nmethods folder"}
fig, ax = plt.subplots(figsize=(10, 4.2)); ax.axis("off")
for (c, r), t in cells.items():
    x, y = XS[c], YS[r]
    ax.add_patch(FancyBboxPatch((x, y), W, H, boxstyle="round,pad=0.005,rounding_size=0.015", fc="#f3f6fb", ec="#2a78d6", lw=0.8))
    ax.text(x + W / 2, y + H / 2, t, ha="center", va="center", fontsize=7.4, color="#0b0b0b", linespacing=1.25)
R = lambda c, r: (XS[c] + W, YS[r] + H / 2); L = lambda c, r: (XS[c], YS[r] + H / 2)
T = lambda c, r: (XS[c] + W / 2, YS[r] + H); B = lambda c, r: (XS[c] + W / 2, YS[r])
arrows = [(R(0,0), L(1,0)), (R(0,1), L(1,1)), (R(0,2), L(1,2)), (R(1,0), L(2,1)), (R(1,1), L(2,1)), (R(1,2), L(2,1)),
          (B(2,0), T(2,1)), (T(2,2), B(2,1)), (R(2,1), L(3,1)), (B(3,0), T(3,1)),
          (R(3,1), L(4,0)), (R(3,1), L(4,1)), (R(3,1), L(4,2))]
for a, b in arrows:
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="-|>", color="#52514e", lw=0.8, shrinkA=1, shrinkB=1))
ax.set_xlim(-0.01, 1.0); ax.set_ylim(0.05, 0.87)
fig.savefig("figs/fig1_workflow.png", dpi=220, bbox_inches="tight")

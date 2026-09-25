import math
import sys
import time
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent))
import geodijkstra as gd  # noqa: E402

D = 1 / 120   # 30 arc-seconds


def test_matches_skimage_near_equator():
    from skimage.graph import MCP_Geometric
    rng = np.random.default_rng(0)
    H, W = 200, 300
    f = rng.uniform(0.001, 0.02, (H, W)).astype(np.float32)
    f[50:150, 140] = np.inf                                   # wall with gaps
    src = np.zeros((H, W), bool); src[10, 10] = True; src[180, 250] = True
    # grid centred on the equator: cells ~ square
    t = gd.travel_time(f, src, lat_top=H / 2 * D, dlat=D, dlon=D)
    cell = gd.R_EARTH * math.radians(D)
    cum, _ = MCP_Geometric(np.where(np.isfinite(f), f * cell, np.inf)).find_costs(np.argwhere(src))
    ok = np.isfinite(cum)
    assert np.array_equal(ok, np.isfinite(t))
    # rows are at |lat| <= 0.83 deg -> cos >= 0.9999, so within 0.02 %
    assert np.allclose(t[ok], cum[ok], rtol=2e-4)


def test_east_west_shrinks_with_latitude():
    H, W = 3, 101
    f = np.full((H, W), 0.01, np.float32)                     # 6 km/h
    src = np.zeros((H, W), bool); src[1, 0] = True
    t = gd.travel_time(f, src, lat_top=60 + 1.5 * D, dlat=D, dlon=D)
    ew60 = gd.R_EARTH * math.cos(math.radians(60)) * math.radians(D)
    assert t[1, 100] == pytest.approx(100 * ew60 * 0.01, rel=1e-5)
    assert t[1, 100] == pytest.approx(0.5 * 100 * gd.R_EARTH * math.radians(D) * 0.01, rel=1e-3)


def test_wraps_across_dateline():
    H, W = 5, 360
    f = np.full((H, W), 0.01, np.float32)
    src = np.zeros((H, W), bool); src[2, 0] = True
    t_wrap = gd.travel_time(f, src, lat_top=2.5, dlat=1, dlon=1, wrap=True)
    t_flat = gd.travel_time(f, src, lat_top=2.5, dlat=1, dlon=1, wrap=False)
    assert t_wrap[2, W - 1] == pytest.approx(t_wrap[2, 1], rel=1e-6)
    assert t_flat[2, W - 1] > 300 * t_wrap[2, 1]


def test_unreachable_and_sources():
    f = np.full((10, 10), 0.01, np.float32)
    f[:, 5] = np.nan
    src = np.zeros((10, 10), bool); src[0, 0] = True
    t = gd.travel_time(f, src, 1.0, 0.1, 0.1)
    assert t[0, 0] == 0 and np.isinf(t[:, 6:]).all() and np.isinf(t[:, 5]).all()


def test_max_minutes_stops_early():
    f = np.full((50, 50), 0.01, np.float32)
    src = np.zeros((50, 50), bool); src[25, 25] = True
    t = gd.travel_time(f, src, 1.0, 0.01, 0.01, max_minutes=25.0)
    assert 1 < np.isfinite(t).sum() < 50 * 50 and t[np.isfinite(t)].max() <= 25.0


def test_benchmark():
    """Rough speed/memory figure for sizing the global run (32 M cells)."""
    rng = np.random.default_rng(1)
    H, W = 4441, 7256
    f = rng.uniform(0.001, 0.03, (H, W)).astype(np.float32)
    src = np.zeros((H, W), bool); src[rng.integers(0, H, 50), rng.integers(0, W, 50)] = True
    gd.travel_time(f[:50, :50], src[:50, :50], 12, D, D)       # compile
    t0 = time.time()
    gd.travel_time(f, src, 12.5, D, D)
    print(f"\n32 M cells: {time.time() - t0:.1f} s")

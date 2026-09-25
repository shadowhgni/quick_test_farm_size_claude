"""Multi-source least-cost travel time on a regular lon/lat grid (numba).

8-neighbour Dijkstra with an indexed binary heap. Step lengths depend on latitude:
east-west = R cos(lat) dlon, north-south = R dlat, diagonal = hypot of the two
(east-west taken at the mean latitude of the two rows). Cost of a step = mean
friction of the two cells (min/m) x step length (m). Impassable cells: friction
= inf or nan. Optional wrap-around in longitude for global grids.
"""
import math

import numpy as np
from numba import njit

R_EARTH = 6371007.2  # authalic radius (m)


def step_lengths(lat_top, dlat, dlon, nrows):
    """Per-row step lengths (m): east-west, to the row above, to the row below,
    diagonal up, diagonal down."""
    lat = lat_top - (np.arange(nrows) + 0.5) * dlat                # cell-centre latitude
    dy = R_EARTH * math.radians(dlat)
    ew = R_EARTH * np.cos(np.radians(lat)) * math.radians(dlon)
    ew_up = np.empty(nrows); ew_dn = np.empty(nrows)
    ew_up[1:] = 0.5 * (ew[1:] + ew[:-1]); ew_up[0] = ew[0]
    ew_dn[:-1] = 0.5 * (ew[:-1] + ew[1:]); ew_dn[-1] = ew[-1]
    return (ew.astype(np.float64), dy, np.hypot(ew_up, dy), np.hypot(ew_dn, dy))


@njit(cache=True)
def _sift_up(heap, pos, dist, k):
    item = heap[k]
    d = dist[item]
    while k > 0:
        parent = (k - 1) >> 1
        p = heap[parent]
        if dist[p] <= d:
            break
        heap[k] = p
        pos[p] = k
        k = parent
    heap[k] = item
    pos[item] = k


@njit(cache=True)
def _sift_down(heap, pos, dist, k, size):
    item = heap[k]
    d = dist[item]
    while True:
        c = 2 * k + 1
        if c >= size:
            break
        if c + 1 < size and dist[heap[c + 1]] < dist[heap[c]]:
            c += 1
        ch = heap[c]
        if dist[ch] >= d:
            break
        heap[k] = ch
        pos[ch] = k
        k = c
    heap[k] = item
    pos[item] = k


@njit(cache=True)
def _dijkstra(fr, sources, ew, dy, dg_up, dg_dn, wrap, max_minutes):
    H, W = fr.shape
    N = H * W
    ff = fr.ravel()
    dist = np.full(N, np.inf, dtype=np.float32)
    pos = np.full(N, -1, dtype=np.int32)          # -1: never queued, -2: settled
    cap = 1 << 20
    heap = np.empty(cap, dtype=np.int32)
    size = 0
    for s in sources:
        if not np.isfinite(ff[s]) or dist[s] == 0.0:
            continue
        dist[s] = 0.0
        if size == cap:
            cap *= 2
            nh = np.empty(cap, dtype=np.int32); nh[:size] = heap[:size]; heap = nh
        heap[size] = s
        pos[s] = size
        size += 1
        _sift_up(heap, pos, dist, size - 1)
    while size > 0:
        u = heap[0]
        size -= 1
        if size > 0:
            heap[0] = heap[size]
            pos[heap[0]] = 0
            _sift_down(heap, pos, dist, 0, size)
        pos[u] = -2
        du = dist[u]
        if du > max_minutes:
            break
        r = u // W
        c = u - r * W
        fu = ff[u]
        for k in range(8):
            if k == 0:
                rr = r; cc = c + 1; L = ew[r]
            elif k == 1:
                rr = r; cc = c - 1; L = ew[r]
            elif k == 2:
                rr = r - 1; cc = c; L = dy
            elif k == 3:
                rr = r + 1; cc = c; L = dy
            elif k == 4:
                rr = r - 1; cc = c + 1; L = dg_up[r]
            elif k == 5:
                rr = r - 1; cc = c - 1; L = dg_up[r]
            elif k == 6:
                rr = r + 1; cc = c + 1; L = dg_dn[r]
            else:
                rr = r + 1; cc = c - 1; L = dg_dn[r]
            if rr < 0 or rr >= H:
                continue
            if cc < 0 or cc >= W:
                if not wrap:
                    continue
                cc = cc % W
            v = rr * W + cc
            if pos[v] == -2:
                continue
            fv = ff[v]
            if not np.isfinite(fv):
                continue
            nd = du + 0.5 * (fu + fv) * L
            if nd < dist[v]:
                dist[v] = nd
                if pos[v] == -1:
                    if size == cap:
                        cap *= 2
                        nh = np.empty(cap, dtype=np.int32); nh[:size] = heap[:size]; heap = nh
                    heap[size] = v
                    pos[v] = size
                    size += 1
                _sift_up(heap, pos, dist, pos[v])
    return dist.reshape(H, W)


def travel_time(friction, sources_mask, lat_top, dlat, dlon, wrap=False, max_minutes=np.inf):
    """Minutes from every cell to the nearest source cell; inf where unreachable.

    friction: 2-D float32 (min/m), inf/nan = impassable. sources_mask: bool array.
    lat_top: latitude of the grid's top edge; dlat, dlon: cell size (degrees).
    """
    fr = np.ascontiguousarray(friction, dtype=np.float32)
    if fr.size >= 2**31 - 1:
        raise ValueError("grid too large for int32 indices")
    ew, dy, up, dn = step_lengths(lat_top, dlat, dlon, fr.shape[0])
    src = np.flatnonzero(sources_mask.ravel()).astype(np.int64)
    t = _dijkstra(fr, src, ew, dy, up, dn, wrap, float(max_minutes))
    if np.isfinite(max_minutes):
        t[t > max_minutes] = np.inf        # tentative values beyond the cut-off
    return t

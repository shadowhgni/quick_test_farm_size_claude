"""Offline tests for friction.py on synthetic rasters and OSM (no downloads)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import friction as fr  # noqa: E402

# 0.1 x 0.1 degree test area in southern Benin
W, S, E, N = 2.40, 6.40, 2.50, 6.50


def test_tobler_factor():
    assert fr.tobler_factor(np.array([0.0]))[0] == 1.0
    assert fr.tobler_factor(np.array([0.1]))[0] == pytest.approx(0.705, abs=1e-3)


def test_tan_slope_on_plane():
    z = np.tile(np.arange(50) * 10.0, (40, 1))   # +10 m per 100 m cell eastwards
    assert np.allclose(fr.tan_slope(z, 100), 0.1)
    z[0, 0] = np.nan
    assert np.isfinite(fr.tan_slope(z, 100)).all()


def test_friction_round_trip_and_nodata():
    s = np.array([[60.0, 5.0, 0.0]], dtype="float32")
    f = fr.to_friction(s)
    assert f[0, 0] == pytest.approx(0.001)            # 60 km/h = 1 km/min
    assert f[0, 2] == fr.NODATA
    assert np.allclose(fr.from_friction(f), s)


def test_offroad_speed_lookup():
    tab = fr.load_landcover_table()
    lc = np.array([[10, 40, 80, 0]], dtype="uint8")
    sp = fr.offroad_speed(lc, np.zeros(lc.shape), tab)
    assert sp.tolist() == [[2.5, 4.0, 0.0, 0.0]]


def test_tile_urls_benin_togo():
    b = (-0.15, 6.1, 3.85, 12.42)
    wc = fr.worldcover_urls(b, 2021)
    tiles = sorted(u.split("_v200_")[1][:7] for u in wc)
    assert tiles == ["N06E000", "N06E003", "N06W003", "N09E000", "N09E003", "N09W003",
                     "N12E000", "N12E003", "N12W003"]
    assert all("/v200/2021/" in u for u in wc)
    assert "/v100/2020/" in fr.worldcover_urls(b, 2020)[0]
    dem = fr.copdem_urls(b)
    assert len(dem) == 7 * 5
    assert any("_N06_00_W001_00_DEM.tif" in u for u in dem)


def test_parse_poly_with_hole():
    text = """test
1
   0 0
   10 0
   10 10
   0 10
END
!2
   4 4
   6 4
   6 6
   4 6
END
END
"""
    g = fr.parse_poly(text)
    assert g.area == pytest.approx(100 - 4)


# ---------------- end to end ----------------
def _tif(path, arr, dtype, nodata=None):
    res = (E - W) / arr.shape[1]
    with rasterio.open(path, "w", driver="GTiff", height=arr.shape[0], width=arr.shape[1],
                       count=1, dtype=dtype, crs=4326, nodata=nodata,
                       transform=from_origin(W, N, res, res)) as d:
        d.write(arr.astype(dtype), 1)


def _osm(path, ways):
    """ways: list of (highway, [(lon, lat), ...])"""
    nodes, xml_ways, nid = [], [], 1
    for wid, (hw, coords) in enumerate(ways, start=1):
        refs = []
        for lon, lat in coords:
            nodes.append(f'<node id="{nid}" lat="{lat}" lon="{lon}"/>')
            refs.append(f'<nd ref="{nid}"/>')
            nid += 1
        xml_ways.append(f'<way id="{wid}">{"".join(refs)}<tag k="highway" v="{hw}"/></way>')
    path.write_text('<?xml version="1.0"?><osm version="0.6">'
                    + "".join(nodes + xml_ways) + "</osm>")


@pytest.fixture
def inputs(tmp_path):
    lc = np.full((100, 100), 40, dtype="uint8")        # cropland
    lc[:, 45:55] = 80                                  # a N-S river, impassable
    _tif(tmp_path / "lc.tif", lc, "uint8", nodata=0)
    dem = np.tile(np.linspace(0, 300, 100), (100, 1))  # rising eastwards
    _tif(tmp_path / "dem.tif", dem, "float32", nodata=-32768)
    primary = ("primary", [(2.41, 6.45), (2.49, 6.45)])        # crosses the river
    track = ("track", [(2.42, 6.42), (2.42, 6.48)])           # built by t2
    _osm(tmp_path / "t1.osm", [primary])
    _osm(tmp_path / "t2.osm", [primary, track])
    (tmp_path / "area.poly").write_text(
        f"area\n1\n {W} {S}\n {E} {S}\n {E} {N}\n {W} {N}\nEND\nEND\n")
    return tmp_path


def test_main_two_dates(inputs):
    t = inputs
    out = t / "out"
    fr.main(["--osm-pbf-t1", str(t / "t1.osm"), "--osm-pbf-t2", str(t / "t2.osm"),
             "--landcover-t1", str(t / "lc.tif"), "--dem", str(t / "dem.tif"),
             "--boundary", str(t / "area.poly"), "--crs", "EPSG:32631",
             "--out-dir", str(out)])
    with rasterio.open(out / "friction_t1.tif") as a, rasterio.open(out / "friction_t2.tif") as b:
        f1, f2 = a.read(1), b.read(1)
        row = a.index(*_utm(2.46, 6.45))[0]          # the primary road row
        col_river = a.index(*_utm(2.50 - 0.05, 6.45))[1]
    v = (f1 != fr.NODATA) & (f2 != fr.NODATA)
    assert (f2[v] <= f1[v] + 1e-9).all()              # t2 never slower than t1
    assert (f2[v] < f1[v]).sum() > 0                  # the new track made cells faster
    assert (f1 == fr.NODATA).sum() > 0                # river is impassable ...
    assert f1[row, col_river] == pytest.approx(0.06 / 70)   # ... except on the bridge
    s = pd.read_csv(out / "friction_summary.csv")
    assert s.loc[s["map"] == "t2", "cells_slower_than_t1"].item() == 0
    assert (out / "speed_change_t2_minus_t1_kmh.tif").exists()


def test_base_friction_mode(inputs, tmp_path):
    t = inputs
    base = np.full((100, 100), 0.06 / 3.0, dtype="float32")    # 3 km/h everywhere
    _tif(t / "base.tif", base, "float32", nodata=fr.NODATA)
    out = t / "out_base"
    fr.main(["--osm-pbf-t1", str(t / "t1.osm"), "--osm-pbf-t2", str(t / "t2.osm"),
             "--base-friction", str(t / "base.tif"), "--out-dir", str(out)])
    with rasterio.open(out / "friction_t2.tif") as r:
        f2 = r.read(1)
        assert r.crs.to_epsg() == 4326 and r.shape == (100, 100)   # base grid kept
    assert f2.max() == pytest.approx(0.02)            # off-road = base friction
    assert f2.min() == pytest.approx(0.06 / 70)       # primary road burned in


def _utm(lon, lat):
    from pyproj import Transformer
    return Transformer.from_crs(4326, 32631, always_xy=True).transform(lon, lat)


def test_benin_togo_driver(inputs, monkeypatch):
    """run_friction_benin_togo.py end to end, remote tiles replaced by local ones."""
    import json
    import zipfile
    import run_friction_benin_togo as rfb

    t = inputs
    data = t / "data"
    data.mkdir()
    for c in rfb.COUNTRIES:            # both "countries" share the synthetic area
        (data / f"{c}-{rfb.T1}.osm").write_text((t / "t1.osm").read_text())
        (data / f"{c}-{rfb.T2}.osm").write_text((t / "t2.osm").read_text())
        (data / f"{c}.poly").write_text((t / "area.poly").read_text())
    feat = {"type": "Feature", "properties": {"WidthMeters": "9.5"},
            "geometry": {"type": "LineString", "coordinates": [[2.47, 6.41], [2.47, 6.49]]}}
    with zipfile.ZipFile(data / "Western_Africa.zip", "w") as z:
        z.writestr("Western_Africa.tsv", f"BEN\t{json.dumps(feat)}\n")

    monkeypatch.chdir(t)
    monkeypatch.setattr(rfb, "DATA", data)
    monkeypatch.setattr(rfb, "OSM_EXT", ".osm")
    monkeypatch.setattr(fr, "worldcover_urls", lambda b, y=2021: [str(t / "lc.tif")])
    monkeypatch.setattr(fr, "copdem_urls", lambda b: [str(t / "dem.tif")])
    monkeypatch.setattr(rfb, "ZOOMS", {"centre": (2.45, 6.45)})
    rfb.main()

    s = pd.read_csv(t / "results_friction_benin_togo" / "friction_summary.csv")
    assert s["map"].tolist() == ["t1", "t2", "t2_ml"]
    assert s["road_cells"].is_monotonic_increasing        # t1 < t2 < t2 + ML
    assert (s["cells_slower_than_t1"] == 0).all()
    for f in ["friction_maps.png", "speed_change.png", "zoom_centre.png"]:
        assert (t / "results_friction_benin_togo" / f).exists()

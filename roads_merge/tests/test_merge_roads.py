"""Offline tests for merge_roads.py on synthetic data (no downloads needed).

Run:  pytest roads_merge/tests -q
"""
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import pytest
import rasterio
import shapely
from shapely.geometry import LineString, mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import merge_roads as mr  # noqa: E402

UTM31 = 32631  # Benin/Togo mostly fall in UTM 31N


def _gdf(geoms, **cols):
    return gpd.GeoDataFrame(cols, geometry=list(geoms), crs=UTM31)


# ---------------- overlap / conflation ----------------
def test_overlap_fraction_matches_buffer_union():
    """Sampling method reproduces v00's exact buffer-union overlap."""
    rng = np.random.default_rng(1)
    ref = [LineString([(0, 0), (2000, 0)]), LineString([(1000, -500), (1000, 500)])]
    lines = []
    for _ in range(200):
        x0, y0 = rng.uniform(-200, 2200), rng.uniform(-100, 100)
        ang, ln = rng.uniform(0, np.pi), rng.uniform(60, 800)
        lines.append(LineString([(x0, y0), (x0 + ln * np.cos(ang), y0 + ln * np.sin(ang))]))
    got = mr.overlap_fraction(np.array(lines), np.array(ref), 20, step_m=2)
    buf = shapely.union_all([r.buffer(20) for r in ref])
    exact = np.array([l.intersection(buf).length / l.length for l in lines])
    assert np.abs(got - exact).max() < 0.02


def test_conflate_keeps_only_unmapped_roads():
    osm = _gdf([LineString([(0, 0), (1000, 0)])], highway=["primary"], speed=[70.0])
    ms = _gdf([
        LineString([(0, 5), (1000, 5)]),        # duplicate of OSM (5 m off)
        LineString([(0, 500), (1000, 500)]),    # genuinely new
        LineString([(800, 10), (800, 300)]),    # mostly new, touches OSM
        LineString([(0, 800), (30, 800)]),      # < MIN_LEN_M
    ], iso3=["BEN"] * 4)
    new = mr.conflate(ms, osm)
    assert len(new) == 2
    assert set(new["source"]) == {"microsoft"}
    assert (new["speed"] == mr.ML_SPEED).all()
    assert new["osm_overlap"].max() < 0.1


def test_flag_new_roads_ignores_resplit_ways():
    t1 = _gdf([LineString([(0, 0), (1000, 0)])], highway=["primary"])
    t2 = _gdf([LineString([(0, 1), (500, 1)]),        # same road, split + redrawn
               LineString([(500, 1), (1000, 1)]),
               LineString([(0, 400), (1000, 400)])],  # new road
              highway=["primary", "primary", "tertiary"])
    assert mr.flag_new_roads(t2, t1).tolist() == [False, False, True]


# ---------------- speeds ----------------
def test_speed_table_and_unpaved_rules():
    tab = mr.load_speed_table()
    hw = pd.Series(["primary", "primary", "tertiary", "tertiary", "track"])
    sf = pd.Series([None, "dirt", None, "asphalt", None])
    sp = mr.assign_speed(hw, sf, tab).tolist()
    assert sp == [70, 70 * 0.7, 40 * 0.7, 40, 15 * 0.7]


# ---------------- readers ----------------
def _write_ms_zip(path, rows):
    tsv = "\n".join(f"{c}\t{json.dumps(f)}" for c, f in rows) + "\n"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("Western_Africa.tsv", tsv)


def _feature(coords, width=5.0):
    # the real file stores WidthMeters as a string
    return {"type": "Feature", "properties": {"WidthMeters": str(width)},
            "geometry": mapping(LineString(coords))}


def test_read_ms_roads_filters_countries(tmp_path):
    z = tmp_path / "Western_Africa.zip"
    _write_ms_zip(z, [("BEN", _feature([(2.4, 6.4), (2.5, 6.5)])),
                      ("TGO", _feature([(1.2, 6.2), (1.3, 6.3)], 7.5)),
                      ("NGA", _feature([(3.4, 6.5), (3.5, 6.6)]))])
    ms = mr.read_ms_roads(z, ["ben", "TGO"])
    assert sorted(ms["iso3"]) == ["BEN", "TGO"]
    assert ms.loc[ms["iso3"] == "TGO", "width_m"].item() == 7.5
    with pytest.raises(ValueError):
        mr.read_ms_roads(z, ["GHA"])


OSM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="test">
  <node id="1" lat="6.40" lon="2.40"/><node id="2" lat="6.40" lon="2.45"/>
  <node id="3" lat="6.45" lon="2.40"/><node id="4" lat="6.45" lon="2.45"/>
  <node id="5" lat="6.50" lon="2.40"/><node id="6" lat="6.50" lon="2.45"/>
  <way id="10"><nd ref="1"/><nd ref="2"/><tag k="highway" v="primary"/></way>
  <way id="11"><nd ref="3"/><nd ref="4"/><tag k="highway" v="track"/>
    <tag k="surface" v="dirt"/></way>
  <way id="12"><nd ref="5"/><nd ref="6"/><tag k="highway" v="footway"/></way>
</osm>
"""


@pytest.fixture
def osm_file(tmp_path):
    p = tmp_path / "tiny.osm"
    p.write_text(OSM_XML)
    return p


def test_read_osm_roads(osm_file):
    osm = mr.read_osm_roads([str(osm_file), str(osm_file)], mr.load_speed_table())
    assert sorted(osm["highway"]) == ["primary", "track"]   # footway dropped, dups removed
    assert osm.set_index("highway").loc["track", "surface"] == "dirt"
    assert osm.set_index("highway").loc["track", "speed"] == pytest.approx(10.5)


# ---------------- raster + end to end ----------------
def test_rasterize_fastest_wins(tmp_path):
    roads = _gdf([LineString([(0, 50), (1000, 50)]), LineString([(0, 50), (1000, 50)])],
                 speed=[70.0, 15.0])
    tif = tmp_path / "s.tif"
    mr.rasterize_speed(roads, tif, res_m=100)
    with rasterio.open(tif) as r:
        assert r.read(1).max() == 70


def test_main_end_to_end(tmp_path, osm_file):
    z = tmp_path / "ms.zip"
    _write_ms_zip(z, [("BEN", _feature([(2.40, 6.4001), (2.45, 6.4001)])),   # dup of way 10
                      ("BEN", _feature([(2.40, 6.60), (2.45, 6.60)]))])     # new
    out = tmp_path / "out"
    roads = mr.main(["--osm-pbf", str(osm_file), "--osm-pbf-t1", str(osm_file),
                     "--ms-roads", str(z), "--iso3", "BEN", "--out-dir", str(out)])
    assert (roads["source"] == "microsoft").sum() == 1
    assert not roads["new_since_t1"].fillna(False).any()
    for f in ["roads_merged.gpkg", "road_length_summary.csv", "road_speed_kmh.tif"]:
        assert (out / f).exists()

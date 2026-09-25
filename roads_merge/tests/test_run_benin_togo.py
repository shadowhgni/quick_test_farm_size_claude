"""Smoke test of run_benin_togo.py on synthetic files with the expected names."""
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_benin_togo as rbt  # noqa: E402

SPOTS = {"benin": (2.5, 9.2), "togo": (1.0, 9.4)}


def _osm_xml(n_ways, lon0, lat0, id0=0):
    # OSM ids are global: give each synthetic country its own id range
    r = np.random.default_rng(1)          # same seed: t2 is a superset of t1
    nodes, ways = [], []
    for w in range(n_ways):
        x, y = lon0 + r.uniform(0, .3), lat0 + r.uniform(0, .3)
        a, b = id0 + 2 * w + 1, id0 + 2 * w + 2
        nodes += [f'<node id="{a}" lat="{y}" lon="{x}"/>',
                  f'<node id="{b}" lat="{y + r.uniform(-.02, .02)}" lon="{x + .02}"/>']
        hw = r.choice(["primary", "tertiary", "track", "unclassified"])
        ways.append(f'<way id="{id0 + w + 1}"><nd ref="{a}"/><nd ref="{b}"/>'
                    f'<tag k="highway" v="{hw}"/></way>')
    return '<?xml version="1.0"?><osm version="0.6">' + "".join(nodes + ways) + "</osm>"


def test_driver_runs(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    rng = np.random.default_rng(0)
    rows = []
    for i, (c, (x, y)) in enumerate(SPOTS.items()):
        (data / f"{c}-{rbt.T1}.osm").write_text(_osm_xml(100, x, y, i * 10**6))
        (data / f"{c}-{rbt.T2}.osm").write_text(_osm_xml(150, x, y, i * 10**6))
        for _ in range(300):
            x0, y0 = x + rng.uniform(0, .3), y + rng.uniform(0, .3)
            f = {"type": "Feature", "properties": {"WidthMeters": float(rng.uniform(3, 9))},
                 "geometry": {"type": "LineString",
                              "coordinates": [[x0, y0], [x0 + .01, y0 + .005]]}}
            rows.append(f"{rbt.COUNTRY[c]}\t{json.dumps(f)}")
    with zipfile.ZipFile(data / "Western_Africa.zip", "w") as z:
        z.writestr("Western_Africa.tsv", "\n".join(rows) + "\n")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(rbt, "OSM_EXT", ".osm")
    monkeypatch.setattr(rbt, "DATA", data)
    rbt.main()

    s = pd.read_csv(tmp_path / "results_benin_togo" / "summary_by_country.csv")
    assert set(s["iso3"]) == {"BEN", "TGO"}
    # 50 extra ways per country at t2 -> new length > 0 but < t2 total
    assert (s["osm_new_since_t1_km"] > 0).all()
    assert (s["osm_new_since_t1_km"] < s[f"osm_{rbt.T2}_km"]).all()
    assert (s["ml_kept_km"] <= s["ml_total_km"]).all()
    assert len(list((tmp_path / "results_benin_togo").glob("qa_*.png"))) == 4

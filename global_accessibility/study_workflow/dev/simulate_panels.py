"""Simulated panels with a known effect, in the layout of stage panels, to test estimate_effects.R:
    python simulate_panels.py <out folder> [effect] [seed]
E1: staggered access-gain events 2016-2022 raise conv_share by `effect` from the event year on
(no pre-trend); burst events (placebo) have no effect. E3: d_conv_share = 0.5 x d_access + noise."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def simulate(out, effect=0.02, seed=1, n=1500, years=range(2008, 2025), mix_shift=0.0):
    rng = np.random.default_rng(seed)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    ids = np.arange(1, n + 1)
    kind = rng.choice(["never", "treated", "burst"], n, p=[0.5, 0.4, 0.1])
    g = np.where(kind == "treated", rng.integers(2016, 2023, n), 0)
    gb = np.where(kind == "burst", rng.integers(2016, 2023, n), 0)
    region = rng.choice(["AAA", "BBB", "CCC", "DDD"], n)
    lat, lon = rng.uniform(-5, 5, n), rng.uniform(10, 20, n)
    unit_fe = rng.normal(0.05, 0.02, n)
    dose = np.where(g > 0, rng.uniform(0.1, 1.0, n), 0.0)
    rows = []
    for y in years:
        yfe = 0.002 * (y - 2008)
        post = (g > 0) & (y >= g)
        rows.append(pd.DataFrame({
            "id": ids, "year": y, "region": region, "lat": lat, "lon": lon, "w": 1.0, "w_cem": 1.0,
            "conv_share": unit_fe + yfe + effect * post + rng.normal(0, 0.01, n),
            "loss_share": unit_fe * 2 + yfe + rng.normal(0, 0.01, n),
            "g__roadonly_cities_11": np.where(kind == "burst", -1, g),
            "gburst__roadonly_cities_11": gb,
            "dose__roadonly_cities_11": dose,
            "band__roadonly_cities_11": np.where(kind == "treated", 1.0, np.where(kind == "never", 0.0, np.nan)),
            "g__total_cities_11": np.where(kind == "burst", -1, g)}))
    e1 = pd.concat(rows, ignore_index=True)
    e1.to_parquet(out / "e1_cells.parquet", index=False)
    d_access = rng.uniform(0, 1, n)
    e3 = pd.DataFrame({"dataset": "E1_cells", "crop": None, "id": ids, "lat": lat, "lon": lon,
                       "region": region, "w": 1.0, "epoch": "2015-2020",
                       "d_access__roadonly_cities_11": d_access,
                       "d_conv_share": 0.5 * d_access + rng.normal(0, 0.05, n)})
    e3.to_parquet(out / "e3_longdiff.parquet", index=False)
    if mix_shift:
        # admin units: access events raise maize share by mix_shift (crop switching) and log yield by `effect`
        na = 400
        ua = np.arange(1, na + 1)
        ga = np.where(rng.random(na) < 0.5, rng.integers(2010, 2018, na), 0)
        rega, lata, lona = rng.choice(["AAA", "BBB"], na), rng.uniform(-5, 5, na), rng.uniform(10, 20, na)
        e2a, e2e = [], []
        for y in range(2005, 2023):
            post = (ga > 0) & (y >= ga)
            base = dict(id=ua, year=y, region=rega, lat=lata, lon=lona, w=1.0,
                        **{"g__roadonly_cities_11": ga, "g__total_cities_11": ga})
            e2a.append(pd.DataFrame(dict(base, crop="Maize",
                                         log_yield=0.2 + effect * post + rng.normal(0, 0.02, na))))
            e2e.append(pd.DataFrame(dict(base, share_maize=0.4 + mix_shift * post + rng.normal(0, 0.01, na),
                                         shannon=1.0 + rng.normal(0, 0.01, na))))
        pd.concat(e2a, ignore_index=True).to_parquet(out / "e2a_admin.parquet", index=False)
        pd.concat(e2e, ignore_index=True).to_parquet(out / "e2e_admin.parquet", index=False)
    return out


if __name__ == "__main__":
    simulate(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 0.02,
             int(sys.argv[3]) if len(sys.argv) > 3 else 1)

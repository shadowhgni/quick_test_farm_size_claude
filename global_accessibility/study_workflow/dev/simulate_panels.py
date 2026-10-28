"""Simulated panels with a known effect, in the layout of stage panels, to test estimate_effects.R:
    python simulate_panels.py <out folder> [effect] [seed]
E1: staggered access-gain events 2016-2022 raise conv_share by `effect` from the event year on
(no pre-trend); burst events (placebo) have no effect. E3: d_conv_share = 0.5 x d_access + noise."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def simulate(out, effect=0.02, seed=1, n=1500, years=range(2008, 2025)):
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
    return out


if __name__ == "__main__":
    simulate(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 0.02,
             int(sys.argv[3]) if len(sys.argv) > 3 else 1)

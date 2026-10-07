#!/usr/bin/env python3
"""
CI check of v8 step 4 pooling: the SSA ("ALL" and per AEZ) means in ssa_summary.csv and
ssa_stage_hits.csv must equal the means computed directly over the pooled cell tables of all
countries. Exits 1 on any difference.

  python tests/check_aggregate.py --region ci_nga
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--region", required=True)
ap.add_argument("--name", default="SSA")
a = ap.parse_args()

sdir = Path("dryspell_v8") / a.region / "step03"
ok = [p.name for p in sorted(sdir.iterdir()) if p.is_dir() and p.name != a.name
      and (p / "status.json").exists() and json.loads((p / "status.json").read_text())["status"] == "ok"]
cells = pd.concat([pd.read_parquet(sdir / c / "cell_summary.parquet") for c in ok], ignore_index=True)
cells["aez"] = cells["aez"].astype(str)
ssa = pd.read_csv(sdir / a.name / "ssa_summary.csv")
ssh = pd.read_csv(sdir / a.name / "ssa_stage_hits.csv")
keys = ["crop", "cycle", "sow"]
bad = 0

agg = dict(n=("impossible", "size"), imp=("impossible", "mean"), p=("p_hit_window", "mean"))
direct = pd.concat([cells.groupby(keys + ["aez"]).agg(**agg).reset_index(),
                    cells.assign(aez="ALL").groupby(keys + ["aez"]).agg(**agg).reset_index()], ignore_index=True)
m = ssa.merge(direct, on=keys + ["aez"], how="outer", indicator=True)
bad += int((m._merge != "both").sum())
both = m[m._merge == "both"]
bad += int((both.n_cells != both.n).sum())
bad += int((~np.isclose(both.pct_cells_impossible, 100 * both.imp, equal_nan=True)).sum())
bad += int((~np.isclose(both.p_hit_window_mean, both.p, equal_nan=True, atol=1e-6)).sum())

# stage hits: pooled mean over possible cells, per stage
n_stage = 0
for crop in cells.crop.unique():
    w = pd.concat([pd.read_parquet(sdir / c / f"cell_stage_hits_{crop}.parquet") for c in ok], ignore_index=True)
    w["aez"] = w["aez"].astype(str)
    w = w[w.impossible == 0]
    pc = [c for c in w.columns if c.startswith("p_hit_")]
    for grp in (w, w.assign(aez="ALL")):
        d = grp.groupby(keys + ["aez"])[pc].mean().reset_index().melt(id_vars=keys + ["aez"], var_name="stage",
                                                                       value_name="p_direct")
        d["stage"] = d["stage"].str.replace("p_hit_", "", regex=False)
        mm = ssh[ssh.crop == crop].merge(d, on=keys + ["aez", "stage"], how="inner")
        n_stage += len(mm)
        bad += int((~np.isclose(mm.p, mm.p_direct, equal_nan=True, atol=1e-6)).sum())
print(f"countries {ok}: summary rows {len(both)}, stage rows {n_stage}, differences {bad}")
sys.exit(1 if bad or not n_stage else 0)

#!/usr/bin/env python3
"""
Independent check of v9 step 4: recompute P(feasible), the impossible flag, P(longest spell
hits the vulnerable window) and P(longest spell hits each stage) for randomly sampled
cells with plain loops over the step 2 spells and seasons, and compare with the
step 3 outputs. Exits 1 on any mismatch.

  python tests/check_sowing.py --region ci_nga --iso3 NGA --crop sorghum --cells 8
"""
import argparse
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("s4", HERE / "v9_04_sowing_risk.py")
s4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", required=True)
    ap.add_argument("--iso3", default="NGA")
    ap.add_argument("--crop", default="sorghum")
    ap.add_argument("--cells", type=int, default=8)
    ap.add_argument("--grace", type=int, default=s4.C.DEMISE_GRACE)
    ap.add_argument("--day0", type=int, default=s4.C.DAY0)
    a = ap.parse_args()

    root = s4.C.region_dir(a.region)
    out = root / "step04" / a.iso3
    cells = pd.read_parquet(out / "cell_summary.parquet")
    cells = cells[cells.crop == a.crop]
    ds = xr.open_dataset(out / f"cells_{a.crop}.nc")
    has = np.load(root / "step03" / "day_has_data.npy")
    minc = s4.C.MIN_SPELL_CROP[a.crop]
    cycles = sorted(cells.cycle.unique())
    sows = sorted(cells.sow.unique())
    pick = cells[["row", "col"]].drop_duplicates().sample(min(a.cells, len(cells)), random_state=7).values
    rows = sorted({int(r) for r, _ in pick})
    flt = [("row", "in", rows)]
    sp = pd.read_parquet(root / "step03" / "spells", filters=flt)
    se = pd.read_parquet(root / "step03" / "seasons", filters=flt)
    O = s4.C.ORIGIN
    n = bad = 0
    for row, col in pick:
        s = se[(se.row == row) & (se.col == col) & se.valid]
        spc = sp[(sp.row == row) & (sp.col == col) & (sp.length >= minc)]
        for L in cycles:
            stages, (w0, w1) = s4.stage_das(a.crop, L)
            for sw in sows:
                feas = hits = 0
                hs = np.zeros(len(stages))
                for _, z in s.iterrows():
                    on = int((np.datetime64(z.onset_date, "D") - O).astype(int))
                    de = int((np.datetime64(z.demise_date, "D") - O).astype(int))
                    S = on + sw                       # sow column already includes day0
                    M = S + L - 1
                    if M > de + a.grace or M >= len(has) or S < 0 or not has[S:M + 1].all():
                        continue
                    feas += 1
                    best = None
                    for q in spc.itertuples():
                        cs, ce = max(q.start, S), min(q.end, M)
                        ln = ce - cs + 1
                        if ln >= minc and (best is None or ln > best[0] or (ln == best[0] and cs < best[1])):
                            best = (ln, cs, ce)
                    if best:
                        b0, b1 = best[1] - S, best[2] - S
                        hits += (min(b1, w1) - max(b0, w0) + 1) >= 1
                        for j, st in enumerate(stages):
                            hs[j] += (min(b1, st[3]) - max(b0, st[2]) + 1) >= 1
                r = cells[(cells.row == row) & (cells.col == col) & (cells.cycle == L) & (cells.sow == sw)].iloc[0]
                pf = feas / len(s) if len(s) else np.nan
                imp = bool(pf < s4.C.FEASIBLE_MIN_FRAC)
                ok = abs(r.p_feasible - pf) < 1e-6 and bool(r.impossible) == imp
                if not imp and feas >= s4.C.MIN_FEASIBLE_SEASONS:
                    ok &= abs(r.p_hit_window - hits / feas) < 1e-6
                    ph = ds.p_hit_stage.sel(cycle=L, sow=sw).sel(lat=r.lat, lon=r.lon, method="nearest").values
                    ok &= np.allclose(ph, hs / feas, atol=1e-6)
                n += 1
                if not ok:
                    bad += 1
                    print(f"MISMATCH row {row} col {col} cycle {L} sow {sw}: p_feasible {r.p_feasible} vs {pf}, "
                          f"p_hit_window {r.p_hit_window} vs {hits}/{feas}")
    print(f"{a.crop}: checked {n} cell x cycle x sowing combinations, mismatches: {bad}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

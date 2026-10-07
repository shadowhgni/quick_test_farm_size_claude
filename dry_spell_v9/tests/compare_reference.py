#!/usr/bin/env python3
"""
Parity check between two runs of the same region (GitHub CI vs HPC).

A "fingerprint" is a few small CSV files summarising a run:
  grid.csv       cell counts per regime and reason; mean onset/demise/length over valid cells;
                 number of spells and valid seasons
  countries.csv  national values per country x crop x cycle x sow (cells, % impossible,
                 P(hit window), most hit stage and its probability)
  pooled.csv     the pooled (SSA / all countries) values, zone == ALL

  # CI: write the reference into the repository
  python tests/compare_reference.py --region ci_nga --write reference/ci_nga
  # HPC: after  python run_all.py --region ci_nga --countries NGA BEN NER CMR TCD
  python tests/compare_reference.py --region ci_nga            # compares with reference/ci_nga

Numbers must agree to 1e-6 (relative) - differences beyond that mean different input data
(e.g. a CHIRPS day that failed to download) or a different code version.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import v9_common as C


def fingerprint(region, name="SSA"):
    rdir = C.region_dir(region)
    gm = xr.open_dataset(rdir / "step03" / "grid_meta.nc")
    meta = C.read_json(rdir / "step03" / "meta.json")
    ok = gm.reason.values == C.REASON_OK
    g = [{"key": f"regime_{C.REGIME_LABELS[k]}", "value": int((gm.regime.values == k).sum())} for k in C.REGIME_LABELS]
    g += [{"key": f"reason_{C.REASON_LABELS[k]}", "value": int((gm.reason.values == k).sum())} for k in C.REASON_LABELS]
    g += [{"key": f"rain_regime_{C.REGIME_LABELS[k]}", "value": int((gm.rain_regime.values == k).sum())}
          for k in C.REGIME_LABELS]
    for v in ("onset_doy_median", "demise_doy_median", "season_len_median", "mean_annual_mm", "n_valid_seasons",
              "demise_shift_median", "false_start_share", "false_demise_share"):
        g.append({"key": f"mean_{v}", "value": float(np.nanmean(gm[v].values[ok]))})
    g += [{"key": "n_spells", "value": meta["n_spells"]}, {"key": "n_valid_seasons", "value": meta["n_valid_seasons"]},
          {"key": "last_day_with_data", "value": meta["last_day_with_data"]}]
    out = {"grid": pd.DataFrame(g)}
    s = rdir / "step04" / name
    cs = pd.read_csv(s / "country_summary.csv")
    out["countries"] = cs[["iso3", "crop", "cycle", "sow", "n_cells", "pct_cells_impossible", "p_hit_window_mean",
                           "most_hit_stage", "most_hit_p"]].sort_values(["iso3", "crop", "cycle", "sow"])
    ps = pd.read_csv(s / "ssa_summary.csv")
    out["pooled"] = ps[ps.zone == "ALL"][["crop", "cycle", "sow", "n_cells", "pct_cells_impossible",
                                         "p_hit_window_mean", "most_hit_stage", "most_hit_p"]] \
        .sort_values(["crop", "cycle", "sow"])
    s6 = rdir / "step06" / region / "summary_by_zone.csv"
    if s6.exists():
        z = pd.read_csv(s6)
        out["spells"] = z[z.zone == "ALL"][["metric", "n_seasons", "n_defined", "mean", "p25", "median", "p75"]] \
            .sort_values("metric")
    return out


def compare(a, b, tol=1e-6):
    """-> list of differences between two DataFrames with the same layout."""
    diffs = []
    if list(a.columns) != list(b.columns) or len(a) != len(b):
        return [f"layout differs: {a.shape} vs {b.shape}"]
    a, b = a.reset_index(drop=True), b.reset_index(drop=True)
    for col in a.columns:
        x, y = a[col], b[col]
        xn, yn = pd.to_numeric(x, errors="coerce"), pd.to_numeric(y, errors="coerce")
        if xn.notna().any() and xn.isna().eq(x.isna()).all():
            same = np.isclose(xn, yn, rtol=tol, atol=tol, equal_nan=True)
        else:
            same = (x.astype(object).where(x.notna(), "").astype(str)
                    == y.astype(object).where(y.notna(), "").astype(str)).values
        for i in np.nonzero(~same)[0][:5]:
            diffs.append(f"{col} row {i}: {x[i]} vs {y[i]}")
    return diffs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="ci_nga")
    ap.add_argument("--name", default="SSA")
    ap.add_argument("--write", default=None, help="write the fingerprint to this folder")
    ap.add_argument("--reference", default=None, help="default: <script folder>/../reference/<region>")
    a = ap.parse_args()
    fp = fingerprint(a.region, a.name)
    if a.write:
        d = Path(a.write)
        d.mkdir(parents=True, exist_ok=True)
        for k, v in fp.items():
            v.to_csv(d / f"{k}.csv", index=False)
        print(f"fingerprint written to {d}")
        return
    ref = Path(a.reference) if a.reference else HERE / "reference" / a.region
    bad = 0
    for k, v in fp.items():
        if not (ref / f"{k}.csv").exists():
            print(f"{k:<10} not in the reference (older version) - skipped")
            continue
        r = pd.read_csv(ref / f"{k}.csv")
        v = pd.read_csv(pd.io.common.StringIO(v.to_csv(index=False)))      # same dtypes as the reference
        d = compare(v, r)
        bad += len(d)
        print(f"{k:<10} {'identical' if not d else f'{len(d)} differences'}")
        for line in d[:10]:
            print("   ", line)
    print("PARITY OK - same results as the reference" if not bad else "PARITY FAILED")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

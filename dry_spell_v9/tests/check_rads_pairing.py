#!/usr/bin/env python3
"""
Check the alignment of RADS seasons across yearly files: the same seasons written in two layouts
  A  file Y = onset of the season starting in Y+1 and demise of the season ending in Y
     (demise BEFORE onset inside a file, like the HPC files), and
  B  file Y = onset and demise of the season starting in Y (onset BEFORE demise inside a file)
must give identical seasons after v9_rads.load_rads (every onset paired with the next demise).
Exits 1 on any difference.

  python tests/make_rads_from_chirps.py dryspell_v9_data/chirps/ci_nga ../chirps_africa --hpc_layout \\
         --also_same ../chirps_africa_same
  python tests/check_rads_pairing.py --region ci_nga --a "../chirps_africa/africa_RainyAndDrySeason.pentad.CHIRPS.{year}.nc" \\
         --b "../chirps_africa_same/africa_RainyAndDrySeason.pentad.CHIRPS.{year}.nc"
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import v9_common as C   # noqa: E402
import v9_rads as R     # noqa: E402


def synthetic_cross_year():
    """pair_seasons on hand-made files: southern-hemisphere seasons (onset November Y, demise March Y+1)
    stored (a) in the file of their own year each, (b) both in the onset-year file, and a northern
    season (June - October). Every season must come out named by its onset year with its own dates."""
    d = lambda s: int(C.day_index(np.array([s], dtype="datetime64[D]"))[0])   # noqa: E731
    years = np.array([2001, 2002, 2003])
    K = len(years)
    on_f = np.full((K, 3), R.SENT, np.int32)
    de_f = np.full((K, 3), R.SENT, np.int32)
    want_on = np.full((K, 3), R.SENT, np.int32)
    want_de = np.full((K, 3), R.SENT, np.int32)
    for k, y in enumerate(years):
        # cell 0: onset in file Y, its demise (March Y+1) in file Y+1 -> file Y holds demise (Y) < onset (Y)
        on_f[k, 0] = d(f"{y}-11-05")
        if k + 1 < K:
            de_f[k + 1, 0] = d(f"{y + 1}-03-20")
        # cell 1: both dates of the season in the onset-year file (demise next year)
        on_f[k, 1], de_f[k, 1] = d(f"{y}-11-05"), d(f"{y + 1}-03-20")
        # cell 2: season inside the calendar year
        on_f[k, 2], de_f[k, 2] = d(f"{y}-06-10"), d(f"{y}-10-15")
        want_on[k] = [d(f"{y}-11-05"), d(f"{y}-11-05"), d(f"{y}-06-10")]
        want_de[k] = [d(f"{y + 1}-03-20"), d(f"{y + 1}-03-20"), d(f"{y}-10-15")]
    want_on[K - 1, 0] = want_de[K - 1, 0] = R.SENT       # last demise of cell 0 is in a file that does not exist
    on, de, used = R.pair_seasons(on_f, de_f, years)
    bad = int((on != want_on).sum() + (de != want_de).sum())
    print(f"synthetic cross-year seasons: {int((on != R.SENT).sum())} paired, pairing {used}; differences {bad}")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="ci_nga")
    ap.add_argument("--a", required=True, help="RADS_FILE_PATTERN of layout A")
    ap.add_argument("--b", required=True, help="RADS_FILE_PATTERN of layout B")
    a = ap.parse_args()
    C.setup_logging()
    bad_syn = synthetic_cross_year()
    cm = C.read_json(C.data_dir("chirps", a.region, "meta.json"))
    lon, lat = np.array(cm["lon"]), np.array(cm["lat"])
    out = {}
    for k, pat in (("A", a.a), ("B", a.b)):
        C.RADS_FILE_PATTERN = pat
        years, on, de, info, diag = R.load_rads(lon, lat, 4)
        out[k] = (on, de)
        print(f"layout {k}: within-file onset before demise {info.onset_before_demise.median():.0%}, "
              f"demise before onset {info.demise_before_onset.median():.0%}; seasons "
              f"{int(((on != R.SENT) & (de != R.SENT)).sum()):,}")
    # the first season year is left out: in layout A its onsets sit in the file of the year before,
    # which does not exist (v9_rads warns about it)
    (oa, da), (ob, db) = ((x[0][1:], x[1][1:]) for x in (out["A"], out["B"]))
    n = int(((oa != R.SENT) & (da != R.SENT)).sum())
    bad = int((oa != ob).sum() + (da != db).sum())
    print(f"seasons {years[1]}-{years[-1]} in A {n:,}; cells x years where A and B differ: {bad}")
    if n == 0:
        print("no season at all - nothing was tested")
    sys.exit(1 if bad or bad_syn or n == 0 else 0)


if __name__ == "__main__":
    main()

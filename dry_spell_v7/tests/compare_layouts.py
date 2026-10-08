#!/usr/bin/env python3
"""
CI check: step 2 must give the same valid seasons whether a season's onset and demise sit in
the same RADS file or in neighbouring files (HPC layout). Every valid season of run A from the
second season year on must exist in run B with identical onset and demise dates, and vice versa.

  python compare_layouts.py RUN_A/dryspell_v7/nga/step2/seasons RUN_B/dryspell_v7/nga/step2/seasons
"""
import sys

import pandas as pd

cols = ["row", "col", "year", "onset_date", "demise_date"]
a = pd.read_parquet(sys.argv[1], columns=cols + ["valid"])
b = pd.read_parquet(sys.argv[2], columns=cols + ["valid"])
y0 = a.year.min() + 1                     # first season year has no onset in the HPC layout
a = a[a.valid & (a.year >= y0)][cols]
b = b[b.valid & (b.year >= y0)][cols]
m = a.merge(b, on=["row", "col", "year"], how="outer", suffixes=("_a", "_b"), indicator=True)
only_a = (m._merge == "left_only").sum()
only_b = (m._merge == "right_only").sum()
both = m[m._merge == "both"]
diff = ((both.onset_date_a != both.onset_date_b) | (both.demise_date_a != both.demise_date_b)).sum()
print(f"valid seasons >= {y0}: A {len(a):,}, B {len(b):,}; only in A {only_a:,}, only in B {only_b:,}, "
      f"different dates {diff:,}")
sys.exit(1 if (only_a or only_b or diff) else 0)

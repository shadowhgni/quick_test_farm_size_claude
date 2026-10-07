#!/usr/bin/env python3
"""
Rewrite RADS files from the "same file" layout (file Y holds onset and demise of the season
of Y) into the layout found in the HPC africa_RainyAndDrySeason.pentad.CHIRPS files:
file Y holds the onset of the season of Y+1 and the demise of the season of Y, and a missing
onset is written as 1970-01-01. Used by CI to check that step 2 re-pairs them correctly.

  python rads_to_hpc_layout.py chirps_africa chirps_africa_hpc
"""
import sys
from pathlib import Path

import numpy as np
import xarray as xr

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
dst.mkdir(parents=True, exist_ok=True)
files = sorted(src.glob("africa_RainyAndDry*.nc"))
ds = {int(f.name.split(".")[-2]): xr.open_dataset(f).load() for f in files}
for y, d in sorted(ds.items()):
    out = d.copy()
    nxt = ds.get(y + 1)
    on = nxt["onset_date"].values if nxt is not None else np.full(d["onset_date"].shape, np.datetime64("NaT"), "datetime64[ns]")
    on = np.where(np.isnat(on), np.datetime64("1970-01-01", "ns"), on)    # placeholder as in the HPC files
    out["onset_date"] = (d["onset_date"].dims, on)
    out.to_netcdf(dst / f"africa_RainyAndDrySeason.pentad.CHIRPS.{y}.nc")
print(f"rewrote {len(ds)} files into {dst}")

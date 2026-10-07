#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_all.py - run the whole v7 dry-spell workflow for every Sub-Saharan African country
======================================================================================

  step 1   CHIRPS -> grid -> all dry spells                (once, whole region)
  step 2   RADS seasons x dry spells                        (once, whole region)
  step 3   k-means zoning                                   (optional, --steps 3)
  step 4   sowing date x crop x cycle, ONE RUN PER COUNTRY  -> dryspell_v7/<region>/step4/<ISO3>/
  step 5   aggregate all countries                          -> dryspell_v7/<region>/step4/SSA/

Run it from the folder that holds chirps_data_cache/ (as for the single scripts):

  nohup python run_all.py --region ssa --workers 40 --aez Spatial_data_repository/003_afr-aez_09.zip > run_all.out 2>&1 &
  python run_all.py --region ssa --resume                       # continue after a crash / time-out
  python run_all.py --region ssa --steps 4 5 --countries NGA GHA BFA --resume
  python run_all.py --region ssa --dry_run                      # print the plan, run nothing

* --resume skips work already done: step 1 if step1_meta.json exists, step 2 if
  step2/metrics.nc exists, a country if its step4/<ISO3>/status.json says ok or skipped.
  Without --resume everything is recomputed.
* A failing country is logged and the run continues; steps 1-2 failing stops the run.
* Several countries can run at once (--country_jobs N); --workers is shared between them.
* Extra step 4 options pass through: --step4_args "--grace 0 --day0 1".
* Everything is logged in dryspell_v7/<region>/run_all.log and run_all_status.csv.
"""

import argparse
import logging
import shlex
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dryspell_v7_common as C

SCRIPTS = {
    1: HERE / "2026-09-26.step1_dry_spell_extract_v07.py",
    2: HERE / "2026-09-26.step2_dry_spell_seasons_v07.py",
    3: HERE / "2026-09-26.step3_bbox_zoning_v07.py",
    4: HERE / "2026-10-06.step4_sowing_date_stage_risk_v07.py",
    5: HERE / "2026-10-07.step5_ssa_aggregate_v07.py",
}
SKIP_EXIT = 3      # step 4: nothing to analyse in this country

# Sub-Saharan Africa (UN M49 "Sub-Saharan Africa"), ISO 3166-1 alpha-3. SOL = Somaliland, which
# Natural Earth draws as a separate polygon (ADM0_A3 SOL); without it northern Somalia is missing.
SSA_ISO3 = [
    "AGO", "BDI", "BEN", "BFA", "BWA", "CAF", "CIV", "CMR", "COD", "COG", "COM", "CPV", "DJI", "ERI",
    "ETH", "GAB", "GHA", "GIN", "GMB", "GNB", "GNQ", "KEN", "LBR", "LSO", "MDG", "MLI", "MOZ", "MRT",
    "MUS", "MWI", "NAM", "NER", "NGA", "RWA", "SDN", "SEN", "SLE", "SOM", "SOL", "SSD", "STP", "SWZ",
    "SYC", "TCD", "TGO", "TZA", "UGA", "ZAF", "ZMB", "ZWE",
]

logger = logging.getLogger("run_all")


def run(cmd, log_file):
    """Run one step; stdout+stderr go to log_file. Returns (exit code, minutes)."""
    t0 = time.time()
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "w") as f:
        f.write("$ " + " ".join(shlex.quote(str(c)) for c in cmd) + "\n")
        f.flush()
        rc = subprocess.call([str(c) for c in cmd], stdout=f, stderr=subprocess.STDOUT)
    return rc, round((time.time() - t0) / 60, 2)


def tail(path, n=15):
    try:
        return "".join(open(path).readlines()[-n:])
    except OSError:
        return ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", default="ssa", help=f"one of {list(C.REGIONS)} or a name with --bbox")
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("LON_MIN", "LAT_MIN", "LON_MAX", "LAT_MAX"))
    ap.add_argument("--steps", nargs="+", type=int, default=[1, 2, 4, 5], choices=[1, 2, 3, 4, 5])
    ap.add_argument("--countries", nargs="+", default=None, help="ISO3 codes (default: all of SSA in the region)")
    ap.add_argument("--workers", type=int, default=32, help="CPU workers (shared between --country_jobs)")
    ap.add_argument("--country_jobs", type=int, default=1, help="countries run at the same time in step 4")
    ap.add_argument("--aez", default=None, help="AEZ raster/zip/vector for step 4 (e.g. 003_afr-aez_09.zip)")
    ap.add_argument("--aez_field", default=None, help="attribute name for a vector --aez")
    ap.add_argument("--step4_args", default="", help='extra step 4 options, e.g. "--grace 0 --day0 1"')
    ap.add_argument("--name", default="SSA", help="step 5 output folder (step4/<name>)")
    ap.add_argument("--resume", action="store_true", help="skip work that is already done")
    ap.add_argument("--dry_run", action="store_true", help="print the plan and exit")
    a = ap.parse_args()

    name, bbox = C.parse_region(a.region, a.bbox)
    rdir = C.region_dir(name)
    logs = rdir / "run_all_logs"
    rdir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s - %(message)s", datefmt="%H:%M:%S",
                        handlers=[logging.StreamHandler(), logging.FileHandler(rdir / "run_all.log", mode="a")],
                        force=True)
    py = sys.executable
    reg = ["--region", name] + (["--bbox", *map(str, a.bbox)] if a.bbox else [])
    status = []
    t_all = time.time()
    logger.info("=" * 70)
    logger.info(f"run_all  region={name} bbox={bbox} steps={a.steps} workers={a.workers} "
                f"country_jobs={a.country_jobs} resume={a.resume}")
    logger.info("=" * 70)

    def record(step, iso3, rc, minutes, state, note=""):
        status.append({"step": step, "iso3": iso3, "exit_code": rc, "status": state, "minutes": minutes,
                       "note": note})
        import pandas as pd
        pd.DataFrame(status).to_csv(rdir / "run_all_status.csv", index=False)

    # ---------------------------------------------------------------- steps 1-3
    for step, done_file, extra in (
            (1, rdir / "step1" / "step1_meta.json", ["--workers", a.workers]),
            (2, rdir / "step2" / "metrics.nc", ["--workers", a.workers]),
            (3, None, (["--bbox", *map(str, a.bbox)] if a.bbox else []))):
        if step not in a.steps:
            continue
        if a.resume and done_file is not None and done_file.exists():
            logger.info(f"step {step}: already done ({done_file}) - skipped (--resume)")
            record(step, "", 0, 0, "resumed")
            continue
        args = (reg if step != 3 else ["--region", name]) + [str(x) for x in extra]
        cmd = [py, SCRIPTS[step], *args]
        logger.info(f"step {step}: {' '.join(map(str, cmd[1:]))}")
        if a.dry_run:
            continue
        rc, mins = run(cmd, logs / f"step{step}.log")
        record(step, "", rc, mins, "ok" if rc == 0 else "failed")
        if rc != 0:
            logger.error(f"step {step} FAILED (exit {rc}) after {mins} min - last lines of {logs / f'step{step}.log'}:\n"
                         + tail(logs / f"step{step}.log"))
            if step in (1, 2):
                sys.exit(f"stopping: step {step} failed")
        else:
            logger.info(f"step {step}: done in {mins} min")

    # ---------------------------------------------------------------- step 4
    if 4 in a.steps:
        countries = [c.upper() for c in (a.countries or SSA_ISO3)]
        bnd = C.load_boundaries(bbox)
        present = set(bnd["iso_a3"]) if bnd is not None else set(countries)
        todo, absent = [c for c in countries if c in present], [c for c in countries if c not in present]
        for c in absent:
            logger.info(f"step 4 {c}: no polygon inside the region bbox - not run")
            record(4, c, None, 0, "not_in_region")
        aez_arg = []
        if a.aez:
            aez = Path(a.aez)
            if aez.suffix.lower() in (".zip", ".asc"):
                # parse the ASCII grid once (the HarvestChoice file is damaged and large), then every
                # country reads its own window of the GeoTIFF
                tif = rdir / "aez" / (aez.stem + ".tif")
                if not tif.exists() and not a.dry_run:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("step4", SCRIPTS[4])
                    s4 = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(s4)
                    logger.info(f"AEZ: converting {aez} -> {tif} (once)")
                    s4.aez_to_geotiff(aez, tif)
                aez = tif
            aez_arg = ["--aez", str(aez)] + (["--aez_field", a.aez_field] if a.aez_field else [])
        w = max(1, a.workers // max(1, a.country_jobs))
        extra = shlex.split(a.step4_args)

        def one(c):
            st = rdir / "step4" / c / "status.json"
            if a.resume and st.exists():
                s = C.read_json(st).get("status")
                if s in ("ok", "skipped"):
                    return c, 0, 0, f"resumed ({s})", ""
            cmd = [py, SCRIPTS[4], *reg[:2], "--iso3", c, "--workers", w, *aez_arg, *extra]
            if a.dry_run:
                return c, 0, 0, "planned", " ".join(map(str, cmd[1:]))
            rc, mins = run(cmd, logs / f"step4_{c}.log")
            state = {0: "ok", SKIP_EXIT: "skipped"}.get(rc, "failed")
            note = C.read_json(st).get("reason", "") if (rc == SKIP_EXIT and st.exists()) else ""
            return c, rc, mins, state, note

        logger.info(f"step 4: {len(todo)} countries, {a.country_jobs} at a time, {w} workers each")
        n_ok = n_skip = n_fail = 0
        with ThreadPoolExecutor(max_workers=max(1, a.country_jobs)) as pool:
            futs = [pool.submit(one, c) for c in todo]
            for i, f in enumerate(as_completed(futs), 1):
                c, rc, mins, state, note = f.result()
                record(4, c, rc, mins, state, note)
                n_ok += state == "ok" or state.startswith("resumed (ok")
                n_skip += state == "skipped" or state.startswith("resumed (skipped")
                n_fail += state == "failed"
                msg = f"step 4 [{i}/{len(todo)}] {c}: {state}" + (f" in {mins} min" if mins else "") + \
                      (f" - {note}" if note else "")
                if state == "failed":
                    logger.error(msg + f"\n{tail(logs / f'step4_{c}.log')}")
                else:
                    logger.info(msg)
        logger.info(f"step 4: ok {n_ok}, skipped {n_skip}, failed {n_fail}, not in region {len(absent)}")

    # ---------------------------------------------------------------- step 5
    if 5 in a.steps:
        cmd = [py, SCRIPTS[5], "--region", name, "--name", a.name]
        if a.countries:
            cmd += ["--countries", *[c.upper() for c in a.countries]]
        logger.info(f"step 5: {' '.join(map(str, cmd[1:]))}")
        if not a.dry_run:
            rc, mins = run(cmd, logs / "step5.log")
            record(5, "", rc, mins, "ok" if rc == 0 else "failed")
            if rc != 0:
                logger.error(f"step 5 FAILED (exit {rc}):\n{tail(logs / 'step5.log')}")
            else:
                logger.info(f"step 5: done in {mins} min -> {rdir / 'step4' / a.name}")

    logger.info(f"run_all finished in {(time.time() - t_all) / 60:.1f} min - status: {rdir / 'run_all_status.csv'}")
    if any(s["status"] == "failed" for s in status):
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_all.py - the whole v8 dry-spell workflow, from scratch, for every SSA country
=================================================================================

  step 1  v8_01_download.py        CHIRPS v2.0 daily for the region, boundaries, AEZ (resumable)
  step 2  v8_02_spells_seasons.py  dry spells, rainfall regime, major-season onset/demise (once)
  step 3  v8_03_sowing_risk.py     ONE RUN PER COUNTRY -> dryspell_v8/<region>/step03/<ISO3>/
  step 4  v8_04_aggregate.py       all countries        -> dryspell_v8/<region>/step03/SSA/

Run it from any working folder; inputs go to ./dryspell_v8_data, results to ./dryspell_v8.

  nohup python run_all.py --region ssa --workers 40 --country_jobs 4 > run_all_ssa.out 2>&1 &
  python run_all.py --region ssa --resume                  # continue after a crash / time-out
  python run_all.py --region ssa --dry_run                 # show the plan
  python run_all.py --region ci_nga --workers 8            # the GitHub CI box (parity check:
  python tests/compare_reference.py --region ci_nga        #  same numbers as the CI reference)

* Step 1 always resumes (only missing days are downloaded).
* --resume also skips step 2 when its outputs are newer than the CHIRPS cache, and every
  country whose step03/<ISO3>/status.json says ok or skipped.
* A failing country is logged and the run continues; steps 1-2 failing stops the run.
* --country_jobs N runs N countries at once; --workers is shared between them.
* Extra step 3 options pass through: --step3_args "--grace 0 --day0 1".
* Log: dryspell_v8/<region>/run_all.log, run_all_status.csv, run_all_logs/.
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
import v8_common as C

SCRIPTS = {1: HERE / "v8_01_download.py", 2: HERE / "v8_02_spells_seasons.py",
           3: HERE / "v8_03_sowing_risk.py", 4: HERE / "v8_04_aggregate.py"}
SKIP_EXIT = 3      # step 3: nothing to analyse in this country

# Sub-Saharan Africa (UN M49), ISO 3166-1 alpha-3. SOL = Somaliland, drawn by Natural Earth as a
# separate polygon (ADM0_A3 SOL); without it northern Somalia would be missing.
SSA_ISO3 = [
    "AGO", "BDI", "BEN", "BFA", "BWA", "CAF", "CIV", "CMR", "COD", "COG", "COM", "CPV", "DJI", "ERI",
    "ETH", "GAB", "GHA", "GIN", "GMB", "GNB", "GNQ", "KEN", "LBR", "LSO", "MDG", "MLI", "MOZ", "MRT",
    "MUS", "MWI", "NAM", "NER", "NGA", "RWA", "SDN", "SEN", "SLE", "SOM", "SOL", "SSD", "STP", "SWZ",
    "SYC", "TCD", "TGO", "TZA", "UGA", "ZAF", "ZMB", "ZWE",
]

logger = logging.getLogger("run_all")


def run(cmd, log_file):
    """Run one step; stdout+stderr -> log_file. Returns (exit code, minutes)."""
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
    ap.add_argument("--region", default="ssa", help=f"one of {list(C.REGIONS)} or a new name with --bbox")
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("LON_MIN", "LAT_MIN", "LON_MAX", "LAT_MAX"))
    ap.add_argument("--steps", nargs="+", type=int, default=[1, 2, 3, 4], choices=[1, 2, 3, 4])
    ap.add_argument("--countries", nargs="+", default=None, help="ISO3 codes (default: all SSA countries in the region)")
    ap.add_argument("--workers", type=int, default=16, help="CPU workers (shared between --country_jobs)")
    ap.add_argument("--threads", type=int, default=32, help="parallel downloads in step 1")
    ap.add_argument("--country_jobs", type=int, default=1, help="countries run at the same time in step 3")
    ap.add_argument("--step3_args", default="", help='extra step 3 options, e.g. "--grace 0 --day0 1"')
    ap.add_argument("--name", default="SSA", help="step 4 output folder (step03/<name>)")
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
    logger.info(f"run_all v8  region={name} bbox={bbox} steps={a.steps} workers={a.workers} "
                f"country_jobs={a.country_jobs} resume={a.resume}")
    logger.info("=" * 70)

    def record(step, iso3, rc, minutes, state, note=""):
        import pandas as pd
        status.append({"step": step, "iso3": iso3, "exit_code": rc, "status": state, "minutes": minutes, "note": note})
        pd.DataFrame(status).to_csv(rdir / "run_all_status.csv", index=False)

    def stop_on_failure(step, rc, mins, log):
        if rc != 0:
            logger.error(f"step {step} FAILED (exit {rc}) after {mins} min - last lines of {log}:\n{tail(log)}")
            sys.exit(f"stopping: step {step} failed")
        logger.info(f"step {step}: done in {mins} min")

    # ---------------------------------------------------------------- step 1
    if 1 in a.steps:
        cmd = [py, SCRIPTS[1], *reg, "--threads", a.threads]
        logger.info(f"step 1: {' '.join(map(str, cmd[1:]))}")
        if not a.dry_run:
            rc, mins = run(cmd, logs / "step1.log")
            record(1, "", rc, mins, "ok" if rc == 0 else "failed")
            stop_on_failure(1, rc, mins, logs / "step1.log")
            meta = C.read_json(C.data_dir("chirps", name, "meta.json"))
            if meta.get("failed_days"):
                logger.warning(f"step 1: {len(meta['failed_days'])} days could not be downloaded (they count as "
                               f"missing): {meta['failed_days'][:10]} - rerun to retry them")

    # ---------------------------------------------------------------- step 2
    if 2 in a.steps:
        done_f, cache_f = rdir / "step02" / "meta.json", C.data_dir("chirps", name, "day_done.npy")
        if a.resume and done_f.exists() and cache_f.exists() and done_f.stat().st_mtime > cache_f.stat().st_mtime:
            logger.info("step 2: outputs newer than the CHIRPS cache - skipped (--resume)")
            record(2, "", 0, 0, "resumed")
        else:
            cmd = [py, SCRIPTS[2], *reg, "--workers", a.workers]
            logger.info(f"step 2: {' '.join(map(str, cmd[1:]))}")
            if not a.dry_run:
                rc, mins = run(cmd, logs / "step2.log")
                record(2, "", rc, mins, "ok" if rc == 0 else "failed")
                stop_on_failure(2, rc, mins, logs / "step2.log")

    # ---------------------------------------------------------------- step 3
    if 3 in a.steps:
        countries = [c.upper() for c in (a.countries or SSA_ISO3)]
        bnd = C.load_boundaries(bbox)
        present = set(bnd["iso_a3"]) if bnd is not None else set(countries)
        todo, absent = [c for c in countries if c in present], [c for c in countries if c not in present]
        for c in absent:
            logger.info(f"step 3 {c}: no polygon inside the region bbox - not run")
            record(3, c, None, 0, "not_in_region")
        w = max(1, a.workers // max(1, a.country_jobs))
        extra = shlex.split(a.step3_args)

        def one(c):
            st = rdir / "step03" / c / "status.json"
            if a.resume and st.exists():
                s = C.read_json(st).get("status")
                if s in ("ok", "skipped"):
                    return c, 0, 0, f"resumed ({s})", ""
            cmd = [py, SCRIPTS[3], "--region", name, "--iso3", c, "--workers", w, *extra]
            if a.dry_run:
                return c, 0, 0, "planned", ""
            rc, mins = run(cmd, logs / f"step3_{c}.log")
            state = {0: "ok", SKIP_EXIT: "skipped"}.get(rc, "failed")
            note = C.read_json(st).get("reason", "") if (rc == SKIP_EXIT and st.exists()) else ""
            return c, rc, mins, state, note

        logger.info(f"step 3: {len(todo)} countries, {a.country_jobs} at a time, {w} workers each")
        n = {"ok": 0, "skipped": 0, "failed": 0}
        with ThreadPoolExecutor(max_workers=max(1, a.country_jobs)) as pool:
            futs = [pool.submit(one, c) for c in todo]
            for i, f in enumerate(as_completed(futs), 1):
                c, rc, mins, state, note = f.result()
                record(3, c, rc, mins, state, note)
                for k in n:
                    n[k] += state == k or state == f"resumed ({k})"
                msg = f"step 3 [{i}/{len(todo)}] {c}: {state}" + (f" in {mins} min" if mins else "") + \
                      (f" - {note}" if note else "")
                (logger.error(msg + f"\n{tail(logs / f'step3_{c}.log')}") if state == "failed" else logger.info(msg))
        logger.info(f"step 3: ok {n['ok']}, skipped {n['skipped']}, failed {n['failed']}, not in region {len(absent)}")

    # ---------------------------------------------------------------- step 4
    if 4 in a.steps:
        cmd = [py, SCRIPTS[4], "--region", name, "--name", a.name]
        if a.countries:
            cmd += ["--countries", *[c.upper() for c in a.countries]]
        logger.info(f"step 4: {' '.join(map(str, cmd[1:]))}")
        if not a.dry_run:
            rc, mins = run(cmd, logs / "step4.log")
            record(4, "", rc, mins, "ok" if rc == 0 else "failed")
            if rc != 0:
                logger.error(f"step 4 FAILED (exit {rc}):\n{tail(logs / 'step4.log')}")
            else:
                logger.info(f"step 4: done in {mins} min -> {rdir / 'step03' / a.name}")

    logger.info(f"run_all finished in {(time.time() - t_all) / 60:.1f} min - status: {rdir / 'run_all_status.csv'}")
    if any(s["status"] == "failed" for s in status):
        sys.exit(1)


if __name__ == "__main__":
    main()

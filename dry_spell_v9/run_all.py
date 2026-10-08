#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_all.py - the whole v9 dry-spell workflow, from scratch
==========================================================

  step 1  v9_01_download.py         CHIRPS v2.0 daily, PKU GIMMS NDVI, boundaries, AEZ, Koppen (resumable)
  step 2  v9_02_ndvi_phenology.py   NDVI seasons: number per year, start / end (only if USE_NDVI)
  step 3  v9_03_spells_seasons.py   dry spells, regime (rain + NDVI), major-season onset / demise
  step 4  v9_04_sowing_risk.py      ONE RUN PER COUNTRY -> dryspell_v9/<region>/step04/<ISO3>/
                                    or ONE target: --target_bbox / --target_polygon / --target_point
  step 5  v9_05_aggregate.py        all countries -> dryspell_v9/<region>/step04/<SSA_NAME>/
  step 6  v9_06_spell_stats.py      dry spells inside the season (number, first / last / longest start
                                    and duration): maps, PDFs, summaries by latitude and zone, for the
                                    whole region (or the single target) -> step06/<region or target>/

Settings: v9_config.py; --config my_settings.json overrides any of them for every step
(e.g. {"FALSE_START_EXCLUDE": true, "SUMMARY_ZONES": "koppen", "DEMISE_ADJUST": "none"}).
Run it from any working folder; inputs go to ./dryspell_v9_data, results to ./dryspell_v9.

  nohup python run_all.py --region ssa --workers 40 --country_jobs 4 > run_all_ssa.out 2>&1 &
  python run_all.py --region ssa --resume                    # continue after a crash / time-out
  python run_all.py --region ssa --dry_run                   # show the plan
  python run_all.py --region ci_nga --workers 8              # the GitHub CI box (parity check:
  python tests/compare_reference.py --region ci_nga          #  same numbers as the CI reference)
  python run_all.py --region ci_nga --steps 4 --target_point 12.0 8.5
  python run_all.py --region ssa --steps 4 --target_polygon states.gpkg --polygon_field NAME \\
         --polygon_value Kano --target_name kano

* Step 1 always resumes (only missing days / half-months are downloaded).
* --resume also skips steps 2-3 when their outputs are newer than their inputs and every
  country whose step04/<ISO3>/status.json says ok or skipped.
  Changing settings? Do NOT use --resume for the steps they affect.
* A failing country is logged and the run continues; steps 1-3 failing stops the run.
* --country_jobs N runs N countries at once; --workers is shared between them.
* Extra step 4 options pass through: --step4_args "--grace 10 --zones koppen".
* Log: dryspell_v9/<region>/run_all.log, run_all_status.csv, run_all_logs/.
"""

import argparse
import logging
import os
import shlex
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent

# --config must be known BEFORE v9_common is imported (it reads $DRYSPELL_V9_CONFIG); the
# child steps inherit the environment variable.
_pre = argparse.ArgumentParser(add_help=False)
_pre.add_argument("--config", default=None)
_cfg = _pre.parse_known_args()[0].config
if _cfg:
    if not Path(_cfg).exists():
        sys.exit(f"--config {_cfg}: file not found")
    os.environ["DRYSPELL_V9_CONFIG"] = str(Path(_cfg).resolve())

sys.path.insert(0, str(HERE))
import v9_common as C   # noqa: E402

SCRIPTS = {1: HERE / "v9_01_download.py", 2: HERE / "v9_02_ndvi_phenology.py",
           3: HERE / "v9_03_spells_seasons.py", 4: HERE / "v9_04_sowing_risk.py", 5: HERE / "v9_05_aggregate.py",
           6: HERE / "v9_06_spell_stats.py"}
SKIP_EXIT = 3      # step 4: nothing to analyse in this country / target

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


def newer(outputs, inputs):
    """True if every output exists and is newer than every existing input."""
    outs = [Path(p) for p in outputs]
    ins = [Path(p) for p in inputs if Path(p).exists()]
    if not all(p.exists() for p in outs):
        return False
    return min(p.stat().st_mtime for p in outs) > max([p.stat().st_mtime for p in ins] or [0])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None, help="JSON file overriding v9_config.py settings (all steps)")
    ap.add_argument("--region", default="ssa", help=f"one of {list(C.REGIONS)} or a new name with --bbox")
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("LON_MIN", "LAT_MIN", "LON_MAX", "LAT_MAX"),
                    help="extent of a NEW region (data download + steps 2-3)")
    ap.add_argument("--steps", nargs="+", type=int, default=[1, 2, 3, 4, 5, 6], choices=[1, 2, 3, 4, 5, 6])
    ap.add_argument("--countries", nargs="+", default=None, help="ISO3 codes (default: all SSA countries in the region)")
    tg = ap.add_mutually_exclusive_group()
    tg.add_argument("--target_bbox", nargs=4, type=float, metavar=("W", "S", "E", "N"),
                    help="steps 4 and 6 for this box only (no country loop, no step 5)")
    tg.add_argument("--target_polygon", default=None, help="step 4 for this polygon file only")
    tg.add_argument("--target_point", nargs=2, type=float, metavar=("LAT", "LON"), help="step 4 for one cell")
    ap.add_argument("--polygon_field", default=None)
    ap.add_argument("--polygon_value", default=None)
    ap.add_argument("--target_name", default=None, help="step04 folder name of the single target")
    ap.add_argument("--workers", type=int, default=16, help="CPU workers (shared between --country_jobs)")
    ap.add_argument("--threads", type=int, default=32, help="parallel downloads in step 1")
    ap.add_argument("--country_jobs", type=int, default=1, help="countries run at the same time in step 4")
    ap.add_argument("--step4_args", default="", help='extra step 4 options, e.g. "--grace 10 --zones koppen"')
    ap.add_argument("--step6_args", default="", help='extra step 6 options, e.g. "--zones koppen"')
    ap.add_argument("--name", default=C.SSA_NAME, help="step 5 output folder (step04/<name>)")
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
    single = a.target_bbox or a.target_polygon or a.target_point
    target_args = []
    if a.target_bbox:
        target_args = ["--bbox", *a.target_bbox]
    elif a.target_polygon:
        target_args = ["--polygon", a.target_polygon]
        if a.polygon_field:
            target_args += ["--polygon_field", a.polygon_field, "--polygon_value", a.polygon_value]
    elif a.target_point:
        target_args = ["--point", *a.target_point]
    steps = [s for s in a.steps if not (s == 2 and not C.USE_NDVI) and not (s == 5 and single)]
    status = []
    t_all = time.time()
    logger.info("=" * 70)
    logger.info(f"run_all v9  region={name} bbox={bbox} steps={steps} workers={a.workers} "
                f"country_jobs={a.country_jobs} resume={a.resume} config={C.CONFIG_FILE or 'v9_config.py'}")
    logger.info(f"  USE_NDVI={C.USE_NDVI} REGIME_SOURCE={C.REGIME_SOURCE} DEMISE_ADJUST={C.DEMISE_ADJUST} "
                f"FALSE_START_EXCLUDE={C.FALSE_START_EXCLUDE} FALSE_DEMISE_EXCLUDE={C.FALSE_DEMISE_EXCLUDE} "
                f"SUMMARY_ZONES={C.SUMMARY_ZONES}")
    logger.info("=" * 70)
    if not a.dry_run:
        C.write_json(rdir / "run_all_settings.json", C.settings_json())

    import pandas as pd
    sf = rdir / "run_all_status.csv"
    started = time.strftime("%Y-%m-%d %H:%M:%S")
    previous = pd.read_csv(sf) if (sf.exists() and not a.dry_run) else None   # earlier runs are kept

    def record(step, unit, rc, minutes, state, note=""):
        status.append({"run_started": started, "step": step, "unit": unit, "exit_code": rc, "status": state,
                       "minutes": minutes, "note": note})
        if not a.dry_run:
            pd.concat([previous, pd.DataFrame(status)], ignore_index=True).to_csv(sf, index=False)

    def stop_on_failure(step, rc, mins, log):
        if rc != 0:
            logger.error(f"step {step} FAILED (exit {rc}) after {mins} min - last lines of {log}:\n{tail(log)}")
            sys.exit(f"stopping: step {step} failed")
        logger.info(f"step {step}: done in {mins} min")

    def simple_step(step, cmd, outputs=None, inputs=None):
        if a.resume and outputs and newer(outputs, inputs or []):
            logger.info(f"step {step}: outputs newer than inputs - skipped (--resume)")
            record(step, "", 0, 0, "resumed")
            return
        logger.info(f"step {step}: {' '.join(map(str, cmd[1:]))}")
        if a.dry_run:
            return
        rc, mins = run(cmd, logs / f"step{step}.log")
        record(step, "", rc, mins, "ok" if rc == 0 else "failed")
        stop_on_failure(step, rc, mins, logs / f"step{step}.log")

    # ---------------------------------------------------------------- step 1
    if 1 in steps:
        only = ["boundaries", "aez", "koppen", "chirps"] + (["ndvi"] if C.USE_NDVI else [])
        simple_step(1, [py, SCRIPTS[1], *reg, "--threads", a.threads, "--only", *only])
        if not a.dry_run:
            meta = C.read_json(C.data_dir("chirps", name, "meta.json"))
            if meta.get("failed_days"):
                logger.warning(f"step 1: {len(meta['failed_days'])} days could not be downloaded (they count as "
                               f"missing): {meta['failed_days'][:10]} - rerun to retry them")

    # ---------------------------------------------------------------- steps 2-3
    ndvi_in = C.data_dir("ndvi", name, "period_done.npy")
    chirps_in = C.data_dir("chirps", name, "day_done.npy")
    cfg_in = [C.CONFIG_FILE] if C.CONFIG_FILE else []
    cfg_in.append(HERE / "v9_config.py")
    if 2 in steps:
        simple_step(2, [py, SCRIPTS[2], *reg, "--workers", a.workers],
                    [rdir / "step02" / "ndvi_phenology.nc"], [ndvi_in, *cfg_in])
    if 3 in steps:
        simple_step(3, [py, SCRIPTS[3], *reg, "--workers", a.workers],
                    [rdir / "step03" / "meta.json"],
                    [chirps_in, rdir / "step02" / "ndvi_phenology.nc", *cfg_in])

    # ---------------------------------------------------------------- step 4
    if 4 in steps and single:
        cmd = [py, SCRIPTS[4], "--region", name, "--workers", a.workers, *target_args]
        if a.target_name:
            cmd += ["--name", a.target_name]
        cmd += shlex.split(a.step4_args)
        logger.info(f"step 4: {' '.join(map(str, cmd[1:]))}")
        if not a.dry_run:
            rc, mins = run(cmd, logs / "step4_target.log")
            state = {0: "ok", SKIP_EXIT: "skipped"}.get(rc, "failed")
            record(4, a.target_name or "target", rc, mins, state)
            (logger.error if state == "failed" else logger.info)(
                f"step 4 target: {state} in {mins} min\n{tail(logs / 'step4_target.log', 4)}")
    elif 4 in steps:
        countries = [c.upper() for c in (a.countries or SSA_ISO3)]
        bnd = C.load_boundaries(bbox)
        present = set(bnd["iso_a3"]) if bnd is not None else set(countries)
        todo, absent = [c for c in countries if c in present], [c for c in countries if c not in present]
        for c in absent:
            logger.info(f"step 4 {c}: no polygon inside the region bbox - not run")
            record(4, c, None, 0, "not_in_region")
        w = max(1, a.workers // max(1, a.country_jobs))
        extra = shlex.split(a.step4_args)

        def one(c):
            st = rdir / "step04" / c / "status.json"
            if a.resume and st.exists():
                s = C.read_json(st).get("status")
                if s in ("ok", "skipped"):
                    return c, 0, 0, f"resumed ({s})", ""
            cmd = [py, SCRIPTS[4], "--region", name, "--iso3", c, "--workers", w, *extra]
            if a.dry_run:
                return c, 0, 0, "planned", ""
            rc, mins = run(cmd, logs / f"step4_{c}.log")
            state = {0: "ok", SKIP_EXIT: "skipped"}.get(rc, "failed")
            note = C.read_json(st).get("reason", "") if (rc == SKIP_EXIT and st.exists()) else ""
            return c, rc, mins, state, note

        logger.info(f"step 4: {len(todo)} countries, {a.country_jobs} at a time, {w} workers each")
        n = {"ok": 0, "skipped": 0, "failed": 0}
        with ThreadPoolExecutor(max_workers=max(1, a.country_jobs)) as pool:
            futs = [pool.submit(one, c) for c in todo]
            for i, f in enumerate(as_completed(futs), 1):
                c, rc, mins, state, note = f.result()
                record(4, c, rc, mins, state, note)
                for k in n:
                    n[k] += state == k or state == f"resumed ({k})"
                msg = f"step 4 [{i}/{len(todo)}] {c}: {state}" + (f" in {mins} min" if mins else "") + \
                      (f" - {note}" if note else "")
                (logger.error(msg + f"\n{tail(logs / f'step4_{c}.log')}") if state == "failed" else logger.info(msg))
        logger.info(f"step 4: ok {n['ok']}, skipped {n['skipped']}, failed {n['failed']}, not in region {len(absent)}")

    # ---------------------------------------------------------------- step 5
    if 5 in steps:
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
                logger.info(f"step 5: done in {mins} min -> {rdir / 'step04' / a.name}")

    # ---------------------------------------------------------------- step 6
    if 6 in steps:
        cmd = [py, SCRIPTS[6], "--region", name, "--workers", a.workers] + shlex.split(a.step6_args)
        if single:
            cmd += [str(x) for x in target_args] + (["--name", a.target_name] if a.target_name else [])
        logger.info(f"step 6: {' '.join(map(str, cmd[1:]))}")
        if not a.dry_run:
            rc, mins = run(cmd, logs / "step6.log")
            state = {0: "ok", SKIP_EXIT: "skipped"}.get(rc, "failed")
            record(6, a.target_name or ("target" if single else name), rc, mins, state)
            (logger.error if state == "failed" else logger.info)(
                f"step 6: {state} in {mins} min\n{tail(logs / 'step6.log', 3)}")

    logger.info(f"run_all finished in {(time.time() - t_all) / 60:.1f} min - status: {rdir / 'run_all_status.csv'}")
    if any(s["status"] == "failed" for s in status):
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
estimate_effects.py - effect estimation of the study "accessibility change, land-use change and crop
yields in Sub-Saharan Africa" (Phase 3: Gate C, Gate V, composite label). Pure Python (no R needed).
Called by access_effects_v01.py (stage estimate), or by hand:
    python estimate_effects.py <panels folder> <output folder> [config.json]

Port of the earlier estimate_effects.R (kept as dev/reference_estimate_effects.R; dev/test_estimate_parity.py
compares the two). Estimators:
    cs        Callaway & Sant'Anna (moderndid att_gt / aggte; outcome regression, varying base period,
              multiplier bootstrap clustered by unit, sampling weights, unbalanced panels)
    contdid   Callaway, Goodman-Bacon & Sant'Anna continuous dose (moderndid cont_did; average causal
              response on the treated, ACRT). Unweighted and on balanced panels only (a limit of the method's
              implementation, as in R contdid): the rows say so in the column `note`
    sunab     Sun & Abraham: cohort x relative-period interactions (never-treated as control, reference
              period -1) in a pyfixest regression with unit and region x year effects; aggregated to the ATT
              with weights = observations per cohort x period, as fixest::aggregate(agg = "ATT")
    twfe      two-way fixed effects, for comparison only (biased with staggered timing)
    longdiff  long differences on the access gain with region x epoch effects
Standard errors of sunab, twfe and longdiff are Conley (1999) spatial HAC errors computed here as in
fixest::conley: uniform kernel within CONLEY_KM, every pair of observations (any period) within the cutoff,
small-sample factor (N - 1) / (N - K) with K counting the fixed effects. Tested against fixest to < 1%.

Inputs (written by stage panels), outputs and column schema are those of the R script:
    estimates.csv (every coefficient; failed models kept with their error), gate_c.csv, gate_v.csv, versions.txt
"""
from __future__ import annotations

import json
import math
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULTS = {   # approved 2026-10-27 (revision 2 drafts marked in the study design); config.json overrides
    "primary_spec": "roadonly_cities_11",
    "specs": ["roadonly_cities_11", "total_cities_11", "roadonly_cities_12", "roadonly_ports_5"],
    "min_e": -5, "max_e": 5,
    "conley_km": 50,
    "bh_q": 0.10,
    "gate_pre_p": 0.10, "gate_pre_ratio": 1 / 3, "gate_placebo_ratio": 0.5, "gate_placebo_p": 0.05,
    "bootstrap_iters": 999,
    "seed": 20261028,
    "max_units_cs": 200000,
    "max_units_sa": 100000,
    "composite_shift": 0.05, "gate_v_r": 0.3, "gate_v_min_n": 30, "gate_v_r_sensor": 0.8,
}
COLUMNS = ["dataset", "outcome", "crop", "spec", "estimator", "control", "term", "estimate", "se", "p", "n",
           "error", "note"]
SHARE_OUTCOMES = ["share_maize", "share_cassava", "share_rice", "share_sorghum_millet", "share_cash",
                  "share_staples_other", "shannon"]
R_EARTH_KM = 6371.0088


def log(*a):
    print(time.strftime("[%Y-%m-%d %H:%M:%S]"), *a, flush=True)


def normal_p(est, se):
    from scipy.stats import norm
    with np.errstate(invalid="ignore", divide="ignore"):
        return float(2 * norm.sf(abs(est / se))) if se and np.isfinite(se) and se > 0 else np.nan


def row(meta, term="overall", estimate=np.nan, se=np.nan, p=np.nan, n=None, error=None, note=None):
    return {**meta, "term": term, "estimate": float(estimate) if estimate is not None else np.nan,
            "se": float(se) if se is not None else np.nan, "p": float(p) if p is not None else np.nan,
            "n": int(n) if n is not None else None, "error": error, "note": note}


def safely_run(fn, meta):
    """Run one model; a failure becomes one row with its error (never dropped)."""
    try:
        out = fn()
    except Exception as e:                              # noqa: BLE001 - every failure is reported
        msg = f"{type(e).__name__}: {e}"
        log("  failed:", meta.get("estimator"), meta.get("control"), msg[:200])
        out = [row(meta, error=msg[:1000])]
    return out


# =============================================================================
# Conley standard errors
# =============================================================================
def unit_xyz(lat, lon):
    la, lo = np.radians(np.asarray(lat, float)), np.radians(np.asarray(lon, float))
    return np.column_stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)])


def conley_meat(scores, lat, lon, cutoff_km):
    """sum over every pair of observations (i, j) within cutoff_km (i = j included) of s_i s_j', with a
    uniform kernel, as fixest::conley (observations of any period are paired). Scores at the same location
    are summed first, so repeated panel coordinates cost nothing."""
    from scipy.spatial import cKDTree
    s = np.asarray(scores, float)
    if s.ndim == 1:
        s = s[:, None]
    key = pd.DataFrame({"lat": np.round(np.asarray(lat, float), 7), "lon": np.round(np.asarray(lon, float), 7)})
    loc = key.groupby(["lat", "lon"], sort=False).ngroup().to_numpy()
    S = np.zeros((loc.max() + 1, s.shape[1]))
    np.add.at(S, loc, s)
    first = pd.Series(np.arange(len(loc))).groupby(loc).first().to_numpy()
    xyz = unit_xyz(key.lat.to_numpy()[first], key.lon.to_numpy()[first])
    chord = 2 * math.sin(cutoff_km / (2 * R_EARTH_KM))
    from scipy import sparse
    meat = S.T @ S
    tree = cKDTree(xyz)
    # neighbours in chunks of query points, as a sparse 0/1 block: memory grows with the pairs, not with
    # pairs x regressors
    step = 20000
    L = len(xyz)
    for a in range(0, L, step):
        nb = tree.query_ball_point(xyz[a:a + step], chord)
        ii = np.repeat(np.arange(len(nb)), [len(x) for x in nb])
        jj = np.concatenate([np.asarray(x, dtype=np.int64) for x in nb]) if len(nb) else np.array([], np.int64)
        keep = jj > ii + a                                  # each unordered pair once (i = j counted above)
        ii, jj = ii[keep], jj[keep]
        if len(ii):
            A = sparse.csr_matrix((np.ones(len(ii)), (ii, jj)), shape=(len(nb), L))
            cross = S[a:a + len(nb)].T @ (A @ S)
            meat += cross + cross.T
    return meat


def fe_count(data, fes):
    """Number of fixed-effect parameters (levels of every FE dimension, minus one per extra dimension)."""
    k = 0
    for f in fes:
        parts = f.split("^")
        k += data.groupby(parts, sort=False).ngroups
    return k - (len(fes) - 1)


def feols_conley(fml, data, weights, cutoff_km, fes):
    """pyfixest regression; returns (coef Series, Conley vcov DataFrame, fitted model, N)."""
    import pyfixest as pf
    # pyfixest's compiled demeaner aborts the whole process (not a Python error) on empty or degenerate
    # input, so the data are checked here first
    rhs = fml.split("~", 1)[1].split("|")[0]
    xs = [v.strip() for v in rhs.split("+") if v.strip()]
    need = [fml.split("~", 1)[0].strip(), *xs, weights, "lat", "lon"] + [p for f in fes for p in f.split("^")]
    need = [c for c in dict.fromkeys(need) if c]
    ok = data[need].notna().all(axis=1)
    if not ok.all():                                        # copy only when rows must go
        data = data[ok]
    if len(data) == 0:
        raise ValueError("no observations")
    if fe_count(data, fes) + len(xs) >= len(data):
        raise ValueError(f"too few observations ({len(data)}) for {len(xs)} regressors and the fixed effects")
    if all(data[x].nunique() <= 1 for x in xs):
        raise ValueError("no variation in the regressors")
    fit = pf.feols(fml, data=data, weights=weights, vcov="hetero", copy_data=False)
    used = fit._data
    s, bread = np.asarray(fit._scores), np.asarray(fit._bread)
    N, K = s.shape
    meat = conley_meat(s, used["lat"].to_numpy(), used["lon"].to_numpy(), cutoff_km)
    kk = K + fe_count(used, fes)
    V = bread @ meat @ bread * (N - 1) / max(N - kk, 1)
    names = list(fit.coef().index)
    return fit.coef(), pd.DataFrame(V, index=names, columns=names), fit, N


# =============================================================================
# estimators
# =============================================================================
def keep_valid(d, yname, gname, weights=None):
    d = d[d[yname].notna() & d[gname].notna() & (d[gname] >= 0)]
    if weights:
        d = d[d[weights].notna()]
    return d


def cap_units(d, gname, cap, rng):
    """At most `cap` units: every treated unit and a random draw of the never-treated ones, but at least half
    of the cap goes to never-treated units (when there are that many), the treated being drawn at random
    when they alone would fill the cap. Without never-treated units the cohort x period terms of Sun-Abraham
    are not identified."""
    units = d["id"].unique()
    if len(units) <= cap:
        return d
    treated = d.loc[d[gname] > 0, "id"].unique()
    ctrl = np.setdiff1d(units, treated)
    n_ctrl = min(len(ctrl), max(cap - len(treated), cap // 2))
    n_tr = min(len(treated), cap - n_ctrl)
    keep_t = rng.choice(treated, n_tr, replace=False) if n_tr < len(treated) else treated
    keep_c = rng.choice(ctrl, n_ctrl, replace=False) if n_ctrl < len(ctrl) else ctrl
    return d[d["id"].isin(np.concatenate([keep_t, keep_c]))]


def cs_estimate(d, yname, gname, control, meta, cfg, rng, weights="w"):
    import moderndid as md
    d = keep_valid(d, yname, gname, weights)
    d = cap_units(d, gname, cfg["max_units_cs"], rng)
    n_treated = d.loc[d[gname] > 0, "id"].nunique()
    if n_treated == 0:
        raise ValueError("no treated units")
    cols = ["id", "year", yname, gname] + ([weights] if weights else [])
    dd = d[cols].copy()
    dd[gname] = dd[gname].astype(int)
    att = md.att_gt(data=dd, yname=yname, tname="year", idname="id", gname=gname, weightsname=weights,
                    control_group=control, est_method="reg", base_period="varying", allow_unbalanced_panel=True,
                    boot=True, biters=int(cfg["bootstrap_iters"]), clustervars=["id"], panel=True,
                    random_state=int(cfg["seed"]))
    dyn = md.aggte(att, type="dynamic", min_e=cfg["min_e"], max_e=cfg["max_e"], na_rm=True)
    simple = md.aggte(att, type="simple", na_rm=True)
    pre_p = getattr(att, "wald_pvalue", None)
    out = [row(meta, "overall", simple.overall_att, simple.overall_se, normal_p(simple.overall_att, simple.overall_se),
               n=dd["id"].nunique()),
           row(meta, "pretest_wald", np.nan, np.nan, pre_p if pre_p is not None else np.nan, n=n_treated,
               note=None if pre_p is not None else "Wald pre-test not available")]
    for e, a, s in zip(np.asarray(dyn.event_times), np.asarray(dyn.att_by_event), np.asarray(dyn.se_by_event)):
        out.append(row(meta, f"e{int(e)}", a, s, normal_p(a, s), n=n_treated))
    return out


def sa_estimate(d, yname, gname, meta, cfg, rng):
    """Sun & Abraham interaction-weighted estimator (as fixest::sunab, reference period -1)."""
    d = keep_valid(d, yname, gname, "w")
    d = cap_units(d, gname, cfg["max_units_sa"], rng)[["id", "year", "region", "lat", "lon", "w", yname, gname]]
    cohort = d[gname].to_numpy()
    rel = np.where(cohort > 0, d["year"].to_numpy() - cohort, 0)
    cells = sorted({(int(c), int(r)) for c, r in zip(cohort, rel) if c > 0 and r != -1})
    if not cells:
        raise ValueError("no treated cohort x period cells")
    names = [f"sa_c{c}_e{'m' if r < 0 else 'p'}{abs(r)}" for c, r in cells]
    dummies = pd.DataFrame({nm: ((cohort == c) & (rel == r)).astype(np.float64) for nm, (c, r) in zip(names, cells)},
                           index=d.index)
    d = pd.concat([d, dummies], axis=1, copy=False)
    del dummies
    fml = f"{yname} ~ {' + '.join(names)} | id + region^year"
    b, V, fit, N = feols_conley(fml, d, "w", cfg["conley_km"], ["id", "region^year"])
    used = fit._data
    # weighted shares, as fixest::aggregate (colSums(weights * sign(mm)))
    wts = used["w"].to_numpy()
    counts = {nm: float(wts @ used[nm].to_numpy()) for nm in names}
    names = [nm for nm in names if nm in b.index]                    # pyfixest drops collinear terms
    cell_of = dict(zip([f"sa_c{c}_e{'m' if r < 0 else 'p'}{abs(r)}" for c, r in cells], cells))

    def combo(sel):
        w = np.array([counts[nm] if sel(cell_of[nm]) else 0.0 for nm in names])
        if w.sum() == 0:
            return None
        w = w / w.sum()
        est = float(w @ b[names].to_numpy())
        se = float(np.sqrt(w @ V.loc[names, names].to_numpy() @ w))
        return est, se
    out = []
    att = combo(lambda cr: cr[1] >= 0)
    if att is None:
        raise ValueError("no post-treatment cells")
    out.append(row(meta, "overall", att[0], att[1], normal_p(*att), n=N))
    for r in sorted({cr[1] for cr in cells}):
        v = combo(lambda cr, r=r: cr[1] == r)
        if v:
            out.append(row(meta, f"e{r}", v[0], v[1], normal_p(*v), n=N))
    return out


def twfe_estimate(d, yname, gname, meta, cfg, dose=None):
    d = keep_valid(d, yname, gname).copy()
    d["post"] = ((d[gname] > 0) & (d["year"] >= d[gname])).astype(np.float64)
    x = "post"
    if dose:
        d["post_dose"] = d["post"] * d[dose]
        x = "post_dose"
    b, V, fit, N = feols_conley(f"{yname} ~ {x} | id + region^year", d, "w", cfg["conley_km"], ["id", "region^year"])
    se = float(np.sqrt(V.loc[x, x]))
    return [row(meta, "overall", b[x], se, normal_p(b[x], se), n=N)]


def dose_estimate(d, yname, gname, dname, meta, cfg):
    import moderndid as md
    d = d[d[yname].notna() & (d[gname] >= 0) & d[dname].notna() & ((d[gname] == 0) | (d[dname] > 0))]
    # moderndid cont_did needs a balanced panel and no weights: keep units observed in every year
    years = d["year"].nunique()
    full = d.groupby("id")["year"].transform("nunique") == years
    dd = d.loc[full, ["id", "year", yname, gname, dname]].copy()
    if dd.empty:
        raise ValueError("no balanced units for the continuous design")
    dd[gname] = dd[gname].astype(int)
    res = md.cont_did(data=dd, yname=yname, tname="year", idname="id", gname=gname, dname=dname,
                      target_parameter="slope", aggregation="dose", treatment_type="continuous",
                      control_group="notyettreated", biters=int(cfg["bootstrap_iters"]),
                      random_state=int(cfg["seed"]))
    est, se = getattr(res, "overall_acrt", np.nan), getattr(res, "overall_acrt_se", np.nan)
    return [row(meta, "overall_acrt", est, se, normal_p(est, se), n=dd["id"].nunique(),
                note="unweighted, balanced panel (cont_did)")]


def ld_estimate(d, yname, xname, meta, cfg):
    # covariates that have values in this dataset (pooled long-difference files hold all-NaN columns
    # for datasets without them)
    covs = [c for c in ("d_rain", "d_logpop", "d_conflict") if c in d.columns and d[c].notna().any()]
    d = d.dropna(subset=[yname, xname] + covs).copy()
    fml = f"{yname} ~ {' + '.join([xname] + covs)} | region^epoch"
    b, V, fit, N = feols_conley(fml, d, "w", cfg["conley_km"], ["region^epoch"])
    se = float(np.sqrt(V.loc[xname, xname]))
    return [row(meta, "overall", b[xname], se, normal_p(b[xname], se), n=N)]


# =============================================================================
# designs per dataset
# =============================================================================
def run_dataset(d, dataset, outcomes, cfg, rng, by_crop=False):
    if d is None or d.empty:
        return []
    groups = sorted(d["crop"].dropna().unique()) if by_crop else [None]
    specs = [s for s in cfg["specs"] if f"g__{s}" in d.columns]
    rows = []
    for cr in groups:
        dd = d[d["crop"] == cr] if by_crop else d
        present = [y for y in outcomes if y in dd.columns and dd[y].notna().any()]
        for y in present:
            for sp in specs:
                g = f"g__{sp}"
                base = {"dataset": dataset, "outcome": y, "crop": cr, "spec": sp}
                log(dataset, y, cr, sp)
                for control in ("notyettreated", "nevertreated"):
                    m = {**base, "estimator": "cs", "control": control}
                    rows += safely_run(lambda m=m, control=control: cs_estimate(dd, y, g, control, m, cfg, rng), m)
                if sp != cfg["primary_spec"]:
                    continue
                if "w_cem" in dd.columns:
                    m = {**base, "estimator": "cs", "control": "matched"}
                    rows += safely_run(lambda m=m: cs_estimate(dd, y, g, "nevertreated", m, cfg, rng, weights="w_cem"), m)
                band = f"band__{sp}"
                if band in dd.columns:
                    db = dd[dd[band].notna()].copy()
                    db["gband"] = np.where(db[band] == 1, db[g], 0)
                    m = {**base, "estimator": "cs", "control": "bands"}
                    rows += safely_run(lambda m=m, db=db: cs_estimate(db, y, "gband", "nevertreated", m, cfg, rng), m)
                gb = f"gburst__{sp}"
                if gb in dd.columns:
                    dp = dd[(dd[g] == 0) | (dd[gb] > 0)].copy()
                    dp["gplacebo"] = dp[gb]
                    m = {**base, "estimator": "cs_placebo_burst", "control": "nevertreated"}
                    rows += safely_run(lambda m=m, dp=dp: cs_estimate(dp, y, "gplacebo", "nevertreated", m, cfg, rng), m)
                m = {**base, "estimator": "sunab", "control": "nevertreated"}
                rows += safely_run(lambda m=m: sa_estimate(dd, y, g, m, cfg, rng), m)
                m = {**base, "estimator": "twfe", "control": "all"}
                rows += safely_run(lambda m=m: twfe_estimate(dd, y, g, m, cfg), m)
                dn = f"dose__{sp}"
                if dn in dd.columns:
                    m = {**base, "estimator": "contdid", "control": "notyettreated"}
                    rows += safely_run(lambda m=m: dose_estimate(dd, y, g, dn, m, cfg), m)
                    m = {**base, "estimator": "twfe_dose", "control": "all"}
                    rows += safely_run(lambda m=m: twfe_estimate(dd, y, g, m, cfg, dose=dn), m)
    return rows


def run_longdiff(d, cfg):
    if d is None or d.empty:
        return []
    ys = [c for c in d.columns if c.startswith("d_") and not c.startswith("d_access")
          and c not in ("d_rain", "d_logpop", "d_conflict")]
    specs = [c[len("d_access__"):] for c in d.columns if c.startswith("d_access__")]
    rows = []
    for (ds, cr), dd in d.groupby(["dataset", d["crop"].fillna("__none__")], sort=True):
        crop = None if cr == "__none__" else cr
        for y in [y for y in ys if dd[y].notna().any()]:
            for sp in specs:
                x = f"d_access__{sp}"
                base = {"dataset": ds, "outcome": y[2:], "crop": crop, "spec": sp, "estimator": "longdiff",
                        "control": "all"}
                rows += safely_run(lambda base=base, dd=dd, y=y, x=x: ld_estimate(dd, y, x, base, cfg), base)
    return rows


# =============================================================================
# gates
# =============================================================================
def bh(p):
    """Benjamini-Hochberg adjusted p-values (NaN kept as NaN and not counted), as R p.adjust("BH")."""
    p = np.asarray(p, float)
    out = np.full(len(p), np.nan)
    ok = np.isfinite(p)
    if ok.any():
        from statsmodels.stats.multitest import multipletests
        out[ok] = multipletests(p[ok], method="fdr_bh")[1]
    return out


def same_crop(series, crop):
    return series.isna() if crop is None or (isinstance(crop, float) and np.isnan(crop)) else series == crop


GATE_C_COLUMNS = ["dataset", "outcome", "crop", "effect", "p", "c1_pretrends", "c2_placebo", "c3_controls_versions",
                  "c4_longdiff", "causal", "label"]


def gate_c(est, cfg):
    prim = est[est.spec == cfg["primary_spec"]]
    keys = prim[["dataset", "outcome", "crop"]].drop_duplicates()
    out = []
    for dataset, outcome, crop in keys.itertuples(index=False):
        crop = None if crop is None or (isinstance(crop, float) and np.isnan(crop)) else crop

        def sel(e, ctrl, sp=cfg["primary_spec"], tm="overall"):
            return est[(est.dataset == dataset) & (est.outcome == outcome) & same_crop(est.crop, crop)
                       & (est.spec == sp) & (est.estimator == e) & (est.control == ctrl) & (est.term == tm)]
        main = sel("cs", "notyettreated")
        eff = main.estimate.iloc[0] if len(main) else np.nan
        pre_p = sel("cs", "notyettreated", tm="pretest_wald").p
        pre = est[(est.dataset == dataset) & (est.outcome == outcome) & same_crop(est.crop, crop)
                  & (est.spec == cfg["primary_spec"]) & (est.estimator == "cs") & (est.control == "notyettreated")
                  & est.term.str.match(r"^e-\d+$") & (est.term != "e-1")]
        c1 = bool(len(pre_p) == 1 and pre_p.iloc[0] > cfg["gate_pre_p"]
                  and (np.abs(pre.estimate.dropna()) < cfg["gate_pre_ratio"] * abs(eff)).all())
        plc = sel("cs_placebo_burst", "nevertreated")
        c2 = (bool(plc.p.iloc[0] > cfg["gate_placebo_p"] and abs(plc.estimate.iloc[0]) < cfg["gate_placebo_ratio"] * abs(eff))
              if len(plc) and np.isfinite(plc.estimate.iloc[0]) else None)
        ctrls = pd.concat([sel("cs", "notyettreated"), sel("cs", "nevertreated"), sel("cs", "matched"), sel("cs", "bands")])
        ctrls = ctrls[np.isfinite(ctrls.estimate)]
        ps = cfg["primary_spec"]
        other = ps.replace("roadonly_", "total_", 1) if ps.startswith("roadonly_") else ps.replace("total_", "roadonly_", 1)
        alt = sel("cs", "notyettreated", sp=other)
        c3 = bool((np.sign(ctrls.estimate) == np.sign(eff)).sum() >= 2
                  and (len(alt) == 0 or np.sign(alt.estimate.iloc[0]) == np.sign(eff)))
        ld = est[(est.estimator == "longdiff") & (est.outcome == outcome) & same_crop(est.crop, crop)
                 & (est.spec == ps) & (est.dataset == dataset)]
        c4 = bool(np.sign(ld.estimate.iloc[0]) == np.sign(eff)) if len(ld) and np.isfinite(ld.estimate.iloc[0]) else None
        causal = bool(c1 and c2 is True and c3 and c4 is True)
        out.append({"dataset": dataset, "outcome": outcome, "crop": crop, "effect": eff,
                    "p": main.p.iloc[0] if len(main) else np.nan, "c1_pretrends": c1, "c2_placebo": c2,
                    "c3_controls_versions": c3, "c4_longdiff": c4, "causal": causal,
                    "label": "causal (Gate C passed)" if causal else "association"})
    g = pd.DataFrame(out, columns=GATE_C_COLUMNS)
    if len(g):
        g["q_bh"] = bh(g.p)
        g["significant_bh"] = g.q_bh <= cfg["bh_q"]
    return g


def composite_label(gc_tab, est, cfg):
    if gc_tab.empty:
        return gc_tab
    mix = est[est.dataset.str.startswith("E2e_") & (est.spec == cfg["primary_spec"]) & (est.estimator == "cs")
              & (est.control == "notyettreated") & (est.term == "overall") & est.outcome.str.startswith("share_")
              & (est.outcome != "share_sold") & np.isfinite(est.p)].copy()
    mix["q"] = bh(mix.p)
    mix["shift"] = (mix.q <= cfg["bh_q"]) & (mix.estimate.abs() >= cfg["composite_shift"])
    shift_admin = bool(mix.loc[mix.dataset == "E2e_admin", "shift"].any())
    shift_ea = bool(mix.loc[mix.dataset == "E2e_ea", "shift"].any())
    g = gc_tab.copy()
    g["crop_mix_shift"] = np.select([g.dataset.isin(["E2a_admin", "E2d_vigour"]), g.dataset == "E2b_ea"],
                                    [shift_admin | ((g.dataset == "E2d_vigour") & shift_ea), shift_ea], False)
    comp = g.crop_mix_shift & g.dataset.isin(["E2a_admin", "E2b_ea", "E2d_vigour"])
    g.loc[comp, "label"] = g.loc[comp, "label"] + "; composite (yield + crop mix)"
    return g


def gate_v(est, inputs_file, cfg):
    inp = pd.read_csv(inputs_file) if Path(inputs_file).exists() else pd.DataFrame()

    def sel(ds, out):
        return est[(est.dataset == ds) & (est.outcome == out) & (est.spec == cfg["primary_spec"])
                   & (est.estimator == "cs") & (est.control == "notyettreated") & (est.term == "overall")]
    main = sel("E2d_vigour", "ndvi_integral")
    if not len(main) or not np.isfinite(main.estimate.iloc[0]):
        return pd.DataFrame([{"criterion": "all", "pass": None, "detail": "no E2d estimate"}])
    eff = main.estimate.iloc[0]
    rows = []
    if len(inp) and "r_within" in inp:
        ok = inp[inp.r_within.notna() & (inp.n >= cfg["gate_v_min_n"])]
        rows.append({"criterion": "1 anomaly correlation", "pass": bool((ok.r_within >= cfg["gate_v_r"]).all()) if len(ok) else None,
                     "detail": f"{len(ok)} zones; min r {round(ok.r_within.min(), 3) if len(ok) else 'NA'}"})
    else:
        rows.append({"criterion": "1 anomaly correlation", "pass": None, "detail": "gate_v_inputs.csv missing"})
    yld = pd.concat([sel("E2a_admin", "log_yield"), sel("E2b_ea", "log_yield")])
    yld = yld[np.isfinite(yld.estimate)]
    rows.append({"criterion": "2 sign agreement with survey yields",
                 "pass": bool((np.sign(yld.estimate) == np.sign(eff)).all()) if len(yld) else None,
                 "detail": f"{len(yld)} yield estimates"})
    plc = pd.concat([sel("E2d_vigour", "ndvi_dry_integral"), sel("E2d_vigour", "ndvi_noncrop_integral")])
    plc_ok = plc[plc.p.notna() & plc.estimate.notna()]
    rows.append({"criterion": "3 placebos (dry season, non-cropland)",
                 "pass": bool(((plc_ok.p > 0.05) & (plc_ok.estimate.abs() < 0.5 * abs(eff))).all()) if len(plc_ok) else None,
                 "detail": f"{len(plc_ok)} placebo estimates ({len(plc) - len(plc_ok)} failed)"})
    idx = pd.concat([sel("E2d_vigour", "kndvi_integral"), sel("E2d_vigour", "evi_integral"), sel("E2d_vigour", "ndvi_peak")])
    idx = idx[np.isfinite(idx.estimate)]
    rs = inp.r_sensor.dropna() if len(inp) and "r_sensor" in inp else pd.Series(dtype=float)
    sens = bool((rs >= cfg["gate_v_r_sensor"]).all()) if len(rs) else None      # no second sensor: not assessed
    idx_ok = bool((np.sign(idx.estimate) == np.sign(eff)).all()) if len(idx) else None
    rows.append({"criterion": "4 index and sensor robustness",
                 "pass": (idx_ok and sens) if idx_ok is not None and sens is not None else
                         (False if idx_ok is False or sens is False else None),
                 "detail": f"{len(idx)} alternative indices; sensor r check {sens}"})
    out = pd.DataFrame(rows)
    allpass = bool(all(v is True for v in out["pass"]))
    return pd.concat([out, pd.DataFrame([{"criterion": "Gate V", "pass": allpass,
                                          "detail": "E2d interpreted only if every criterion passes"}])],
                     ignore_index=True)


# =============================================================================
# main
# =============================================================================
def read_panel(panels_dir, name):
    f = Path(panels_dir) / f"{name}.parquet"
    if not f.exists():
        log(f"{name}: not found, skipped")
        return None
    return pd.read_parquet(f)


def versions():
    out = {"python": sys.version.split()[0]}
    for m in ("moderndid", "pyfixest", "statsmodels", "numpy", "pandas", "scipy"):
        try:
            out[m] = __import__(m).__version__
        except Exception as e:                          # noqa: BLE001
            out[m] = f"not available ({e})"
    return out


def main(panels_dir="ae_results/panels", out_dir="ae_results/estimates", cfg_file=None):
    cfg = dict(DEFAULTS)
    if cfg_file and Path(cfg_file).exists():
        cfg.update(json.loads(Path(cfg_file).read_text()))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(int(cfg["seed"]))
    log(f"estimate_effects.py: panels {panels_dir} -> {out_dir}; {versions()}")
    P = {n: read_panel(panels_dir, n) for n in ("e1_cells", "e1c_replacement", "e2a_admin", "e2b_ea", "e2d_vigour",
                                                 "e2e_admin", "e2e_ea", "e3_longdiff")}
    rows = []
    rows += run_dataset(P["e1_cells"], "E1_cells", ["conv_share", "conv_annual_share", "conv_tree_share",
                                                    "newcrop_share", "loss_share"], cfg, rng)
    rows += run_dataset(P["e1c_replacement"], "E1c_replacement", ["repl_annual", "repl_tree", "repl_pasture",
                                                                  "repl_regrowth", "repl_other"], cfg, rng)
    rows += run_dataset(P["e2a_admin"], "E2a_admin", ["log_yield"], cfg, rng, by_crop=True)
    rows += run_dataset(P["e2b_ea"], "E2b_ea", ["log_yield", "log_value_ha"], cfg, rng, by_crop=True)
    rows += run_dataset(P["e2d_vigour"], "E2d_vigour", ["ndvi_integral", "ndvi_peak", "kndvi_integral", "evi_integral",
                                                        "ndvi_dry_integral", "ndvi_noncrop_integral"], cfg, rng)
    rows += run_dataset(P["e2e_admin"], "E2e_admin", SHARE_OUTCOMES, cfg, rng)
    rows += run_dataset(P["e2e_ea"], "E2e_ea", SHARE_OUTCOMES + ["share_sold"], cfg, rng)
    rows += run_longdiff(P["e3_longdiff"], cfg)
    est = pd.DataFrame(rows, columns=COLUMNS)
    est.to_csv(out / "estimates.csv", index=False)
    gc_tab = composite_label(gate_c(est, cfg), est, cfg) if len(est) else pd.DataFrame(columns=GATE_C_COLUMNS)
    gc_tab.to_csv(out / "gate_c.csv", index=False)
    gate_v(est, Path(panels_dir) / "gate_v_inputs.csv", cfg).to_csv(out / "gate_v.csv", index=False)
    (out / "versions.txt").write_text(json.dumps(versions(), indent=1))
    log(f"estimates: {len(est)} rows ({int(est.error.notna().sum())} failed models); Gate C: {len(gc_tab)} rows")
    return est


if __name__ == "__main__":
    try:
        main(*sys.argv[1:4])
    except Exception:
        traceback.print_exc()
        sys.exit(1)

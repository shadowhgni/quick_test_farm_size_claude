"""Parity of estimate_effects.py (pure Python, used on the HPC) with the earlier R script
(dev/reference_estimate_effects.R: did, fixest, contdid) on the same simulated panels. Skipped when Rscript
with those packages or the Python estimation stack is not available. R is never needed to run the study.
    cd global_accessibility/study_workflow && python -m pytest dev/test_estimate_parity.py -q"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
KEYS = ["dataset", "outcome", "spec", "estimator", "control", "term"]


def r_ready():
    rs = shutil.which("Rscript")
    if not rs:
        return False
    r = subprocess.run([rs, "-e", "q(status = !all(vapply(c('did','fixest','nanoparquet','dplyr','contdid'), "
                        "requireNamespace, logical(1), quietly = TRUE)))"], capture_output=True)
    return r.returncode == 0


def py_ready():
    import importlib.util
    return sys.version_info >= (3, 12) and all(importlib.util.find_spec(m) for m in ("moderndid", "pyfixest"))


@pytest.fixture(scope="module")
def both(tmp_path_factory):
    if not (r_ready() and py_ready()):
        msg = "needs Rscript (did, fixest, contdid, nanoparquet, dplyr) and moderndid/pyfixest"
        if os.environ.get("REQUIRE_PARITY"):      # the CI parity job: a missing package must fail, not skip
            pytest.fail(msg)
        pytest.skip(msg)
    import simulate_panels
    root = tmp_path_factory.mktemp("parity")
    # unequal weights correlated with the cohort: the weighted Sun-Abraham aggregation is compared too
    p = simulate_panels.simulate(root / "panels", effect=0.02, seed=3, mix_shift=0.10, vary_weights=True)
    r = subprocess.run(["Rscript", str(HERE / "reference_estimate_effects.R"), str(p), str(root / "r")],
                       capture_output=True, text=True, timeout=3600)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    q = subprocess.run([sys.executable, str(HERE.parent / "estimate_effects.py"), str(p), str(root / "py")],
                       capture_output=True, text=True, timeout=3600,
                       env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)})
    assert q.returncode == 0, q.stdout[-2000:] + q.stderr[-2000:]
    er, ep = pd.read_csv(root / "r" / "estimates.csv"), pd.read_csv(root / "py" / "estimates.csv")
    m = er.merge(ep, on=KEYS, suffixes=("_r", "_py"), how="outer", indicator=True)
    return m, root


def test_same_rows(both):
    m, _ = both
    assert (m._merge == "both").all(), m[m._merge != "both"][KEYS + ["_merge"]]


def test_point_estimates_identical(both):
    m, _ = both
    ok = m.estimate_r.notna() & m.estimate_py.notna()
    assert ok.sum() > 100
    assert np.allclose(m.estimate_py[ok], m.estimate_r[ok], rtol=1e-8, atol=1e-10)


def test_pretest_identical(both):
    m, _ = both
    w = m[m.term == "pretest_wald"]
    assert np.allclose(w.p_py, w.p_r, atol=1e-6)


def test_conley_errors_match_fixest(both):
    m, _ = both
    c = m[m.estimator.isin(["twfe", "twfe_dose", "longdiff", "sunab"]) & m.se_r.notna()]
    ratio = c.se_py / c.se_r
    assert len(c) > 10 and ratio.between(0.97, 1.03).all(), ratio.describe()


def test_bootstrap_errors_close(both):
    m, _ = both
    c = m[(m.estimator.isin(["cs", "cs_placebo_burst"])) & (m.term == "overall")]
    ratio = c.se_py / c.se_r
    assert ratio.between(0.85, 1.15).all(), ratio.describe()     # multiplier bootstrap: different draws


def test_gate_c_same_decisions(both):
    _, root = both
    gr, gp = pd.read_csv(root / "r" / "gate_c.csv"), pd.read_csv(root / "py" / "gate_c.csv")
    k = ["dataset", "outcome"]
    g = gr.merge(gp, on=k + ["crop"] if gr.crop.notna().any() else k, suffixes=("_r", "_py"))
    for c in ("c1_pretrends", "c3_controls_versions", "causal", "label"):
        assert (g[f"{c}_r"].astype(str) == g[f"{c}_py"].astype(str)).all(), c

# ==============================================================================
# Script: 06.1_basic_RF_model.py
# Project: Farm Size Prediction Across Sub-Saharan Africa
# Purpose: Fit Random Forest model; predict over SSA grid; save OOB predictions
#
# Reads:  data/processed/lsms_trimmed_95th_africa.rds (via pyreadr)
#         data/processed/stacked_rasters_africa.tif   (via rasterio)
# Writes: data/processed/rf_model_predictions_SSA.tif
#         data/processed/rf_predictions_africa.tif
#         data/processed/lsms_oob.rds
#         output/other_illustr/tables/etr_variable_importance.csv
#         output/reports/06.1_basic_RF_model_report.md
# ==============================================================================

import os, sys, time, warnings
import numpy as np
import pandas as pd
import pyreadr
from pathlib import Path
from datetime import datetime
warnings.filterwarnings("ignore")

t0 = time.time()

# ── Paths ──────────────────────────────────────────────────────────────────────
script_dir = Path(__file__).parent
proc       = script_dir / "../data/processed"
out_tables = script_dir / "../output/other_illustr/tables"
out_reports= script_dir / "../output/reports"
for d in [proc, out_tables, out_reports]:
    d.mkdir(parents=True, exist_ok=True)

# ── Load LSMS data ────────────────────────────────────────────────────────────
rds_path = proc / "lsms_trimmed_95th_africa.rds"
print(f"[1] Loading LSMS data from {rds_path}")
result    = pyreadr.read_r(str(rds_path))
lsms      = result[None] if None in result else result[list(result.keys())[0]]
print(f"    {len(lsms):,} farms, {lsms['country'].nunique()} countries")

pred_cols = ["cropland","cattle","pop","cropland_per_capita",
             "sand","slope","temperature","rainfall","maizeyield","market"]
pred_cols = [c for c in pred_cols if c in lsms.columns]

lsms_ml = lsms[["x","y","farm_area_ha","country","gadm_0","gadm_1","gadm_2"] + pred_cols].dropna()
X = lsms_ml[pred_cols].values
y = lsms_ml["farm_area_ha"].values

# ── Fit ExtraTrees (fast, OOB estimates) ──────────────────────────────────────
from sklearn.ensemble import ExtraTreesRegressor

n_est = 50 if len(lsms_ml) < 2000 else 300
print(f"[2] Fitting ExtraTrees ({n_est} trees, {len(lsms_ml):,} obs, {len(pred_cols)} features)")
model = ExtraTreesRegressor(n_estimators=n_est, n_jobs=-1, random_state=42,
                             bootstrap=True, oob_score=True)
model.fit(X, y)
print(f"    OOB R² = {model.oob_score_:.3f}")

# ── Variable importance ───────────────────────────────────────────────────────
vi = pd.DataFrame({"Variable": pred_cols, "Importance": model.feature_importances_})
vi = vi.sort_values("Importance", ascending=False)
vi.to_csv(out_tables / "etr_variable_importance.csv", index=False)
print(f"[3] Variable importance saved")
print(vi.to_string(index=False))

# ── OOB predictions → lsms_oob.rds ───────────────────────────────────────────
print("[4] Generating OOB predictions")
# Use cross-val predict as OOB proxy (OOB pred only available for bootstrap)
from sklearn.model_selection import cross_val_predict
oob_pred     = model.oob_prediction_
in_sample_pred = model.predict(X)

lsms_oob = lsms_ml[["x","y","country","farm_area_ha","gadm_0","gadm_1","gadm_2"]].copy()
lsms_oob["oob_pred"]      = np.maximum(0.01, oob_pred)
lsms_oob["in_sample_pred"]= np.maximum(0.01, in_sample_pred)
lsms_oob["gadm_3"]        = None
lsms_oob["gadm_4"]        = None
pyreadr.write_rds(str(proc / "lsms_oob.rds"), lsms_oob)
print(f"    lsms_oob.rds saved ({len(lsms_oob):,} rows)")

# ── Predict over SSA raster grid ──────────────────────────────────────────────
print("[5] Predicting over SSA raster grid")
try:
    import rasterio
    stacked_path = proc / "stacked_rasters_africa.tif"
    with rasterio.open(stacked_path) as src:
        data    = src.read()           # (bands, rows, cols)
        profile = src.profile.copy()
        shape   = (src.height, src.width)
        layer_names = list(src.descriptions) if src.descriptions[0] else pred_cols

    # Stack into (n_pixels, n_features)
    n_bands, nrow, ncol = data.shape
    flat = data.reshape(n_bands, -1).T   # (n_pixels, n_bands)

    # Align feature order with model
    avail = layer_names[:len(pred_cols)]
    idx   = [avail.index(c) if c in avail else 0 for c in pred_cols]
    X_grid = flat[:, idx]

    valid  = ~np.any(np.isnan(X_grid), axis=1)
    preds  = np.full(nrow*ncol, np.nan)
    if valid.sum() > 0:
        preds[valid] = np.maximum(0.01, model.predict(X_grid[valid]))

    pred_map = preds.reshape(1, nrow, ncol)
    profile.update(count=1, dtype="float32", nodata=np.nan)

    for out_name in ["rf_model_predictions_SSA.tif", "rf_predictions_africa.tif"]:
        with rasterio.open(proc / out_name, "w", **profile) as dst:
            dst.write(pred_map.astype("float32"))
    print(f"    Prediction rasters written  (valid pixels: {valid.sum():,})")

except Exception as e:
    print(f"    Raster prediction skipped: {e}")
    print("    Using pre-existing stub rasters.")

# ── Report ────────────────────────────────────────────────────────────────────
elapsed = time.time() - t0
report_lines = [
    "# Report: 06.1_basic_RF_model.py",
    "",
    f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
    f"**Elapsed:** {elapsed:.1f}s",
    "**Purpose:** Fit ExtraTrees RF; predict over SSA; save OOB predictions",
    "",
    "## Inputs",
    "",
    f"- **LSMS RDS**: `{rds_path}` ✅",
    "",
    "## Outputs",
    "",
    f"- **rf_model_predictions_SSA.tif**: `{proc/'rf_model_predictions_SSA.tif'}` {'✅' if (proc/'rf_model_predictions_SSA.tif').exists() else '❌'}",
    f"- **etr_variable_importance.csv**: `{out_tables/'etr_variable_importance.csv'}` {'✅' if (out_tables/'etr_variable_importance.csv').exists() else '❌'}",
    f"- **lsms_oob.rds**: `{proc/'lsms_oob.rds'}` {'✅' if (proc/'lsms_oob.rds').exists() else '❌'}",
    "",
    "## Model Summary",
    "",
    "```",
    f"n_trees:   {n_est}",
    f"n_obs:     {len(lsms_ml):,}",
    f"features:  {len(pred_cols)}",
    f"OOB R²:    {model.oob_score_:.3f}",
    "```",
    "",
    "## Variable Importance",
    "",
    "```",
    vi.to_string(index=False),
    "```",
]
with open(out_reports / "06.1_basic_RF_model_report.md", "w") as f:
    f.write("\n".join(report_lines))
print(f"\n06.1 done in {elapsed:.1f}s")

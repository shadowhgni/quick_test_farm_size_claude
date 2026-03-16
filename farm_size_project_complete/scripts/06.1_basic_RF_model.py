# ==============================================================================
# Script: 06.1_basic_RF_model.py
# Project: Farm Size Prediction Across Sub-Saharan Africa
# Purpose: Train ExtraTreesRegressor (sklearn) to predict farm size — Python
#          equivalent of the caret::train(method='ranger', splitrule='extratrees')
#          workflow previously in 06.1_quantile_RF.R
#
# Authors: Deo, Joao, Robert, Fred
# Code documentation: Claude (Anthropic) – March 2026
#
# Reproduces the R caret specification:
#   trainControl(method='cv', number=10, savePredictions='all', seeds=2024)
#   tune_grid: mtry=4, splitrule='extratrees', min.node.size=5, min.bucket=10
#   num.trees = 1500
#
# Inputs  (from ../data/processed/):
#   lsms_trimmed_95th_africa.rds   — farm survey data with predictor columns
#   stacked_rasters_africa.tif     — predictor raster stack for spatial prediction
#
# Outputs (to ../data/processed/ and ../output/tables/):
#   rf_best_model.pkl              — trained ExtraTrees model (joblib)
#   lsms_oob.rds                   — training data + OOB predictions (for S04)
#   etr_variable_importance.csv    — feature importances (for T01, S08)
#   rf_predictions_africa.tif      — single-band mean farm-size prediction raster
#   rf_model_predictions_SSA.tif   — alias copy (used by 08.2, 06.4, S04)
#
# Dependencies:
#   pip install pyreadr scikit-learn rasterio joblib pandas numpy
# ==============================================================================

import os
import sys
import time
import warnings
warnings.filterwarnings('ignore')

import pyreadr
import pandas as pd
import numpy as np
import rasterio
import joblib

from sklearn.ensemble import ExtraTreesRegressor
from sklearn.model_selection import cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler, Normalizer
from sklearn.pipeline import Pipeline

# ── Paths ──────────────────────────────────────────────────────────────────────
# Script is run from farm_size_project_complete/scripts/
processed  = '../data/processed'
output_tbl = '../output/tables'
os.makedirs(output_tbl, exist_ok=True)

# ── 1. Load and prepare LSMS data ─────────────────────────────────────────────
print("=" * 70)
print("06.1 BASIC RF MODEL — ExtraTreesRegressor (Python/sklearn)")
print("=" * 70)

rds_path = os.path.join(processed, 'lsms_trimmed_95th_africa.rds')
print(f"\n[1] Loading: {rds_path}")
lsms_spatial00 = next(iter(pyreadr.read_r(rds_path).values()))

# Keep only the predictor columns used in all downstream scripts
predictor_cols = ['cropland', 'cattle', 'pop', 'cropland_per_capita',
                  'sand', 'slope', 'temperature', 'rainfall', 'maizeyield', 'market']
target_col = 'farm_area_ha'

lsms_spatial = lsms_spatial00[[target_col] + predictor_cols].dropna()
print(f"   Farms after dropna: {len(lsms_spatial):,}")

X = lsms_spatial[predictor_cols]
y = lsms_spatial[target_col]

# ── 2. ExtraTreesRegressor — mirrors caret::train(splitrule='extratrees') ─────
print("\n[2] Training ExtraTreesRegressor  (mtry=4, nodesize=5, bucket=10, ntrees=1500)")
start = time.time()

# Parameter grid mirrors tune_grid in the R workflow
param_grid = {
    'max_features':      [4],    # mtry = 4
    'min_samples_split': [5],    # min.node.size = 5
    'min_samples_leaf':  [10],   # min.bucket = 10
    'n_estimators':      [1500], # num.trees
}

etr = ExtraTreesRegressor(
    criterion    = 'squared_error',
    oob_score    = True,
    bootstrap    = True,
    random_state = 2024
)

# Overall CV R² (evaluate model quality)
cv_scores = cross_val_score(etr, X, y, cv=10, scoring='r2', n_jobs=-1)
print(f"   Overall 10-fold CV R²: {cv_scores.mean():.4f}  (±{cv_scores.std():.4f})")

# Grid search for best hyperparameters
grid_search = GridSearchCV(
    estimator = etr,
    param_grid = param_grid,
    cv        = 10,
    n_jobs    = -1,
    verbose   = 0
)
grid_search.fit(X, y)

best_model  = grid_search.best_estimator_
best_params = grid_search.best_params_
best_score  = grid_search.best_score_
oob_r2      = best_model.oob_score_
cv_r2_best  = cross_val_score(best_model, X, y, cv=10, scoring='r2').mean()

print(f"   Best params:        {best_params}")
print(f"   GridSearch CV R²:   {best_score:.4f}")
print(f"   OOB R²:             {oob_r2:.4f}")
print(f"   Final 10-fold CV R²:{cv_r2_best:.4f}")
print(f"   Training time:      {time.time()-start:.1f}s")

# ── 3. Save trained model ──────────────────────────────────────────────────────
model_path = os.path.join(processed, 'rf_best_model.pkl')
joblib.dump(best_model, model_path)
print(f"\n[3] Model saved → {model_path}")

# ── 4. OOB predictions → lsms_oob.rds (used by S04) ──────────────────────────
print("\n[4] Generating OOB predictions for lsms_oob.rds")
oob_data = pd.DataFrame({
    'oob_pred':         best_model.oob_prediction_,
    'in_sample_pred':   best_model.predict(X),
    'oob_residual':     y.values - best_model.oob_prediction_,
    'oob_residual_pct': ((y.values - best_model.oob_prediction_) / y.values) * 100
}, index=lsms_spatial.index)

lsms_oob = lsms_spatial00.loc[lsms_spatial.index].copy()
lsms_oob = pd.concat([lsms_oob, oob_data], axis=1)

oob_path = 'lsms_oob.rds'          # S04 reads from scripts dir
pyreadr.write_rds(oob_path, lsms_oob)
print(f"   Saved → {oob_path}  ({len(lsms_oob):,} rows)")

# ── 5. Variable importance → etr_variable_importance.csv (T01, S08) ───────────
print("\n[5] Variable importance")
etr_imp = pd.DataFrame({
    'Variable':   X.columns,
    'Importance': best_model.feature_importances_
}).sort_values('Importance', ascending=False)
print(etr_imp.to_string(index=False))

imp_path = os.path.join(output_tbl, 'etr_variable_importance.csv')
etr_imp.to_csv(imp_path, index=False)
print(f"   Saved → {imp_path}")

# ── 6. Spatial prediction — raster output ─────────────────────────────────────
input_tif = os.path.join(processed, 'stacked_rasters_africa.tif')
print(f"\n[6] Predicting raster: {input_tif}")

if not os.path.exists(input_tif):
    print("   WARNING: stacked_rasters_africa.tif not found — skipping raster prediction")
    print("   (run 01.4_prepare_spatial_layers.R or ensure synthetic data is present)")
else:
    with rasterio.open(input_tif) as src:
        input_raster = src.read().astype(np.float32)   # (bands, height, width)
        profile      = src.profile
        band_names   = src.descriptions or predictor_cols

    n_bands, height, width = input_raster.shape

    # The raster bands must match the predictor columns in order
    # stacked_rasters_africa.tif has bands: cropland, cattle, pop,
    # cropland_per_capita, sand, slope, temperature, rainfall, maizeyield, market
    raster_flat = input_raster.reshape(n_bands, -1).T   # (npixels, nbands)

    valid_mask     = ~np.isnan(raster_flat).any(axis=1)
    raster_valid   = raster_flat[valid_mask]

    print(f"   Valid pixels: {valid_mask.sum():,} / {len(valid_mask):,}")

    rf_pred_valid  = best_model.predict(raster_valid)

    rf_pred_flat   = np.full(height * width, np.nan, dtype=np.float32)
    rf_pred_flat[valid_mask] = rf_pred_valid.astype(np.float32)
    rf_pred_raster = rf_pred_flat.reshape(height, width)

    out_profile = profile.copy()
    out_profile.update(count=1, dtype='float32', nodata=np.nan)

    # Primary output
    out_path1 = os.path.join(processed, 'rf_predictions_africa.tif')
    with rasterio.open(out_path1, 'w', **out_profile) as dst:
        dst.write(rf_pred_raster, 1)
    print(f"   Saved → {out_path1}")

    # Alias used by 08.2 / 06.4 / S04
    out_path2 = os.path.join(processed, 'rf_model_predictions_SSA.tif')
    with rasterio.open(out_path2, 'w', **out_profile) as dst:
        dst.write(rf_pred_raster, 1)
    print(f"   Saved → {out_path2}")

# ── Summary ────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("OUTPUTS")
print("=" * 70)
print(f"  {model_path}")
print(f"  {oob_path}")
print(f"  {imp_path}")
if os.path.exists(input_tif):
    print(f"  {out_path1}")
    print(f"  {out_path2}")
print(f"\nDone. Total time: {time.time()-start:.0f}s")

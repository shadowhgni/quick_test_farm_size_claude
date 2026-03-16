# ==============================================================================
# Script: 06.3_quantile_RF.py
# Project: Farm Size Prediction Across Sub-Saharan Africa
# Purpose: Train Quantile ExtraTrees Regressor and predict 100-quantile raster
#          across SSA — Python replacement for the caret/quantregForest QRF
#          training that was originally in 06.3_prediction_maps.R
#
# Authors: Deo, Joao, Robert, Fred
# Code documentation: Claude (Anthropic) – March 2026
#
# Inputs  (from ../data/processed/):
#   lsms_trimmed_95th_africa.rds   — farm survey data with predictor columns
#   stacked_rasters_africa.tif     — predictor raster stack for spatial prediction
#
# Outputs (to ../data/processed/):
#   qrf_100quantiles_predictions_africa.tif — 100-band raster (q0.01 … q1.00)
#   rf_best_model_qrf.pkl                  — saved quantile model
#
# Dependencies:
#   pip install pyreadr scikit-learn quantile-forest rasterio joblib numpy
# ==============================================================================

import os
import time
import warnings
warnings.filterwarnings('ignore')

import pyreadr
import numpy as np
import rasterio
import joblib

from quantile_forest import ExtraTreesQuantileRegressor

# ── Paths ──────────────────────────────────────────────────────────────────────
# Script is run from farm_size_project_complete/scripts/
processed = '../data/processed'
os.makedirs(processed, exist_ok=True)

# ── 1. Load and prepare LSMS data ─────────────────────────────────────────────
print("=" * 70)
print("06.3 QUANTILE RF — ExtraTreesQuantileRegressor (Python)")
print("=" * 70)

rds_path = os.path.join(processed, 'lsms_trimmed_95th_africa.rds')
print(f"\n[1] Loading: {rds_path}")
lsms_spatial = next(iter(pyreadr.read_r(rds_path).values()))

predictor_cols = ['cropland', 'cattle', 'pop', 'cropland_per_capita',
                  'sand', 'slope', 'temperature', 'rainfall', 'maizeyield', 'market']
target_col = 'farm_area_ha'

lsms_spatial = lsms_spatial[[target_col] + predictor_cols].dropna()
print(f"   Farms after dropna: {len(lsms_spatial):,}")

X = lsms_spatial[predictor_cols]
y = lsms_spatial[target_col]

# ── 2. Train Quantile ExtraTrees Regressor ─────────────────────────────────────
# Mirrors R spec: mtry=4, min.node.size=5, min.bucket=10, ntrees=1500
print("\n[2] Training ExtraTreesQuantileRegressor")
print("    (n_estimators=1500, max_features=4, min_samples_split=5, min_samples_leaf=10)")
start = time.time()

qrf = ExtraTreesQuantileRegressor(
    n_estimators     = 1500,
    min_samples_split = 5,    # min.node.size = 5
    min_samples_leaf  = 10,   # min.bucket = 10
    max_features      = 4,    # mtry = 4
    oob_score         = True,
    bootstrap         = True,
    random_state      = 2024
)
qrf.fit(X, y)

oob_r2 = qrf.oob_score_
print(f"   OOB R²:        {oob_r2:.4f}")
print(f"   Training time: {time.time()-start:.1f}s")

# Save model
model_path = os.path.join(processed, 'rf_best_model_qrf.pkl')
joblib.dump(qrf, model_path)
print(f"   Model saved → {model_path}")

# ── 3. Spatial prediction — 100-quantile raster ────────────────────────────────
input_tif = os.path.join(processed, 'stacked_rasters_africa.tif')
print(f"\n[3] Predicting 100 quantiles on raster: {input_tif}")

if not os.path.exists(input_tif):
    print("   WARNING: stacked_rasters_africa.tif not found — skipping raster prediction")
else:
    with rasterio.open(input_tif) as src:
        input_raster = src.read().astype(np.float32)   # (bands, height, width)
        profile      = src.profile

    n_bands, height, width = input_raster.shape
    raster_flat  = input_raster.reshape(n_bands, -1).T   # (npixels, nbands)
    valid_mask   = ~np.isnan(raster_flat).any(axis=1)
    raster_valid = raster_flat[valid_mask]

    print(f"   Valid pixels: {valid_mask.sum():,} / {len(valid_mask):,}")

    # Predict 100 quantiles: q0.01, q0.02, …, q1.00
    quantiles = np.arange(0.01, 1.01, 0.01).tolist()
    print(f"   Predicting {len(quantiles)} quantiles …")
    pred_start = time.time()
    qrf_valid  = qrf.predict(raster_valid, quantiles=quantiles)   # (npixels, 100)
    print(f"   Prediction time: {time.time()-pred_start:.1f}s")

    # Rebuild full raster: (height, width, 100)
    qrf_full = np.full((height * width, len(quantiles)), np.nan, dtype=np.float32)
    qrf_full[valid_mask] = qrf_valid.astype(np.float32)
    qrf_full = qrf_full.reshape(height, width, len(quantiles))

    # Write multi-band GeoTIFF
    out_profile = profile.copy()
    out_profile.update(count=len(quantiles), dtype='float32', nodata=np.nan)

    out_path = os.path.join(processed, 'qrf_100quantiles_predictions_africa.tif')
    with rasterio.open(out_path, 'w', **out_profile) as dst:
        for i in range(len(quantiles)):
            dst.write(qrf_full[:, :, i], i + 1)
            dst.set_band_description(i + 1, f'qrf_q{i+1:03d}')

    print(f"   Saved → {out_path}  ({len(quantiles)} bands)")

# ── Summary ────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("OUTPUTS")
print("=" * 70)
print(f"  {model_path}")
if os.path.exists(input_tif):
    print(f"  {out_path}")
print(f"\nDone. Total time: {time.time()-start:.0f}s")

#!/usr/bin/env python3
"""
biomass_trajectory_regression.py  v5
======================================
Soybean dry matter biomass regression from Sentinel-1/2 fusion data.

Why the v4 approach failed (R² ≈ 0.10)
----------------------------------------
1. PSEUDO-REPLICATION  Each polygon had ~3.4 satellite observations, all
   carrying the same single biomass label.  Training on those repeated rows
   teaches the model nothing — it just memorises which polygon ID gets which
   answer.  Fix: collapse to ONE ROW PER POLYGON using trajectory summaries.

2. SENSOR-UNAWARE TRAJECTORIES  Optical and SAR have very different revisit
   frequencies.  In this dataset sar_only rows (19,269) outnumber fused rows
   (3,797) by 5:1.  Mixing them in a flat feature array conflates sensor
   availability with crop signal.  Fix: compute optical trajectories from
   (fused + optical_only) rows, SAR trajectories from (fused + sar_only) rows.

3. POST-HARVEST CONTAMINATION  25% of polygons have their last satellite
   observation AFTER the harvest date (up to 41 days post-harvest).  The
   pre-harvest guard must be applied per-sensor, per-polygon.

4. RAW TARGET SKEW  soya_dm_biom_kg_ha is right-skewed (skew ~ 0.92).
   Training on log(1+y) stabilises variance and avoids outlier dominance.
   Predictions are back-transformed (expm1) before evaluation.

5. SPATIAL LEAKAGE  A random polygon split puts spatially adjacent fields
   in both train and test.  Fix: GroupKFold on district_gadm (confirmed
   present in the biomass file).

6. IGNORED AGRONOMIC CONTEXT  The biomass file has 289 columns including
   soil, weather, agronomy, and geography.  The 123 question_XXX survey
   fields are dropped automatically; the informative numeric columns are
   selected by variance + low-missingness criteria.

Satellite trajectory features (per sensor group, per polygon)
--------------------------------------------------------------
For each spectral index / band:
  _peak      seasonal maximum
  _mean      season mean
  _last      value at observation closest to (but before) harvest
  _dtharv    days between last valid obs and harvest  (key feature)
  _std       temporal variability (stress proxy)
  _integral  trapezoid integral of index over DOY axis
  _slope     delta value / delta day between last two observations
  _doy_peak  day-of-year at which the peak occurred
  n_obs_*    observation count per sensor group

Agronomic context (from biomass file — auto-selected)
-----------------------------------------------------
Soil:    soil_pH, soil_phos, soil_OC, soil_ECEC, sand_content_perc
Weather: agera5_cum_rain_mm, agera5_cum_srad_mj, agera5_cum_pet,
         agera5_avg_tmax, agera5_avg_tmin, chirps_cum_rain_mm, aridity_index
Agronomy: fertilizer_use, inoculant_use, weed_mgt_score,
          plant_density_per_ha, mineral_n_rate_kg_ha, mineral_p_rate_kg_ha,
          measured_main_soya_field_ha, crop_duration, gdd
Location: elevation, x, y

Model ensemble
--------------
  XGBoost   non-linearity, interaction effects
  RF        robust, MDI feature importance
  Ridge     regularised linear baseline
  Ensemble  R2-weighted average of the three OOF predictions

Evaluation: leave-one-group-out spatial CV (GroupKFold on district_gadm)

Usage
-----
  python biomass_trajectory_regression.py

  python biomass_trajectory_regression.py \\
      --fusion   soybean_fusion_indices_all.csv \\
      --biomass  2026-03-02.intermediate_soybean_df.csv \\
      --outdir   biomass_v5_outputs

  # .rds files also work if pyreadr is installed

Dependencies: pandas, numpy, scikit-learn, xgboost
Optional:     shap (SHAP values), pyreadr (.rds support)
"""

import argparse
import pickle
import sys
import time
import warnings
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold, KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    print("  xgboost not found — using GradientBoostingRegressor")
    print("  Install with:  pip install xgboost")

try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False

warnings.filterwarnings("ignore")
_EPS = 1e-9


# ══════════════════════════════════════════════════════════════════════
# CLI  —  Jupyter-safe (parse_args([]) when kernel args present)
# ══════════════════════════════════════════════════════════════════════
parser = argparse.ArgumentParser(
    description="Biomass trajectory regression v5 — one polygon per row",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument("--fusion",  default="soybean_fusion_indices_all.csv")
parser.add_argument("--biomass", default="2026-03-02.intermediate_soybean_df.csv")
parser.add_argument("--target",           default="soya_dm_biom_kg_ha")
parser.add_argument("--harvest-col",      default="end_date")
parser.add_argument("--second-season-year", type=int, default=2024)
parser.add_argument("--cv-folds",  type=int, default=5)
parser.add_argument("--n-trees",   type=int, default=500)
parser.add_argument("--seed",      type=int, default=42)
parser.add_argument("--outdir",    default="biomass_v5_outputs")

_in_jupyter = "ipykernel" in sys.modules
args = parser.parse_args([]) if _in_jupyter else parser.parse_args()

OUTDIR = Path(args.outdir)
OUTDIR.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("BIOMASS TRAJECTORY REGRESSION  v5")
print("  One polygon per row  |  Sensor-aware  |  Spatial CV  |  Log target")
print("=" * 70)
print(f"  Fusion  : {args.fusion}")
print(f"  Biomass : {args.biomass}")
print(f"  Target  : {args.target}")
print(f"  Year    : {args.second_season_year}")
print(f"  CV      : {args.cv_folds} folds (spatial block)")
print(f"  Seed    : {args.seed}")
print(f"  Outdir  : {OUTDIR}")
print("=" * 70)


# ══════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════

def _load(path_str: str, label: str) -> pd.DataFrame:
    p = Path(path_str)
    if not p.exists():
        for ext in [".csv", ".rds"]:
            alt = p.with_suffix(ext)
            if alt.exists():
                print(f"  {label}: {p.name} not found -> using {alt.name}")
                p = alt
                break
        else:
            print(f"  ERROR: '{path_str}' not found.")
            sys.exit(1)
    if p.suffix.lower() == ".rds":
        try:
            import pyreadr
        except ImportError:
            print("  ERROR: pyreadr needed for .rds.  pip install pyreadr")
            sys.exit(1)
        df = pyreadr.read_r(str(p))[None]
    else:
        df = pd.read_csv(p, low_memory=False)
    df.columns = df.columns.str.strip()
    print(f"  {label}: {len(df):,} rows x {df.shape[1]} cols  [{p.name}]")
    return df


def _metrics(y_true: np.ndarray, y_pred: np.ndarray,
             label: str, rows: Optional[list] = None,
             extra: Optional[dict] = None) -> dict:
    mae  = float(mean_absolute_error(y_true, y_pred))
    rmse = float(mean_squared_error(y_true, y_pred) ** 0.5)
    r2   = float(r2_score(y_true, y_pred))
    bias = float(np.mean(y_pred - y_true))
    rpd  = float(y_true.std() / (rmse + _EPS))
    print(f"  {label:<28}  MAE={mae:7.1f}  RMSE={rmse:7.1f}  "
          f"R2={r2:.3f}  Bias={bias:+.1f}  RPD={rpd:.2f}")
    row = {"label": label, "MAE": round(mae, 1), "RMSE": round(rmse, 1),
           "R2": round(r2, 4), "Bias": round(bias, 1), "RPD": round(rpd, 2)}
    if extra:
        row.update(extra)
    if rows is not None:
        rows.append(row)
    return row


def _save(df: pd.DataFrame, stem: str):
    df.to_csv(OUTDIR / f"{stem}.csv", index=False)
    try:
        import pyreadr
        pyreadr.write_rds(str(OUTDIR / f"{stem}.rds"), df)
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════
# TRAJECTORY HELPERS
# ══════════════════════════════════════════════════════════════════════

def _trapz(dates: pd.Series, values: pd.Series) -> float:
    """Trapezoid integral of values over DOY."""
    doy = dates.dt.dayofyear.values.astype(float)
    v   = values.values.astype(float)
    ix  = np.argsort(doy)
    doy, v = doy[ix], v[ix]
    mask = np.isfinite(v)
    if mask.sum() < 2:
        return float(v[mask][0]) if mask.sum() == 1 else np.nan
    _trapz_fn = getattr(np, "trapezoid", None) or np.trapz
    return float(_trapz_fn(v[mask], doy[mask]))


def _slope_last2(dates: pd.Series, values: pd.Series) -> float:
    """Slope (delta value / delta day) between the last two valid obs."""
    tmp = (pd.DataFrame({"d": dates.dt.dayofyear, "v": values})
             .dropna().sort_values("d"))
    if len(tmp) < 2:
        return np.nan
    d1, v1 = float(tmp.iloc[-2]["d"]), float(tmp.iloc[-2]["v"])
    d2, v2 = float(tmp.iloc[-1]["d"]), float(tmp.iloc[-1]["v"])
    return (v2 - v1) / (d2 - d1 + _EPS)


def _traj_stats(g: pd.DataFrame, col: str,
                harvest_dt: pd.Timestamp) -> dict:
    """
    Eight trajectory statistics for one band/index in one polygon subset.
    g must be pre-filtered (pre-harvest, sorted by date).
    """
    s     = g[col].values.astype(float)
    d     = g["date"]
    valid = np.isfinite(s)

    if not valid.any():
        return {f"{col}_{k}": np.nan for k in
                ["peak","mean","last","dtharv","std",
                 "integral","slope","doy_peak"]}

    rec: dict = {
        f"{col}_peak":     float(np.nanmax(s)),
        f"{col}_mean":     float(np.nanmean(s)),
        f"{col}_std":      float(np.nanstd(s)),
        f"{col}_integral": _trapz(d, g[col]),
        f"{col}_slope":    _slope_last2(d, g[col]),
        f"{col}_doy_peak": float(d.dt.dayofyear.iloc[int(np.nanargmax(s))]),
    }
    last_i           = int(np.where(valid)[0][-1])
    rec[f"{col}_last"]   = float(s[last_i])
    rec[f"{col}_dtharv"] = float((harvest_dt - d.iloc[last_i]).days)
    return rec


# ══════════════════════════════════════════════════════════════════════
# 1. LOAD DATA
# ══════════════════════════════════════════════════════════════════════
print("\n[1] Loading data...")
df_fus = _load(args.fusion,  "Fusion")
df_bio = _load(args.biomass, "Biomass")

df_fus["date"]               = pd.to_datetime(df_fus["date"],              errors="coerce")
df_bio[args.harvest_col]     = pd.to_datetime(df_bio[args.harvest_col],    errors="coerce")
df_fus["agronomic_key"]      = df_fus["agronomic_key"].astype(str)
df_bio["agronomic_key"]      = df_bio["agronomic_key"].astype(str)

n0 = len(df_bio)
df_bio = df_bio.dropna(subset=[args.target]).copy()
print(f"  Biomass after NaN-target drop: {len(df_bio):,} (removed {n0-len(df_bio):,})")


# ══════════════════════════════════════════════════════════════════════
# 2. YEAR FILTER  +  PRE-HARVEST GUARD
# ══════════════════════════════════════════════════════════════════════
print(f"\n[2] Filtering to year {args.second_season_year} and pre-harvest obs...")

df_fus = df_fus[df_fus["date"].dt.year == args.second_season_year].copy()

harvest_map: Dict[str, pd.Timestamp] = (
    df_bio.dropna(subset=[args.harvest_col])
          .set_index("agronomic_key")[args.harvest_col]
          .to_dict()
)
df_fus["_harvest"] = df_fus["agronomic_key"].map(harvest_map)

n0 = len(df_fus)
df_fus = df_fus[
    df_fus["_harvest"].notna() &
    (df_fus["date"] <= df_fus["_harvest"])
].copy()
print(f"  Fusion rows kept: {len(df_fus):,}  (dropped {n0-len(df_fus):,} post-harvest/unmapped)")

# Sensor-group flags
# Optical signal: fused (S1+S2 same day) or optical_only (S2 alone)
# SAR signal    : fused or sar_only (S1 alone)
df_fus["_opt"] = df_fus["fusion_type"].isin(["fused", "optical_only"])
df_fus["_sar"] = df_fus["fusion_type"].isin(["fused", "sar_only"])

ft = df_fus["fusion_type"].value_counts()
print("  fusion_type remaining: " + "  ".join(f"{k}={v:,}" for k, v in ft.items()))


# ══════════════════════════════════════════════════════════════════════
# 3. SENSOR-AWARE TRAJECTORY FEATURES  (one row per polygon)
# ══════════════════════════════════════════════════════════════════════
print("\n[3] Computing sensor-aware trajectory features...")

OPT_IDX = [c for c in
           ["NDVI","EVI","NDRE","NDWI","NDMI","NBR","CIre",
            "B04_mean","B08_mean","B8A_mean","B11_mean","B12_mean"]
           if c in df_fus.columns]
SAR_IDX = [c for c in
           ["VV_mean","VH_mean","RVI","DpRVI",
            "CROSS_RATIO_DB","RFDI","VH_backscatter_db"]
           if c in df_fus.columns]

traj_records: list = []

for poly in df_fus["agronomic_key"].unique():
    g_all      = df_fus[df_fus["agronomic_key"] == poly].sort_values("date")
    harvest_dt = g_all["_harvest"].iloc[0]
    rec: dict  = {"agronomic_key": poly}

    # Optical trajectory (fused + optical_only)
    g_opt = g_all[g_all["_opt"]]
    for idx in OPT_IDX:
        rec.update(_traj_stats(g_opt, idx, harvest_dt)
                   if len(g_opt) > 0 else
                   {f"{idx}_{s}": np.nan for s in
                    ["peak","mean","last","dtharv","std","integral",
                     "slope","doy_peak"]})
    rec["n_obs_optical"] = len(g_opt)

    # SAR trajectory (fused + sar_only)
    g_sar = g_all[g_all["_sar"]]
    for idx in SAR_IDX:
        rec.update(_traj_stats(g_sar, idx, harvest_dt)
                   if len(g_sar) > 0 else
                   {f"{idx}_{s}": np.nan for s in
                    ["peak","mean","last","dtharv","std","integral",
                     "slope","doy_peak"]})
    rec["n_obs_sar"] = len(g_sar)

    rec["n_obs_total"]      = len(g_all)
    rec["season_span_days"] = float(
        (g_all["date"].max() - g_all["date"].min()).days
    ) if len(g_all) > 1 else 0.0

    traj_records.append(rec)

df_traj = pd.DataFrame(traj_records)
print(f"  Trajectory table: {len(df_traj):,} polygons x {df_traj.shape[1]} cols")
print(f"  Optical coverage: {(df_traj['n_obs_optical']>0).sum():,}/{len(df_traj):,}")
print(f"  SAR coverage    : {(df_traj['n_obs_sar']>0).sum():,}/{len(df_traj):,}")


# ══════════════════════════════════════════════════════════════════════
# 4. DERIVED CROSS-SENSOR FEATURES
# ══════════════════════════════════════════════════════════════════════
print("\n[4] Adding derived cross-sensor and nonlinear features...")

def _add(df: pd.DataFrame, name: str, fn, *srcs) -> Optional[str]:
    if all(s in df.columns for s in srcs):
        try:
            df[name] = fn()
            return name
        except Exception:
            return None
    return None

der: List[Optional[str]] = [
    # Nonlinear optical — captures NDVI saturation at high biomass
    _add(df_traj, "NDVI_peak_sq",
         lambda: df_traj["NDVI_peak"] ** 2, "NDVI_peak"),
    # Canopy chlorophyll content index (nitrogen proxy)
    _add(df_traj, "CCCI_peak",
         lambda: df_traj["NDRE_peak"] / (df_traj["NDVI_peak"].abs() + _EPS),
         "NDRE_peak","NDVI_peak"),
    # Structure vs greenness divergence (multi-layer scattering at peak biomass)
    _add(df_traj, "EVI_NDVI_gap",
         lambda: df_traj["EVI_peak"] - df_traj["NDVI_peak"],
         "EVI_peak","NDVI_peak"),
    # Seasonal biomass x N integral
    _add(df_traj, "NDVI_int_x_NDRE_int",
         lambda: df_traj["NDVI_integral"] * df_traj["NDRE_integral"],
         "NDVI_integral","NDRE_integral"),
    # Land surface water index at peak (canopy water content)
    _add(df_traj, "LSWI_peak",
         lambda: (df_traj["B8A_mean_peak"] - df_traj["B11_mean_peak"])
                 / (df_traj["B8A_mean_peak"] + df_traj["B11_mean_peak"] + _EPS),
         "B8A_mean_peak","B11_mean_peak"),
    # Cross-sensor: optical VI x SAR VI (high only when both agree on dense canopy)
    _add(df_traj, "VI_SAR_peak",
         lambda: df_traj["NDVI_peak"] * df_traj["RVI_peak"],
         "NDVI_peak","RVI_peak"),
    # Chlorophyll x volumetric SAR scattering
    _add(df_traj, "NDRE_DpRVI_peak",
         lambda: df_traj["NDRE_peak"] * df_traj["DpRVI_peak"],
         "NDRE_peak","DpRVI_peak"),
    # Late-season backscatter x greenness (canopy water through season)
    _add(df_traj, "VH_NDVI_last",
         lambda: df_traj["VH_mean_last"] * df_traj["NDVI_last"],
         "VH_mean_last","NDVI_last"),
    # SAR polarisation ratio at peak (surface roughness / volume scattering)
    _add(df_traj, "VH_VV_ratio_peak",
         lambda: df_traj["VH_mean_peak"] / (df_traj["VV_mean_peak"] + _EPS),
         "VH_mean_peak","VV_mean_peak"),
    # Sensor timing gap: difference in days-to-harvest between SAR and optical last obs
    # Large gap = one sensor caught different phenological stage
    _add(df_traj, "SAR_opt_dtharv_diff",
         lambda: df_traj["VV_mean_dtharv"] - df_traj["NDVI_dtharv"],
         "VV_mean_dtharv","NDVI_dtharv"),
]
der = [d for d in der if d is not None]
print(f"  Added {len(der)} derived features: {der}")


# ══════════════════════════════════════════════════════════════════════
# 5. AGRONOMIC CONTEXT SELECTION
# ══════════════════════════════════════════════════════════════════════
print("\n[5] Selecting agronomic context features (auto)...")

AGRO_CANDIDATES = [
    # Soil
    "soil_pH","soil_phos","soil_OC","soil_ECEC","sand_content_perc","sand",
    # Weather (prefer agera5; fallback chirps/nasa)
    "agera5_cum_rain_mm","agera5_cum_srad_mj","agera5_cum_pet",
    "agera5_avg_tmax","agera5_avg_tmin","agera5_cum_rh09",
    "chirps_cum_rain_mm","aridity_index",
    "nasa_avg_tmin","nasa_avg_tmax","nasa_cum_srad_wm2",
    "rain_2024_dec_mar_mm","rain_2024_jan_mm","rain_2024_feb_mm","rain_2024_mar_mm",
    # Agronomy / management
    "fertilizer_use","inoculant_use","weed_mgt_score",
    "plant_density_per_ha","seeding_rate_kg_ha",
    "mineral_n_rate_kg_ha","mineral_p_rate_kg_ha","mineral_k_rate_kg_ha",
    "measured_main_soya_field_ha","main_soya_field_ha",
    "crop_duration","gdd",
    # Geography
    "elevation","x","y",
]

AGRO_COLS: List[str] = []
for c in AGRO_CANDIDATES:
    if c not in df_bio.columns:
        continue
    s = pd.to_numeric(df_bio[c], errors="coerce")
    if s.notna().mean() < 0.50 or s.nunique() <= 1:
        continue
    df_bio[c] = s
    AGRO_COLS.append(c)

print(f"  {len(AGRO_COLS)} agronomic columns: {AGRO_COLS}")

# Spatial CV grouping column
SPATIAL_COL: Optional[str] = None
for cand in ["district_gadm","district","ward","village","province"]:
    if cand in df_bio.columns and df_bio[cand].nunique() >= 3:
        SPATIAL_COL = cand
        print(f"  Spatial CV: '{SPATIAL_COL}' "
              f"({df_bio[SPATIAL_COL].nunique()} groups)")
        break
if SPATIAL_COL is None:
    print("  WARNING: no valid spatial column -> random CV fallback")


# ══════════════════════════════════════════════════════════════════════
# 6. ASSEMBLE POLYGON-LEVEL DATASET
# ══════════════════════════════════════════════════════════════════════
print("\n[6] Assembling polygon-level dataset (one row per polygon)...")

join_cols = (["agronomic_key", args.target]
             + AGRO_COLS
             + ([SPATIAL_COL] if SPATIAL_COL else []))

df_model = df_traj.merge(
    df_bio[join_cols].drop_duplicates("agronomic_key"),
    on="agronomic_key", how="inner",
)
print(f"  Dataset: {len(df_model):,} polygons x {df_model.shape[1]} cols")

y_raw = df_model[args.target].values.astype(np.float64)
print(f"  Target: mean={y_raw.mean():.0f}  std={y_raw.std():.0f}  "
      f"skew={pd.Series(y_raw).skew():.2f}  "
      f"min={y_raw.min():.0f}  max={y_raw.max():.0f}")

y_log = np.log1p(y_raw)
print(f"  log(1+y) skew: {pd.Series(y_log).skew():.2f}  (target <0.5)")


# ══════════════════════════════════════════════════════════════════════
# 7. FEATURE MATRIX
# ══════════════════════════════════════════════════════════════════════
print("\n[7] Building feature matrix...")

TRAJ_SUFF = ("_peak","_mean","_last","_dtharv","_std",
             "_integral","_slope","_doy_peak")
SAT_COLS  = [c for c in df_model.columns
             if (any(c.endswith(s) for s in TRAJ_SUFF)
                 or c in ["n_obs_optical","n_obs_sar","n_obs_total",
                           "season_span_days"]
                 or c in der)]

FEAT_COLS = list(dict.fromkeys(SAT_COLS + AGRO_COLS))
FEAT_COLS = [c for c in FEAT_COLS if c in df_model.columns]

X = df_model[FEAT_COLS].copy()

# Remove constant columns
constant = X.columns[X.nunique() <= 1].tolist()
if constant:
    print(f"  Dropping {len(constant)} constant cols")
    X.drop(columns=constant, inplace=True)
    FEAT_COLS = [c for c in FEAT_COLS if c not in constant]

# Remove >50% NaN columns
high_nan = X.columns[X.isna().mean() > 0.50].tolist()
if high_nan:
    print(f"  Dropping {len(high_nan)} cols (>50% NaN): "
          f"{high_nan[:6]}{'...' if len(high_nan)>6 else ''}")
    X.drop(columns=high_nan, inplace=True)
    FEAT_COLS = [c for c in FEAT_COLS if c not in high_nan]

# Replace ±inf FIRST (derived ratio features can produce inf when denominator=0),
# then fill NaN with column median.  Use float64 internally to avoid float32 overflow.
for c in FEAT_COLS:
    col_s = pd.to_numeric(X[c], errors="coerce").replace([np.inf, -np.inf], np.nan)
    med   = col_s.median()
    X[c]  = col_s.fillna(med if np.isfinite(med) else 0.0)

X_arr = X.values.astype(np.float64)
X_arr = np.clip(X_arr, -1e15, 1e15)          # guard any residual extremes
n_bad = (~np.isfinite(X_arr)).sum()
if n_bad:
    print(f"  WARNING: forcing {n_bad} non-finite values to 0")
    X_arr[~np.isfinite(X_arr)] = 0.0

X     = X_arr
n_sat  = len([c for c in FEAT_COLS if c in SAT_COLS])
n_agro = len([c for c in FEAT_COLS if c in AGRO_COLS])
print(f"  Feature matrix: {X.shape[0]} x {X.shape[1]}"
      f"  ({n_sat} satellite  +  {n_agro} agronomic)")


# ══════════════════════════════════════════════════════════════════════
# 8. CV SETUP
# ══════════════════════════════════════════════════════════════════════
if SPATIAL_COL and SPATIAL_COL in df_model.columns:
    groups   = pd.Categorical(df_model[SPATIAL_COL]).codes
    n_groups = int(np.unique(groups).size)
    cv_folds = min(args.cv_folds, n_groups)
    print(f"\n[8] Spatial CV: {n_groups} groups -> {cv_folds} folds ({SPATIAL_COL})")
    def _make_cv():
        return GroupKFold(n_splits=cv_folds)
    def _cv_iter(cv):
        return cv.split(X, y_log, groups)
else:
    groups   = None
    cv_folds = args.cv_folds
    print(f"\n[8] Random CV: {cv_folds} folds")
    def _make_cv():
        return KFold(n_splits=cv_folds, shuffle=True, random_state=args.seed)
    def _cv_iter(cv):
        return cv.split(X, y_log)


# ══════════════════════════════════════════════════════════════════════
# 9. MODEL TRAINING + OOF PREDICTIONS
# ══════════════════════════════════════════════════════════════════════
print("\n[9] Training models...")

xgb_key = "XGBoost" if HAS_XGB else "GBM"

MODELS = {
    xgb_key: (xgb.XGBRegressor(
        n_estimators=600, max_depth=5, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.7,
        reg_alpha=0.5, reg_lambda=1.0, min_child_weight=3,
        random_state=args.seed, n_jobs=-1, verbosity=0,
    ) if HAS_XGB else GradientBoostingRegressor(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, random_state=args.seed,
    )),
    "RF": RandomForestRegressor(
        n_estimators=args.n_trees, max_features="sqrt",
        min_samples_leaf=3, n_jobs=-1, random_state=args.seed,
    ),
    "Ridge": Pipeline([
        ("scale", RobustScaler()),
        ("ridge", Ridge(alpha=10.0)),
    ]),
}

all_metrics: list = []
oof_preds:   dict = {}
t0 = time.time()

for name, model in MODELS.items():
    print(f"\n  -- {name} --")
    oof_log = np.full(len(y_log), np.nan)
    for tr, te in _cv_iter(_make_cv()):
        model.fit(X[tr], y_log[tr])
        oof_log[te] = model.predict(X[te])
    oof_raw = np.expm1(oof_log)
    oof_preds[name] = oof_raw
    _metrics(y_raw, oof_raw, f"{name} OOF", all_metrics,
             {"model": name, "cv": "spatial_OOF"})

print(f"\n  CV time: {time.time()-t0:.0f}s")


# ══════════════════════════════════════════════════════════════════════
# 10. R2-WEIGHTED ENSEMBLE
# ══════════════════════════════════════════════════════════════════════
print("\n[10] Ensemble (R2-weighted average of OOF predictions)...")

r2_vals = np.array([r2_score(y_raw, oof_preds[n]) for n in MODELS])
weights = np.maximum(r2_vals, 0.0)

if weights.sum() == 0:
    # All models negative R2 — defer to the best (least bad) model
    best_idx         = int(np.argmax(r2_vals))
    weights          = np.zeros(len(r2_vals))
    weights[best_idx] = 1.0
    print(f"  NOTE: all OOF R2 negative -> single best model "
          f"({list(MODELS.keys())[best_idx]})")
else:
    weights /= weights.sum()
print("  Weights: " +
      "  ".join(f"{n}={w:.3f}" for n, w in zip(MODELS, weights)))

oof_stack = sum(w * oof_preds[n] for n, w in zip(MODELS, weights))
_metrics(y_raw, oof_stack, "Ensemble (R2-weighted)", all_metrics,
         {"model": "Ensemble"})


# ══════════════════════════════════════════════════════════════════════
# 11. RETRAIN ON FULL DATA
# ══════════════════════════════════════════════════════════════════════
print("\n[11] Retraining final models on full dataset...")
final_models: dict = {}
for name, model in MODELS.items():
    model.fit(X, y_log)
    final_models[name] = model

# RF feature importance
rf_imp = (pd.DataFrame({"feature": FEAT_COLS,
                         "RF_MDI": final_models["RF"].feature_importances_})
          .sort_values("RF_MDI", ascending=False).reset_index(drop=True))
print("\n  Top 25 features (RF MDI):")
print(rf_imp.head(25).to_string(index=False))
rf_imp.to_csv(OUTDIR / "feature_importance_RF.csv", index=False)

if HAS_XGB:
    xgb_imp = (pd.DataFrame({
        "feature": FEAT_COLS,
        "XGB_gain": final_models[xgb_key].feature_importances_,
    }).sort_values("XGB_gain", ascending=False).reset_index(drop=True))
    xgb_imp.to_csv(OUTDIR / "feature_importance_XGB.csv", index=False)


# ══════════════════════════════════════════════════════════════════════
# 12. SHAP
# ══════════════════════════════════════════════════════════════════════
if HAS_SHAP and HAS_XGB:
    print("\n[12] SHAP values...")
    try:
        explainer = shap.TreeExplainer(final_models[xgb_key])
        sv        = explainer.shap_values(X)
        shap_sum  = (pd.DataFrame({
            "feature": FEAT_COLS,
            "mean_abs_shap": np.abs(sv).mean(axis=0),
        }).sort_values("mean_abs_shap", ascending=False).reset_index(drop=True))
        shap_sum.to_csv(OUTDIR / "shap_summary.csv", index=False)
        pd.DataFrame(sv, columns=FEAT_COLS).to_csv(OUTDIR / "shap_values.csv",
                                                     index=False)
        print("  Top 15 features by mean |SHAP|:")
        print(shap_sum.head(15).to_string(index=False))
    except Exception as e:
        print(f"  SHAP failed: {e}")
else:
    print("\n[12] SHAP skipped (pip install shap)")


# ══════════════════════════════════════════════════════════════════════
# 13. SAVE OUTPUTS
# ══════════════════════════════════════════════════════════════════════
print("\n[13] Saving outputs...")

pred_df = df_model[["agronomic_key"]].copy()
if SPATIAL_COL and SPATIAL_COL in df_model.columns:
    pred_df[SPATIAL_COL] = df_model[SPATIAL_COL].values
pred_df[args.target]  = y_raw
pred_df["log_target"] = y_log
for name, oof in oof_preds.items():
    pred_df[f"pred_{name}"]  = oof
    pred_df[f"resid_{name}"] = y_raw - oof
pred_df["pred_Ensemble"]  = oof_stack
pred_df["resid_Ensemble"] = y_raw - oof_stack
_save(pred_df, "predictions")

pd.DataFrame(all_metrics).to_csv(OUTDIR / "model_comparison.csv", index=False)

with open(OUTDIR / "final_models.pkl", "wb") as fh:
    pickle.dump({"models": final_models, "features": FEAT_COLS,
                 "weights": dict(zip(MODELS, weights.tolist())),
                 "log_target": True}, fh)


# ══════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("FINAL RESULTS  (spatial out-of-fold)")
print("=" * 70)
print(f"  Polygons       : {len(df_model):,}")
print(f"  Features       : {len(FEAT_COLS)}"
      f"  ({n_sat} satellite + {n_agro} agronomic)")
print(f"  CV strategy    : "
      f"{'spatial ('+SPATIAL_COL+')' if SPATIAL_COL else 'random'}"
      f"  {cv_folds} folds")
print()
mdf = pd.DataFrame(all_metrics)
print(mdf[["label","MAE","RMSE","R2","RPD"]].to_string(index=False))
print()
best = mdf.loc[mdf["R2"].idxmax()]
print(f"  Best R2: {best['label']}  R2={best['R2']:.3f}  "
      f"RMSE={best['RMSE']:.1f}  RPD={best['RPD']:.2f}")
print(f"\n  RPD guide: >1.4 usable  |  >1.8 good  |  >2.0 excellent")
print(f"  (biomass std = {y_raw.std():.0f} kg/ha;  "
      f"random baseline RMSE = {y_raw.std():.0f})")
print(f"\n  Outputs -> {OUTDIR.resolve()}")
print("=" * 70)

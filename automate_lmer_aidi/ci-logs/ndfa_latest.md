# NDFA Model Selection CI Log
Run: 22718257971  Commit: ef4a49bcf0de9f9c9f15af5bf9feefb2483edd01
Time: Thu Mar  5 12:42:54 UTC 2026

## Output
```
>>> CI MODE: reduced folds, predictor sets, and RF trees

Dataset: n = 86 

=============================================================
PHASE 1: Predictor selection (glmmTMB 5-fold CV)
=============================================================

Running 4 predictor sets with 3 folds each

Predictor set: mgmt 
  Mean CV RMSE = 0.2011  (sd = 0.0118)

Predictor set: mgmt_clim_soil 
  Mean CV RMSE = 0.2019  (sd = 0.0237)

Predictor set: full_selected 
  Mean CV RMSE = 0.1964  (sd = 0.0237)

Predictor set: full_temporal 
  Mean CV RMSE = 0.2003  (sd = 0.0266)

=== Predictor selection summary (sorted by CV RMSE) ===
            set RMSE_mean RMSE_sd n_folds_ok
  full_selected    0.1964  0.0237          3
  full_temporal    0.2003  0.0266          3
           mgmt    0.2011  0.0118          3
 mgmt_clim_soil    0.2019  0.0237          3

>> Best predictor set: 'full_selected'

=============================================================
PHASE 2: 3-model comparison on best predictor set
  Set: full_selected 
=============================================================

Warning message:
the ‘nobars’ function has moved to the reformulas package. Please update your imports, or ask an upstream package maintainter to do so.
This warning is displayed once per session. 
Fixed-effect predictors passed to RF:
  pd_s, arid_s, phos_s, ecec_s, nsoi_s, inoculant_use, seed_type, farmer_gender 

--- Fold 1 of 5 ---
  glmmTMB (Beta GLMM)... done.
  lmerTest (Gaussian LMM)... done.
  Random Forest (ranger)... done.

--- Fold 2 of 5 ---
  glmmTMB (Beta GLMM)... done.
  lmerTest (Gaussian LMM)... done.
  Random Forest (ranger)... done.

--- Fold 3 of 5 ---
  glmmTMB (Beta GLMM)... done.
  lmerTest (Gaussian LMM)... done.
  Random Forest (ranger)... done.

There were 39 warnings (use warnings() to see them)
=============================================================
PHASE 2 RESULTS — Best predictor set: full_selected 
=============================================================

--- Overall CV performance (mean ± sd across 5 folds) ---
    Model R2_mean  R2_sd RMSE_mean RMSE_sd RRMSE_mean MAE_mean MAE_sd
  glmmTMB  0.1681 0.1596    0.1964  0.0237     0.4536   0.1532 0.0235
 lmerTest  0.1557 0.1354    0.1981  0.0220     0.4574   0.1558 0.0257
       RF  0.1468 0.1657    0.1983  0.0160     0.4578   0.1590 0.0118

--- Fold-level performance ---
# A tibble: 3 × 13
   fold glmmTMB_R2 glmmTMB_RMSE glmmTMB_RRMSE glmmTMB_MAE lmerTest_R2
  <dbl>      <dbl>        <dbl>         <dbl>       <dbl>       <dbl>
1     1     0.29          0.184         0.422       0.150      0.223 
2     2    -0.0125        0.224         0.521       0.178     -0.0002
3     3     0.227         0.181         0.418       0.132      0.244 
# ℹ 7 more variables: lmerTest_RMSE <dbl>, lmerTest_RRMSE <dbl>,
#   lmerTest_MAE <dbl>, RF_R2 <dbl>, RF_RMSE <dbl>, RF_RRMSE <dbl>,
#   RF_MAE <dbl>

Results saved to 2026-03-05.ndfa_model_selection_cv_results.rds
```

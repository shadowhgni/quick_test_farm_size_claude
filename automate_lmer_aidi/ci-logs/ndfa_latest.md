# NDFA Model Selection CI Log
Run: 22726446833  Commit: 54725c30e99c3c8848857fb4fa294f11a1f3bd54
Time: Thu Mar  5 16:02:45 UTC 2026

## Output
```
>>> CI MODE: reduced folds, predictor sets, and RF trees

Dataset: n = 86 

=============================================================
PHASE 1: Predictor selection (glmmTMB 5-fold CV)
=============================================================

Running 8 predictor sets with 3 folds each

Predictor set: prev_best 
  Mean CV RMSE = 0.1964  (sd = 0.0237)

Predictor set: elev_rh09_mgmt 
  Mean CV RMSE = 0.2117  (sd = 0.0141)

Predictor set: rh09_phos_tmin_mgmt 
  Mean CV RMSE = 0.2101  (sd = 0.0112)

Predictor set: rh09_soil_mgmt 
  Mean CV RMSE = 0.2001  (sd = 0.0191)

Predictor set: dur_rh09_soil_mgmt 
  Mean CV RMSE = 0.2034  (sd = 0.0270)

Predictor set: weed_mgmt_clim 
  Mean CV RMSE = 0.2119  (sd = 0.0193)

Predictor set: parsimonious_rh09 
  Mean CV RMSE = 0.1987  (sd = 0.0236)

Predictor set: kitchen_sink 
  Mean CV RMSE = 0.2393  (sd = 0.0287)

=== Predictor selection summary (sorted by CV RMSE) ===
                 set RMSE_mean RMSE_sd n_folds_ok
           prev_best    0.1964  0.0237          3
   parsimonious_rh09    0.1987  0.0236          3
      rh09_soil_mgmt    0.2001  0.0191          3
  dur_rh09_soil_mgmt    0.2034  0.0270          3
 rh09_phos_tmin_mgmt    0.2101  0.0112          3
      elev_rh09_mgmt    0.2117  0.0141          3
      weed_mgmt_clim    0.2119  0.0193          3
        kitchen_sink    0.2393  0.0287          3

>> Best predictor set: 'prev_best'

=============================================================
PHASE 2: 3-model comparison on best predictor set
  Set: prev_best 
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
PHASE 2 RESULTS — Best predictor set: prev_best 
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

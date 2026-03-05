# NDFA Model Selection CI Log
Run: 22726527941  Commit: 75aa48142f28a43ec974b2384c1c78a3af271618
Time: Thu Mar  5 16:05:28 UTC 2026

## Output
```
>>> Running in GitHub Actions — full settings, no shortcuts

Dataset: n = 86 

=============================================================
PHASE 1: Predictor selection (glmmTMB 5-fold CV)
=============================================================

Running 27 predictor sets with 5 folds each

Predictor set: mgmt_only 
  Mean CV RMSE = 0.1990  (sd = 0.0239)

Predictor set: prev_best 
  Mean CV RMSE = 0.1995  (sd = 0.0328)

Predictor set: rh09_mgmt 
  Mean CV RMSE = 0.1971  (sd = 0.0292)

Predictor set: elev_mgmt 
  Mean CV RMSE = 0.1975  (sd = 0.0265)

Predictor set: elev_rh09_mgmt 
  Mean CV RMSE = 0.2063  (sd = 0.0280)

Predictor set: dur_mgmt 
  Mean CV RMSE = 0.2004  (sd = 0.0272)

Predictor set: tmin_mgmt 
  Mean CV RMSE = 0.1990  (sd = 0.0226)

Predictor set: rh09_tmin_mgmt 
  Mean CV RMSE = 0.2034  (sd = 0.0295)

Predictor set: rain_arid_mgmt 
  Mean CV RMSE = 0.2049  (sd = 0.0264)

Predictor set: gdd_mgmt 
  Mean CV RMSE = 0.2026  (sd = 0.0257)

Predictor set: phos_mgmt 
  Mean CV RMSE = 0.1931  (sd = 0.0273)

Predictor set: soil_full_mgmt 
  Mean CV RMSE = 0.2000  (sd = 0.0316)

Predictor set: phos_ecec_mgmt 
  Mean CV RMSE = 0.1982  (sd = 0.0372)

Predictor set: weed_mgmt 
  Mean CV RMSE = 0.2062  (sd = 0.0195)

Predictor set: dens_mgmt 
  Mean CV RMSE = 0.1995  (sd = 0.0241)

Predictor set: prevcrop_mgmt 
  Mean CV RMSE = 0.2145  (sd = 0.0364)

Predictor set: temporal_mgmt 
  Mean CV RMSE = 0.2073  (sd = 0.0296)

Predictor set: nfert_mgmt 
    [attempt 1/5] ERROR: contrasts can be applied only to factors with 2 or more levels
    [attempt 2/5] ERROR: contrasts can be applied only to factors with 2 or more levels
    [attempt 3/5] ERROR: contrasts can be applied only to factors with 2 or more levels
    [attempt 4/5] ERROR: contrasts can be applied only to factors with 2 or more levels
    [attempt 5/5] ERROR: contrasts can be applied only to factors with 2 or more levels
    [attempt 1/5] ERROR: contrasts can be applied only to factors with 2 or more levels
    [attempt 2/5] ERROR: contrasts can be applied only to factors with 2 or more levels
    [attempt 3/5] ERROR: contrasts can be applied only to factors with 2 or more levels
    [attempt 4/5] ERROR: contrasts can be applied only to factors with 2 or more levels
    [attempt 5/5] ERROR: contrasts can be applied only to factors with 2 or more levels
    [attempt 1/5] ERROR: contrasts can be applied only to factors with 2 or more levels
    [attempt 2/5] ERROR: contrasts can be applied only to factors with 2 or more levels
    [attempt 3/5] ERROR: contrasts can be applied only to factors with 2 or more levels
    [attempt 4/5] ERROR: contrasts can be applied only to factors with 2 or more levels
    [attempt 5/5] ERROR: contrasts can be applied only to factors with 2 or more levels
    [attempt 1/5] ERROR: contrasts can be applied only to factors with 2 or more levels
    [attempt 2/5] ERROR: contrasts can be applied only to factors with 2 or more levels
    [attempt 3/5] ERROR: contrasts can be applied only to factors with 2 or more levels
    [attempt 4/5] ERROR: contrasts can be applied only to factors with 2 or more levels
    [attempt 5/5] ERROR: contrasts can be applied only to factors with 2 or more levels
    [attempt 1/5] ERROR: contrasts can be applied only to factors with 2 or more levels
    [attempt 2/5] ERROR: contrasts can be applied only to factors with 2 or more levels
    [attempt 3/5] ERROR: contrasts can be applied only to factors with 2 or more levels
    [attempt 4/5] ERROR: contrasts can be applied only to factors with 2 or more levels
    [attempt 5/5] ERROR: contrasts can be applied only to factors with 2 or more levels
  Mean CV RMSE = NaN  (sd = NA)

Predictor set: rh09_phos_tmin_mgmt 
  Mean CV RMSE = 0.1996  (sd = 0.0303)

Predictor set: rh09_soil_mgmt 
  Mean CV RMSE = 0.2061  (sd = 0.0396)

Predictor set: elev_rh09_soil_mgmt 
  Mean CV RMSE = 0.2058  (sd = 0.0379)

Predictor set: dur_rh09_soil_mgmt 
  Mean CV RMSE = 0.2064  (sd = 0.0389)

Predictor set: weed_mgmt_clim 
  Mean CV RMSE = 0.2142  (sd = 0.0349)

Predictor set: tmin_dur_phos_mgmt 
  Mean CV RMSE = 0.1970  (sd = 0.0284)

Predictor set: parsimonious_rh09 
  Mean CV RMSE = 0.2054  (sd = 0.0256)

Predictor set: parsimonious_3 
  Mean CV RMSE = 0.2001  (sd = 0.0296)

Predictor set: kitchen_sink 
  Mean CV RMSE = 0.2291  (sd = 0.0325)

=== Predictor selection summary (sorted by CV RMSE) ===
                 set RMSE_mean RMSE_sd n_folds_ok
           phos_mgmt    0.1931  0.0273          5
  tmin_dur_phos_mgmt    0.1970  0.0284          5
           rh09_mgmt    0.1971  0.0292          5
           elev_mgmt    0.1975  0.0265          5
      phos_ecec_mgmt    0.1982  0.0372          5
           mgmt_only    0.1990  0.0239          5
           tmin_mgmt    0.1990  0.0226          5
           prev_best    0.1995  0.0328          5
           dens_mgmt    0.1995  0.0241          5
 rh09_phos_tmin_mgmt    0.1996  0.0303          5
      soil_full_mgmt    0.2000  0.0316          5
      parsimonious_3    0.2001  0.0296          5
            dur_mgmt    0.2004  0.0272          5
            gdd_mgmt    0.2026  0.0257          5
      rh09_tmin_mgmt    0.2034  0.0295          5
      rain_arid_mgmt    0.2049  0.0264          5
   parsimonious_rh09    0.2054  0.0256          5
 elev_rh09_soil_mgmt    0.2058  0.0379          5
      rh09_soil_mgmt    0.2061  0.0396          5
           weed_mgmt    0.2062  0.0195          5
      elev_rh09_mgmt    0.2063  0.0280          5
  dur_rh09_soil_mgmt    0.2064  0.0389          5
       temporal_mgmt    0.2073  0.0296          5
      weed_mgmt_clim    0.2142  0.0349          5
       prevcrop_mgmt    0.2145  0.0364          5
        kitchen_sink    0.2291  0.0325          5
          nfert_mgmt       NaN      NA          0

>> Best predictor set: 'phos_mgmt'

=============================================================
PHASE 2: 3-model comparison on best predictor set
  Set: phos_mgmt 
=============================================================

Warning message:
the ‘nobars’ function has moved to the reformulas package. Please update your imports, or ask an upstream package maintainter to do so.
This warning is displayed once per session. 
Fixed-effect predictors passed to RF:
  phos_s, inoculant_use, seed_type, farmer_gender 

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

--- Fold 4 of 5 ---
  glmmTMB (Beta GLMM)... done.
  lmerTest (Gaussian LMM)... done.
  Random Forest (ranger)... done.

--- Fold 5 of 5 ---
  glmmTMB (Beta GLMM)... done.
  lmerTest (Gaussian LMM)... done.
  Random Forest (ranger)... done.

There were 50 or more warnings (use warnings() to see the first 50)
=============================================================
PHASE 2 RESULTS — Best predictor set: phos_mgmt 
=============================================================

--- Overall CV performance (mean ± sd across 5 folds) ---
    Model R2_mean  R2_sd RMSE_mean RMSE_sd RRMSE_mean MAE_mean MAE_sd
 lmerTest  0.1728 0.3286    0.1916  0.0277     0.4421   0.1552 0.0254
  glmmTMB  0.1614 0.3251    0.1931  0.0273     0.4457   0.1567 0.0255
       RF  0.0094 0.1854    0.2135  0.0206     0.4921   0.1739 0.0186

--- Fold-level performance ---
# A tibble: 5 × 13
   fold glmmTMB_R2 glmmTMB_RMSE glmmTMB_RRMSE glmmTMB_MAE lmerTest_R2
  <dbl>      <dbl>        <dbl>         <dbl>       <dbl>       <dbl>
1     1     0.392         0.159         0.370       0.122       0.385
2     2    -0.0786        0.219         0.502       0.176      -0.086
3     3    -0.288         0.223         0.525       0.182      -0.272
4     4     0.345         0.182         0.412       0.140       0.393
5     5     0.436         0.182         0.419       0.163       0.444
# ℹ 7 more variables: lmerTest_RMSE <dbl>, lmerTest_RRMSE <dbl>,
#   lmerTest_MAE <dbl>, RF_R2 <dbl>, RF_RMSE <dbl>, RF_RRMSE <dbl>,
#   RF_MAE <dbl>

Results saved to 2026-03-05.ndfa_model_selection_cv_results.rds
```

# NDFA Model Selection CI Log
Run: 22714152807  Commit: a8363bc9d94606f5d7343e91020ff2a549991499
Time: Thu Mar  5 10:48:41 UTC 2026

## Output
```
>>> CI MODE: reduced folds, predictor sets, and RF trees

Dataset: n = 90 

=============================================================
PHASE 1: Predictor selection (glmmTMB 5-fold CV)
=============================================================

Running 4 predictor sets with 3 folds each

Predictor set: mgmt 
  Mean CV RMSE = 0.1492  (sd = 0.0133)

Predictor set: mgmt_clim_soil 
  Mean CV RMSE = 0.1270  (sd = 0.0169)

Predictor set: full_selected 
  Mean CV RMSE = 0.1041  (sd = 0.0103)

Predictor set: full_temporal 
  Mean CV RMSE = 0.1045  (sd = 0.0094)

=== Predictor selection summary (sorted by CV RMSE) ===
            set RMSE_mean RMSE_sd n_folds_ok
  full_selected    0.1041  0.0103          3
  full_temporal    0.1045  0.0094          3
 mgmt_clim_soil    0.1270  0.0169          3
           mgmt    0.1492  0.0133          3

>> Best predictor set: 'full_selected'

=============================================================
PHASE 2: 3-model comparison on best predictor set
  Set: full_selected 
=============================================================

Error in str2lang(x) : <text>:1:103: unexpected '|'
1: ~ pd_s + I(pd_s^2) + arid_s + phos_s + ecec_s + nsoi_s + inoculant_use + seed_type + farmer_gender + (|
                                                                                                          ^
Calls: all.vars ... as.formula -> formula -> formula.character -> str2lang
Execution halted
```

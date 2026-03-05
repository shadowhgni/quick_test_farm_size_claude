# NDFA Model Selection CI Log
Run: 22716485914  Commit: b24a0072bad8f3eb3048aab9c5c2f2ef9372bef9
Time: Thu Mar  5 11:52:28 UTC 2026

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

Error in str2lang(x) : <text>:1:103: unexpected '|'
1: ~ pd_s + I(pd_s^2) + arid_s + phos_s + ecec_s + nsoi_s + inoculant_use + seed_type + farmer_gender + (|
                                                                                                          ^
Calls: all.vars ... as.formula -> formula -> formula.character -> str2lang
Execution halted
```

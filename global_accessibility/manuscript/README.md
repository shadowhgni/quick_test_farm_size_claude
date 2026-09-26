# Manuscript draft

`Manuscript_v3_Methods_Results_Discussion_Suppl.docx` (current): Methods (global workflow,
`global_accessibility_v3.py`: OSM full history, reference years 2015, 2020 and 2026, store,
routing validation per continent), Results and Discussion (regional test, 1°W–4.5°E, 5.5–13.5°N,
including the sensitivity analysis of K and the border delay), then the Supplementary Material and
the references. Values marked **[global]** are to be replaced after the global run.

Rebuild from the CI results:

```bash
cd global_accessibility/test_results && python ../manuscript/figs_v3.py   # figures -> manuscript/figs_v3/
cd ../manuscript && node build_v3.js                                     # needs the `docx` npm package
```

Table rows in `build_v3.js` were generated from `test_results/` (tables, methods, nelson_comparison,
routing_validation, sensitivity).

`Manuscript_v2_…docx`, `build.js`, `figs.py`, `fig1.py` and `figs/` are the previous version
(2015 and 2026 only), kept for reference.

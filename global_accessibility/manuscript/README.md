# Manuscript draft

`Manuscript_v2_Methods_Results_Discussion_Suppl.docx`: Methods (global workflow,
`global_accessibility_v2.py`), Results and Discussion (regional test, 1°W–4.5°E,
5.5–13.5°N, 2015 vs 2026, including the sensitivity analysis of K and the border
delay), then the Supplementary Material and the references. Values marked **[global]**
are to be replaced after the global run.

Rebuild: `python figs.py && python fig1.py` (from `global_accessibility/test_results/`;
copy `test_results/sensitivity/sensitivity.png` to `figs/fig5_sensitivity.png`), then
`node build.js` (needs the `docx` npm package).

# Manuscript drafts

- `Methods_Results.docx`: Methods (full global workflow) and Results (regional test,
  1°W–4.5°E, 5.5–13.5°N, 2015 vs 2026). Values marked **[global]** are to be replaced
  after the global run.
- `Supplementary_Material.docx`: Text S1 (implementation), Tables S1–S10, Figures S1–S2.

Rebuild: `python figs.py && python fig1.py` (from `global_accessibility/test_results/`),
then `node build.js` (needs the `docx` npm package). Figures are drawn from the 1 km COGs
in `test_results/cog_1km/`.

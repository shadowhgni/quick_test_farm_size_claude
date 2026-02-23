# Farm Size Prediction Across Sub-Saharan Africa

[![Test R Scripts](https://github.com/YOUR_USERNAME/farm-size-ssa/actions/workflows/test-scripts.yml/badge.svg)](https://github.com/YOUR_USERNAME/farm-size-ssa/actions/workflows/test-scripts.yml)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)

Machine learning models for predicting farm sizes across Sub-Saharan Africa using LSMS survey data and spatial predictors.

## 📋 Overview

This project develops Random Forest and Quantile Regression Forest models to predict farm sizes across 16 Sub-Saharan African countries using:

- **Survey Data:** Living Standards Measurement Study (LSMS) household surveys (~100,000 farms)
- **Spatial Predictors:** Cropland, population density, climate, soil, market access, and more

## 🚀 Quick Start

### Option 1: Run with GitHub Actions (No Local Setup)

1. Fork this repository
2. GitHub Actions will automatically run tests on push
3. View results in the Actions tab

### Option 2: Run with Synthetic Data

```r
# Clone the repository
git clone https://github.com/YOUR_USERNAME/farm-size-ssa.git
cd farm-size-ssa/scripts

# Generate synthetic data and run tests
Rscript 00_run_all_tests.R
```

### Option 3: Full Pipeline with Real Data

See [Data Requirements](#-data-requirements) below.

## 📁 Project Structure

```
farm-size-ssa/
├── scripts/                    # R and Python scripts
│   ├── 00_install_packages.R   # Package installation
│   ├── 00_download_spatial_data.R  # Data downloads
│   ├── 00_synthetic_data.R     # Synthetic data generator
│   ├── 00_run_all_tests.R      # Test runner
│   ├── 01.1-01.4_*.R           # Spatial data preparation
│   ├── 02.1-02.3_*.R           # LSMS data compilation
│   ├── 03.1-03.3_*.R           # Data pooling & stats
│   ├── 04.x_*.R                # ML algorithm comparison
│   ├── 05.x_*.R                # Random Forest evaluation
│   ├── 06.x_*.R                # Quantile RF models
│   ├── 07.x-10.x_*.R           # Predictions & validation
│   ├── F01-F03_*.R             # Main figures
│   └── S01-S08_*.R             # Supplementary figures
├── data/
│   ├── raw/
│   │   ├── spatial/            # Spatial predictor layers
│   │   └── web_scrapped/       # Survey data, FAOSTAT
│   └── processed/              # Analysis-ready datasets
├── output/
│   ├── figures/{main,supplementary}/
│   ├── tables/{main,supplementary}/
│   ├── maps/
│   └── reports/
├── .github/workflows/          # CI/CD pipelines
├── renv.lock                   # Package versions
└── README.md
```

## 📊 Data Requirements

### Auto-Downloaded (via `geodata` package)
| Data | Source | Script |
|------|--------|--------|
| GADM boundaries | GADM | `00_download_spatial_data.R` |
| SPAM 2010/2017 cropland | IFPRI | `00_download_spatial_data.R` |
| Population density | GPW v4 | `00_download_spatial_data.R` |
| Soil (SoilGrids) | ISRIC | `00_download_spatial_data.R` |
| Elevation | WorldClim | `00_download_spatial_data.R` |
| Temperature | WorldClim | `00_download_spatial_data.R` |
| Travel time | Malaria Atlas | `00_download_spatial_data.R` |
| CHIRPS rainfall | UCSB | `01.1_chirps_download.R` |

### Manual Downloads Required
| Data | Source | Size | Path |
|------|--------|------|------|
| SPAM 2020 | [Harvard Dataverse](https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/SWPENT) | ~2 GB | `data/raw/spatial/spam/spam2020/` |
| Cattle density | [Harvard Dataverse](https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/GIVQ75) | ~500 MB | `data/raw/spatial/cattle-density/` |
| Wealth index | [Harvard Dataverse](https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/5OGWYM) | ~200 MB | `data/raw/spatial/poverty/` |
| Du et al. 2025 Livestock | [Zenodo](https://zenodo.org/records/17128483) | 17.6 GB | `data/raw/spatial/livestock-du2025/` |
| LSMS surveys | [World Bank](https://www.worldbank.org/en/programs/lsms) | ~10 GB | `data/raw/web_scrapped/survey_data/` |

## 🔧 Installation

### Using renv (Recommended)

```r
# Install renv if needed
install.packages("renv")

# Restore exact package versions
renv::restore()
```

### Manual Installation

```r
source("scripts/00_install_packages.R")
```

## 🧪 Testing

### Run Full Test Suite

```bash
Rscript scripts/00_run_all_tests.R
```

### Run Individual Tests

```r
setwd("scripts")
source("00_synthetic_data.R")  # Generate test data
source("03.3_descriptive_stats.R")  # Run specific script
```

### GitHub Actions

Tests run automatically on:
- Push to `main` or `develop`
- Pull requests
- Weekly schedule (Mondays 6 AM UTC)
- Manual trigger

## 📈 Key Outputs

| Output | Description |
|--------|-------------|
| `stacked_rasters_africa.tif` | 10-layer predictor stack |
| `lsms_trimmed_95th_africa.rds` | Analysis-ready farm data |
| `drivers_correlation_matrix.png` | Predictor correlations |
| `summary_descriptive_stats_survey.csv` | Farm size statistics |

## 🌍 Country Coverage

| Country | Surveys | Years |
|---------|---------|-------|
| Ethiopia | 5 | 2011-2021 |
| Malawi | 5 | 2004-2019 |
| Nigeria | 4 | 2010-2018 |
| Tanzania | 6 | 2008-2020 |
| Uganda | 8 | 2005-2019 |
| + 11 more | ... | ... |

**Total: ~43 country-year combinations, ~100,000 farms**

## 📚 Citation

If you use this code or data, please cite:

```bibtex
@software{farm_size_ssa,
  author = {[Authors]},
  title = {Farm Size Prediction Across Sub-Saharan Africa},
  year = {2026},
  url = {https://github.com/YOUR_USERNAME/farm-size-ssa}
}
```

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Contact

- **Issues:** [GitHub Issues](https://github.com/YOUR_USERNAME/farm-size-ssa/issues)
- **Email:** [your.email@institution.org]

---

*Last updated: February 2026*

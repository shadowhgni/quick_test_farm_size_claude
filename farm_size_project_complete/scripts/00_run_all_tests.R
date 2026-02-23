# ==============================================================================
# Script: 00_install_packages.R
# Project: Farm Size Prediction Across Sub-Saharan Africa
# Purpose: Install all required R packages and create project folder structure
# 
# Authors: Deo, Joao, Robert, Fred 
# Documentation: Claude (Anthropic) - February 2026
#
# Inputs:
#   - None (installation script)
#
# Outputs:
#   - Installed R packages
#   - Project folder structure (if not exists)
#
# Dependencies:
#   - Base R installation
#   - Internet connection for package downloads
#
# Usage:
#   source("00_install_packages.R")
#
# Notes:
#   - Run this script once at project setup
#   - Some packages require system libraries (e.g., GDAL for terra)
#   - GitHub packages require 'remotes' package
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. SET WORKING DIRECTORY
# ------------------------------------------------------------------------------
# Set working directory to scripts folder using here package
# This ensures consistent path resolution across different systems
setwd(paste0(here::here(), '/scripts'))

# ------------------------------------------------------------------------------
# 2. PACKAGE INSTALLATION FUNCTION
# ------------------------------------------------------------------------------
#' Install packages if not already installed
#' @param packages Character vector of package names to install
#' @return NULL (side effect: installs missing packages)
install_me <- function(packages) {

  # Identify packages not yet installed

  missing_packages <- packages[!(packages %in% installed.packages()[, "Package"])]
  
  # Install missing packages from CRAN

  if (length(missing_packages)) {
    message("Installing missing packages: ", paste(missing_packages, collapse = ", "))
    install.packages(missing_packages, dependencies = TRUE)
  } else {
    message("All packages are already installed.")
  }
}

# ------------------------------------------------------------------------------
# 3. REQUIRED PACKAGES LIST
# ------------------------------------------------------------------------------
# Packages organized by category:

required_packages <- c(
  # Data manipulation & visualization
  'tidyverse',      # Core tidyverse (dplyr, ggplot2, tidyr, etc.)
  'here',           # Project-relative paths
  'patchwork',      # Combining ggplot objects
  'ggExtra',        # Marginal plots for ggplot2
  'GGally',         # ggplot2 extension for pairs plots
  
  # Web scraping & data download

'curl',           # URL data transfer
  'httr',           # HTTP requests
  'rvest',          # Web scraping
  
 # Spatial data handling
  'terra',          # Modern raster/vector handling (replaces raster)
  'geodata',        # Download geographic datasets (GADM, WorldClim, etc.)
  'afrilearndata',  # African spatial datasets
  
  # Machine learning - general
  'caret',          # ML training framework
  'gbm',            # Gradient boosting machines
  'xgboost',        # Extreme gradient boosting
  'kernlab',        # Kernel-based ML (SVM)
  'e1071',          # SVM and other ML algorithms
  
  # Machine learning - Random Forest
  'randomForest',   # Classic RF implementation
  'quantregForest', # Quantile regression forests
  'ranger',         # Fast RF implementation
  
  # Statistical distributions & analysis
  'XNomial',        # Exact multinomial tests
  'EnvStats',       # Environmental statistics
  'fitdistrplus',   # Distribution fitting
  'ineq'            # Inequality measures (Gini, etc.)
)

# ------------------------------------------------------------------------------
# 4. INSTALL CRAN PACKAGES
# ------------------------------------------------------------------------------
message("=== Installing CRAN packages ===")
install_me(required_packages)

# ------------------------------------------------------------------------------
# 5. INSTALL GITHUB PACKAGES
# ------------------------------------------------------------------------------
message("=== Installing GitHub packages ===")

# Ensure remotes is installed first
if (!requireNamespace("remotes", quietly = TRUE)) {
  install.packages("remotes")
}

# afrilearndata: African spatial learning datasets
# Contains land cover, boundaries, and other spatial data for Africa
tryCatch({
  remotes::install_github('afrimapr/afrilearndata', upgrade = "never")
  message("afrilearndata installed successfully")
}, error = function(e) {
  message("Warning: Could not install afrilearndata from GitHub: ", e$message)
})

# tabulizer: PDF table extraction (requires Java)
# Used for extracting data from PDF documents
tryCatch({
  remotes::install_github('ropensci/tabulizer', upgrade = "never")
  message("tabulizer installed successfully")
}, error = function(e) {
  message("Warning: Could not install tabulizer from GitHub: ", e$message)
  message("Note: tabulizer requires Java - ensure Java is installed")
})

# ------------------------------------------------------------------------------
# 6. CREATE PROJECT FOLDER STRUCTURE
# ------------------------------------------------------------------------------
message("=== Creating project folder structure ===")

# Define project root (one level up from scripts)
project_root <- here::here()

# Define folder structure
folders <- c(
  # Main folders
  file.path(project_root, "scripts"),
  file.path(project_root, "data", "raw", "spatial"),
  file.path(project_root, "data", "raw", "web_scrapped", "faostat"),
  file.path(project_root, "data", "raw", "web_scrapped", "survey_data"),
  file.path(project_root, "data", "processed"),
  file.path(project_root, "output", "maps"),
  file.path(project_root, "output", "graphs"),
  file.path(project_root, "output", "tables", "main"),
  file.path(project_root, "output", "tables", "supplementary"),
  file.path(project_root, "output", "figures", "main"),
  file.path(project_root, "output", "figures", "supplementary"),
  file.path(project_root, "output", "reports"),
  file.path(project_root, "validation"),
  file.path(project_root, "archive")
)

# Create folders that don't exist
for (folder in folders) {
  if (!dir.exists(folder)) {
    dir.create(folder, recursive = TRUE)
    message("Created: ", folder)
  }
}

# ------------------------------------------------------------------------------
# 7. VERIFY INSTALLATION
# ------------------------------------------------------------------------------
message("\n=== Verifying package installation ===")

# Check which packages loaded successfully
loaded <- sapply(required_packages, function(pkg) {
  tryCatch({
    suppressPackageStartupMessages(library(pkg, character.only = TRUE))
    TRUE
  }, error = function(e) FALSE)
})

if (all(loaded)) {
  message("SUCCESS: All packages installed and loaded correctly!")
} else {
  message("WARNING: Some packages failed to load:")
  message(paste(names(loaded)[!loaded], collapse = ", "))
}

# ------------------------------------------------------------------------------
# 8. SESSION INFO
# ------------------------------------------------------------------------------
message("\n=== Session Info ===")
message("R version: ", R.version.string)
message("Platform: ", R.version$platform)
message("Working directory: ", getwd())

message("\n=== Setup Complete ===")
# ==============================================================================

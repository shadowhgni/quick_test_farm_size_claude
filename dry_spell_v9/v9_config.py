# -*- coding: utf-8 -*-
"""
v9_config.py - ALL settings of the v9 dry-spell workflow
=======================================================

Every parameter of every step lives here, grouped by topic and documented. Two ways to change
them, without touching the code:

  1. edit this file, or
  2. write a JSON file with only the settings you change, e.g. my_settings.json:
         {"DEMISE_ADJUST": "none", "FALSE_START_EXCLUDE": true, "SUMMARY_ZONES": "koppen",
          "CYCLES": [90, 120]}
     and run   python run_all.py --config my_settings.json ...
     (run_all exports DRYSPELL_V9_CONFIG=<file>; every step reads it on import). Unknown keys are
     an error, so a typo cannot silently do nothing. The settings actually used are written to
     dryspell_v9/<region>/settings_used.json.

Sections
  A. Regions and folders          F. Rainfall regime (bimodality) and major season
  B. Input data sources           G. Season onset / demise (RADS method), false starts / demises
  C. Time periods                 H. NDVI phenology and its use (regime refinement, demise)
  D. Dry spells                   I. Crops, stages, sowing dates, cycles (step 4)
  E. Data quality                 J. Spatial summaries (zones), figures, performance
                                  K. Dry spells inside the season: maps, PDFs (step 6)
"""

# =============================================================================
# A. REGIONS AND FOLDERS
# =============================================================================

# Named boxes (lon_min, lat_min, lon_max, lat_max). Any other box: run_all.py --region NAME --bbox ...
REGIONS = {
    "ssa": (-18.0, -35.0, 52.0, 24.0),     # Sub-Saharan Africa (mainland + Madagascar)
    "study": (-18.0, 2.0, 38.7, 23.5),     # West Africa + Cameroon / Chad / CAR / Sudan / South Sudan
    "ci_nga": (2.5, 4.5, 14.5, 14.5),      # Nigeria box of the GitHub CI and the HPC parity check
}
DATA_ROOT = "dryspell_v9_data"     # downloaded inputs (relative to the working folder)
OUT_ROOT = "dryspell_v9"           # results

# =============================================================================
# B. INPUT DATA SOURCES (all downloaded by v9_01_download.py, no login needed)
# =============================================================================

# CHIRPS v2.0 daily, 0.05 deg (Funk et al. 2015). Only the region's tiles of each daily COG are read.
CHIRPS_COG_URL = ("https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/cogs/p05/"
                  "{y}/chirps-v2.0.{y}.{m:02d}.{d:02d}.cog")

# NDVI: PKU GIMMS NDVI v1.2 (Li et al. 2023, ESSD 15, 4181; Zenodo 10.5281/zenodo.8253971, CC BY 4.0).
# Half-monthly, 1/12 deg, the GIMMS NDVI3g record (the input of Vrieling et al. 2013, Remote Sens.
# 5, 982) recalibrated with Landsat. "AVHRR_solely" = GIMMS NDVI3g only (1982-2015, closest to the
# paper); "AVHRR_MODIS_consolidated" extends to 2022 with MODIS.
NDVI_PRODUCT = "AVHRR_solely"
NDVI_ZENODO_RECORD = "8253971"
NDVI_ZIPS = {
    "AVHRR_solely": ["1982_1990", "1991_2000", "2001_2010", "2011_2015"],
    "AVHRR_MODIS_consolidated": ["1982_1990", "1991_2000", "2001_2010", "2011_2022"],
}
NDVI_ZIP_URL = "https://zenodo.org/records/{rec}/files/PKU_GIMMS_NDVI_{prod}_{period}.zip?download=1"
NDVI_SCALE, NDVI_FILL = 0.001, 65535          # uint16 * 0.001; 65535 = non-vegetated / NDVI <= 0
NDVI_QC_BAD = [2]                             # QC band values treated as missing (2 = possible snow/cloud)

# Country boundaries: Natural Earth 1:50m (public domain); GeoJSON mirror as fallback
BOUNDARY_URLS = [
    "https://naciscdn.org/naturalearth/50m/cultural/ne_50m_admin_0_countries.zip",
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson",
]
# Agro-ecological zones of Africa (Sebastian 2009, HarvestChoice/IFPRI, CC BY-NC 3.0;
# https://cgspace.cgiar.org/items/73435d49-8dce-4293-8fca-9c764e4cf5d2 = doi:10.7910/DVN/HJYYTI).
# The ASCII grid on Dataverse is damaged south of 3.8 N (read tolerantly, rest = no data).
AEZ_URL = ("https://dataverse.harvard.edu/api/access/datafile/:persistentId?"
           "persistentId=doi:10.7910/DVN/HJYYTI/0I9GVI")
# Koppen-Geiger 1 km (Beck et al. 2023, Sci. Data 10, 724; figshare 21789074, CC BY 4.0)
KOPPEN_URL = "https://ndownloader.figshare.com/files/61012822"      # koppen_geiger_tif.zip
KOPPEN_PERIOD = "1991_2020"
KOPPEN_FILE = "koppen_geiger_0p00833333.tif"                       # 0p1 / 0p5 / 1p0 also in the zip

# =============================================================================
# C. TIME PERIODS
# =============================================================================
DATA_YEAR_MIN, DATA_YEAR_MAX = 1981, 2025     # CHIRPS years downloaded
CLIM_YEAR_MIN, CLIM_YEAR_MAX = 1981, 2024     # complete years for the mean annual rainfall cycle
SEASON_YEAR_MIN, SEASON_YEAR_MAX = 1981, 2024 # seasons kept (by calendar year of onset)
NDVI_YEAR_MIN, NDVI_YEAR_MAX = 1982, 2015     # NDVI years used (product limits: 1982-2015 / 2022)

# =============================================================================
# D. DRY SPELLS
# =============================================================================
DRY_MM = 1.0              # a day is dry if rain < DRY_MM; a missing day is never dry and breaks a spell
STEP1_MIN_SPELL = 5       # shortest spell stored by step 3 (days); step 4 minimum must be >= this

# =============================================================================
# E. DATA QUALITY
# =============================================================================
MAX_MISSING_FRAC = 0.005  # a cell is unusable if more than 0.5 % of its days have no rainfall
WINDOW_MIN_COVER = 0.95   # a season window needs rainfall data on >= 95 % of its days
MIN_VALID_SEASONS = 5     # fewer valid seasons -> the cell is not analysed in step 4

# =============================================================================
# F. RAINFALL REGIME (BIMODALITY) AND MAJOR SEASON
# =============================================================================
# From the daily mean annual rainfall cycle smoothed by a circular moving average:
#   ratio = mid-season trough / smaller of the two main peaks
REGIME_SMOOTH_DAYS = 31        # moving-average width (days)
PEAK_MIN_REL = 0.25            # a peak must reach this share of the annual maximum
PEAK_MIN_SEP = 45              # peaks closer than this (days) count as one
BIMODAL_MAX_RATIO = 0.80       # ratio <= 0.80 -> bimodal
TRANSITION_MAX_RATIO = 0.95    # 0.80 < ratio <= 0.95 -> transition; above (or one peak) -> unimodal
ARID_MM = 150.0                # mean annual rain below this -> no rainy season analysed
# CHIRPS 1981-2024 calibration: Lagos 0.33, Ibadan 0.63, Ilorin 0.73 (bimodal); Port Harcourt 0.81,
# Enugu 0.88 (transition); Makurdi 0.98, Abuja 0.99, Kano / Sokoto / Maiduguri 1.00 (unimodal).

# Which season of a BIMODAL cell is analysed (transition cells keep one season with the dip inside):
#   "wettest": larger climatological rainfall      "first": the one after the driest part of the year
MAJOR_SEASON_RULE = "wettest"

# How the final regime is decided (section H refines it with NDVI):
#   "rain"      rainfall only (v8 behaviour)
#   "consensus" bimodal only when rainfall shows a trough (ratio <= TRANSITION_MAX_RATIO) AND NDVI
#               shows two growing seasons; rainfall-bimodal cells with one NDVI season become
#               transition (one season); NDVI cannot create a trough that rainfall does not have
#   "ndvi"      bimodal whenever NDVI shows two seasons and rainfall has any trough
REGIME_SOURCE = "consensus"

# =============================================================================
# G. SEASON ONSET / DEMISE (RADS METHOD) AND FALSE STARTS / DEMISES
# =============================================================================
# Inside each cell's major-season window: S(t) = cumsum(rain - window mean daily rain);
# onset = day after min(S); demise = day of max(S) after the onset (Liebmann & Marengo 2001,
# Bombardi et al. 2019). An onset on the window's first day is rejected.
SEASON_LEN_MIN = 30            # days; a shorter season is not a cropping season
SEASON_LEN_MAX = 330

# False start: a dry spell right after the onset; false demise: a dry spell just before the demise
# (the season had in fact ended earlier and a late shower set the demise). Seasons are always
# FLAGGED (columns false_start / false_demise); set *_EXCLUDE to drop them from the analysis.
FALSE_WINDOW_DAYS = 20         # look at the first (start) / last (demise) 20 days of the season
FALSE_DRY_DAYS = 10            # ... and require at least 10 dry days there
FALSE_DRY_MODE = "spell"       # "spell": 10 CONSECUTIVE dry days; "total": 10 dry days in total
FALSE_START_EXCLUDE = False
FALSE_DEMISE_EXCLUDE = False

# =============================================================================
# H. NDVI PHENOLOGY (Vrieling et al. 2013 approach) AND ITS USE
# =============================================================================
USE_NDVI = True                # False -> v8 behaviour (no NDVI download, regime from rain only)
# Gap filling and smoothing of the half-monthly series before phenology
NDVI_MAX_GAP = 3               # interpolate gaps up to 3 half-months; longer gaps stay missing
NDVI_SMOOTH = 3                # running-median width (half-months) applied before detection
# Number of seasons from the mean annual NDVI profile (24 half-months)
NDVI_MIN_AMPLITUDE = 0.05      # a season's peak must rise this much above the trough before it
NDVI_PEAK_MIN_SEP = 3          # half-months between two peaks (~45 days)
NDVI_MIN_MEAN = 0.10           # profiles with mean NDVI below this are treated as no vegetation signal
# Per-year start / end of season: variable threshold inside a search window around each mean peak
NDVI_SOS_THRESHOLD = 0.5       # SOS = upward crossing of trough_before + 0.5 x (peak - trough_before)
NDVI_EOS_THRESHOLD = 0.5       # EOS = downward crossing of trough_after + 0.5 x (peak - trough_after)
NDVI_REGRID = "nearest"        # NDVI 1/12 deg -> CHIRPS 0.05 deg: each cell takes the NDVI pixel it lies in
NDVI_FILL_RADIUS = 2           # NDVI pixels (~9 km each) a pixel without vegetation signal (town, water)
                               # may borrow its seasons from; 0 = off

# Demise adjustment with NDVI: vegetation stays green after the last rains (stored soil water).
#   "none"          rainfall demise only
#   "median_offset" demise + clip(median over years of (NDVI EOS - rainfall demise), 0, DEMISE_SHIFT_MAX)
#   "per_year"      demise + clip(EOS - demise of that year, 0, DEMISE_SHIFT_MAX); the cell median
#                   where the year has no NDVI (e.g. after NDVI_YEAR_MAX)
DEMISE_ADJUST = "median_offset"
DEMISE_SHIFT_MAX = 30          # days; never move the demise more than this
DEMISE_MATCH_WINDOW = (-30, 90)  # an NDVI EOS belongs to a rainfall season if it falls this many
                                 # days around the rainfall demise

# =============================================================================
# I. CROPS, STAGES, SOWING DATES, CYCLES (step 4)
# =============================================================================
SOW_OFFSETS = [0, 10, 20, 30, 40]   # days after DAY0
DAY0 = 0                            # first sowing = onset + DAY0 (0 or 1)
CYCLES = [70, 90, 110, 130]         # days from sowing to physiological maturity
DEMISE_GRACE = 0                    # extra days maturity may exceed the (NDVI-adjusted) demise.
                                    # v8 used 10 with the rainfall demise; with DEMISE_ADJUST the NDVI
                                    # offset replaces it. Use 10 with DEMISE_ADJUST = "none".
FEASIBLE_MIN_FRAC = 0.5             # a cell is IMPOSSIBLE if fewer seasons than this are feasible
MIN_FEASIBLE_SEASONS = 5            # probabilities need at least this many feasible seasons
MIN_SPELL_CROP = {"sorghum": 10, "pearl_millet": 10, "groundnut": 10}   # days, per crop

# STAGES - onset of each stage in days after sowing (DAS) for a REFERENCE cultivar, from published
# stage keys with typical timings, then rescaled to every cycle length in CYCLES:
#   * emergence stays at emergence_das whatever the cycle;
#   * cultivars of different duration differ mostly BEFORE the anchor stage (flowering) in sorghum and
#     pearl millet: the anchor-to-maturity (grain filling) duration changes only as
#     (cycle / reference_cycle) ** post_anchor_exponent, the vegetative phase takes the rest;
#   * groundnut (indeterminate) is the other way round: time to first flower (anchor R1) changes little,
#     (cycle / reference_cycle) ** pre_anchor_exponent, and pod / seed filling takes the rest;
#   * stages inside each phase keep their relative positions. stage_windows.csv lists the result.
# The exponents are my assumption (not from a single published table) - calibrate with local trials.
# "window" = most drought-vulnerable period: [stage, offset days] start and end (inclusive), both
# relative to stage ONSETS.
CROPS = {
    "sorghum": {
        "label": "Sorghum",
        # Vanderlip & Reeves (1972) stages 0-9 as in the K-State sorghum growth-stage guide (timings in
        # days after EMERGENCE: 3-leaf ~10, 5-leaf 20-25, GPD 30-40, boot 50-60, half-bloom 60-70,
        # soft dough 75-85, hard dough 85-95, physiological maturity 95-115) + 5 d sowing-to-emergence
        "reference_cycle": 110, "emergence_das": 5, "anchor": "S6", "post_anchor_exponent": 0.6,
        "stages": [["S0", "emergence", 5], ["S1", "3-leaf", 15], ["S2", "5-leaf", 27],
                   ["S3", "growing point differentiation", 40], ["S4", "flag leaf visible", 50],
                   ["S5", "boot", 60], ["S6", "half-bloom", 70], ["S7", "soft dough", 85],
                   ["S8", "hard dough", 95]],                       # S9 physiological maturity = end of cycle
        "window": [["S5", -7], ["S6", 14]],   # ~1 week before boot to ~2 weeks after half-bloom (K-State)
    },
    "pearl_millet": {
        "label": "Pearl millet",
        # Maiti & Bidinger (1981, ICRISAT Res. Bull. 6) stages 0-9; DAS from the typical timings of the
        # stage key (emergence 3-5, heading 45-55, flowering 50-65, milk 65-75, dough 75-85, maturity
        # 85-100 DAS); 3-leaf, tillering, panicle initiation and flag leaf placed by Maiti & Bidinger's
        # proportions (not given in days in the key)
        "reference_cycle": 92, "emergence_das": 4, "anchor": "P6", "post_anchor_exponent": 0.6,
        "stages": [["P0", "emergence", 4], ["P1", "3-leaf", 10], ["P2", "tillering", 17],
                   ["P3", "panicle initiation", 35], ["P4", "flag leaf / boot", 42],
                   ["P5", "panicle emergence (heading)", 50], ["P6", "flowering (anthesis)", 57],
                   ["P7", "milk", 70], ["P8", "dough", 80]],         # P9 physiological maturity = end of cycle
        "window": [["P6", 0], ["P8", -1]],    # flowering + milk: the most sensitive phase (tillers can
                                              # compensate earlier stress; Mahalakshmi & Bidinger 1985)
    },
    "groundnut": {
        "label": "Groundnut",
        # Boote (1982) R stages with the typical timings of the peanut growth-stage key (DAP: R1 25-40,
        # R2 35-45, R3 45-55, R4 55-70, R5 70-80, R6 80-90, R7 90-105, R8 harvest maturity 105-140);
        # emergence ~8 DAP is my assumption (not in the key)
        "reference_cycle": 120, "emergence_das": 8, "anchor": "R1", "pre_anchor_exponent": 0.3,
        "stages": [["VE", "emergence", 8], ["R1", "beginning bloom", 32], ["R2", "beginning peg", 40],
                   ["R3", "beginning pod", 50], ["R4", "full pod", 62], ["R5", "beginning seed", 75],
                   ["R6", "full seed", 85], ["R7", "beginning maturity", 97]],   # R8 = end of cycle
        "window": [["R3", 0], ["R7", -1]],    # pod set to seed filling (Nageswara Rao et al. 1985)
    },
}

# =============================================================================
# J. SPATIAL SUMMARIES, FIGURES, PERFORMANCE
# =============================================================================
# Zones used to summarise step 4 and step 5 results:
#   "aez8"   HarvestChoice AEZ, 8 classes: tropic-warm / tropic-cool x arid / semiarid / subhumid /
#            humid (subtropic classes folded into warm / cool by their 2nd digit)
#   "aez"    HarvestChoice AEZ, all classes (3-digit codes)
#   "koppen" Koppen-Geiger 1991-2020 (Beck et al. 2023), 30 classes, labels from legend.txt
#   "regime" rainfall regime only (unimodal / transition / bimodal)
SUMMARY_ZONES = "aez8"
SSA_NAME = "SSA"                 # folder of the aggregate (step 5)
ROWS_PER_TASK = 8                # grid rows per worker task (steps 3-4)
FIG_DPI = 170

# =============================================================================
# K. DRY SPELLS INSIDE THE SEASON: MAPS, PDFs, LATITUDE / ZONE SUMMARIES (step 6)
# =============================================================================
# Crop-independent statistics of every valid (major) season, as in v7: spells are clipped to the
# window [onset + EXCLUDE_FIRST, demise - EXCLUDE_LAST] and kept if >= SPELL_STATS_MIN days long.
SPELL_STATS_MIN = 10             # days (< DRY_MM each); must be >= STEP1_MIN_SPELL
SPELL_STATS_EXCLUDE_FIRST = 10   # v7 default: ignore the first 10 days after onset (onset = day 0)
SPELL_STATS_EXCLUDE_LAST = 10    # ... and the last 10 days before the demise
SPELL_STATS_DEMISE = "rain"      # "rain": rainfall demise (spells are about the RAINY season);
                                 # "adjusted": NDVI-adjusted demise (section H) - adds the dry-down
SPELL_STATS_MIN_COND = 3         # a cell median of first / last / longest needs >= 3 seasons with it
LAT_BAND_DEG = 1.0               # latitude bands of the tables and the latitude profile
PDF_LAT_BAND_DEG = 2.0           # coarser bands for the PDF curves (one curve each)
PDF_SMOOTH_DAYS = 3              # Gaussian smoothing (sd, days) of the PDF curves; 0 = raw histogram


# Study design: accessibility change, land-use change and crop yields in Sub-Saharan Africa

Revision of "NDVI-based crop yield estimation and land-use change in Sub-Saharan Africa" (27 Oct 2026) · @Deo-Gratias Judrita Mawugnon HOUGNI

## What changed in this revision

The study now asks whether changes in travel time to cities and markets are associated with, and where the evidence allows, cause forest conversion to cropland and yield change. The earlier land-use mapping and NDVI yield work become outcome layers for that question.

- **New treatment layer.** Annual travel-time maps for 2015–2026 come from `global_accessibility_v3.py`, plus a road-only version with destinations held fixed. A long-term level uses 2015, 2020 and 2025.
- **The treatment is dated and checked before any outcome is examined.** The year a road appears in OpenStreetMap (OSM) is the year it was mapped, not necessarily the year it was built.
- **Yields come in three tiers:**
  1. Admin panels (HarvestStat, GROW-Africa);
  2. LSMS-ISA survey data aggregated to enumeration areas (EA panels);
  3. The NDVI pilot of the earlier design, kept for crops that pass its Gate B.
- **A new identification section** defines treated and control units, the estimators, and the checks a result must pass before it is called causal rather than an association.
- **The earlier 1 km yield prediction (old Phase 3) becomes optional.** Attribution does not depend on it.

## Scope, questions and estimands

The study estimates two effects of access change and one long-term description, and every result is reported as an association unless it passes the identification checks of Gate C.

| Estimand | Outcome | Unit | Treatment | Years |
| --- | --- | --- | --- | --- |
| E1 | Forest-to-cropland conversion (area, share of forest at baseline) | 0.01° cell (~1.1 km) | Access change, annual | Loss years 2016–2022 confirmed; 2001–2015 pre-period |
| E1b | New cropland from other natural vegetation | 0.01° cell | Same | 2016–2022 |
| E2a | Yield, admin statistics | Admin unit × crop × season | Population- or cropland-weighted access change of the unit | 2001–2023 |
| E2b | Yield, enumeration areas | LSMS-ISA enumeration area × crop × season (household and plot data aggregated) | Cropland-weighted access change of the 0.01° cells within 5 km of the EA point | Survey waves 2008–2024 |
| E2c | Seasonal NDVI productivity on pure-crop footprints | Footprint or cell × crop × season | Access change | 2017–2023 (Sentinel-2), 2001–2023 if MODIS qualifies |
| E3 | Long differences of E1 and E2 | As above | Change 2015→2020, 2020→2025, 2015→2025 | Three epochs |

**Intensification vs. extensification.** Better access can raise output by expanding cropland (E1) or by raising yields on existing cropland (E2). To keep them apart, every yield outcome is measured on **stable cropland only**: cropland in every year of the window (Phase 1 mask). Yields on newly converted land are reported separately, because they mix soil fertility and management effects with access.

**Direction of change.** Increases and decreases in access are estimated separately, never pooled. Decreases are rare and partly artefacts of OSM editing (Phase 0), so they are reported only after the tag-edit filter.

## Phased plan and gates

The study runs in four phases with four gates, each written down before the data it judges are examined.

| Phase | Content | Gate | Pass condition (thresholds fixed in advance) |
| --- | --- | --- | --- |
| 0 | Treatment: annual access 2015–2026, road-only counterfactual, dating of road events | **T** | Share of OSM "new road" events confirmed by imagery within ±1 year ≥ threshold, per zone |
| 1 | Land use: cropland change, forest-to-cropland conversion | **A** | Unchanged from the earlier design: class accuracies per zone |
| 2 | Yields: admin and LSMS panels prepared; NDVI pilot | **B** | NDVI tier only, unchanged from the earlier design |
| 3 | Effect estimation for E1–E3 | **C** | Pre-trends, placebos and agreement across control definitions (Section "Gate C") |

A zone that fails Gate T is analysed only at the long-term level (E3), which tolerates dating errors of one to two years. A failed gate is reported, not hidden.

## Phase 0: treatment — measuring and dating access change

Access change is measured from one source and one method for every year, and each change is attributed to a road event whose date is checked independently.

### Access layers (from `global_accessibility_v3.py`)

- **Annual runs:** `--years 2015 2016 … 2026`, all cut from the same OSM full-history file at 1 January. The years are processed one after another to bound disk use.
  - Each year leaves its friction surface, road speeds and 17 travel-time layers in `store/`, readable with `load_store()`.
  - The Weiss et al. (2018) completion currently applies to every year from 2015 to the year before the last. For annual runs it is kept as a sensitivity option, not the default, because it would make roads appear earlier than OSM shows them.
- **Two treatment versions:**
  1. **Total access:** settlements and population of the nearest GHSL epoch. This mixes road change with settlement growth.
  2. **Road-only access:** destinations, land cover and the governance factor held at 2015, so that only the road network changes.
  - The road-only version needs a new script option (`--fixed-destinations 2015`). This is listed as required work.
- **Treatment variables:**
  - **Binary event:** the first year in which travel time to the nearest settlement of 50,000–50 million (cities_11) falls by at least 20% and at least 15 minutes, and stays below that level for two years. Both thresholds are placeholders.
  - **Continuous dose:** change in log travel time.
  - **Market access:** sum over settlements of population × travel time^(−θ). θ is varied, and this measure is used as a check only.
  - **Layers:** cities_11 is primary; cities_12 (≥ 5,000) and ports_5 are alternatives.

### The mapping-date problem

A road appears in OSM when someone maps it. In much of Africa, large areas were mapped in bursts by humanitarian campaigns or by AI-assisted imports, years after the roads were built. Without correction, the "treatment year" would partly be the year a mapping campaign passed. Campaigns may themselves be correlated with outcomes, for example through NGO presence after a crisis.

Each road event is therefore classified and dated as follows.

1. **Segment-level events.** From the OSM history, each way gets its first appearance, and each change of class or surface tag is recorded.
   - Events are aggregated per 0.01° cell into: new way; upgrade (class raised, or surface changed to paved on an existing way); downgrade (the reverse); deletion.
   - This needs an extra extraction step from the history file before `time-filter`. The way-level history is in the file; the procedure is to be written.
2. **Mapping bursts.** An event is flagged as a probable mapping event, not construction, when it occurs in a cell-year where:
   - a large number of ways was added by few users or changesets; or
   - the changeset comes from a known import or campaign; or
   - the way's geometry already shows up in imagery from earlier years.
   - Burst thresholds are fixed in advance.
   - **Metadata (checked):** the full-history planet keeps the user, uid, changeset and timestamp of every version (Geofabrik's public extracts drop them since May 2018, so they cannot be used for this step). Each version's changeset ID joins the changeset dump (`changesets-YYMMDD.osm.bz2`), whose tags identify campaigns and imports:
     - `comment` and `hashtags` carry HOT Tasking Manager hashtags (`#hotosm-project-<id>` on the production instance; the prefix is from community sources);
     - `created_by` = "Rapid …" and `data_used` (matching MapWithAI or Esri) mark AI-assisted edits;
     - `source` and `imagery_used` record the imagery.
     - No official tag marks Microsoft road imports. The history file holds personal data and is handled under GDPR.
3. **Imagery confirmation.** A new-way or upgrade event is confirmed when a road-construction signal appears in the 1–2 years before or at the OSM date:
   - in Landsat or Sentinel-2 time series along the segment: a bare-soil fraction jump, or a new linear feature;
   - the model is the Landsat road-dating method of Valle et al. (2024), developed on the Transamazon highway.
   - The ground check for the method is the Congo Basin forest-road dataset (Slagter et al. 2024), which gives the month of opening for 46,311 km of roads built 2019–2023.
4. **Externally dated projects.** These form a subsample with independent timing and planned location:
   - **AidData Geospatial Global Chinese Development Finance v3** (2024; commitments 2000–2021, implementation tracked to 2023): actual implementation start and completion dates, sector (e.g. "Transport and storage"), and precise OSM geometries for 8,797 features of 9,405 projects. This is the main dated subsample. Whether road projects come as line geometries is to be checked on a road record.
   - **World Bank Geocoded Research Release v1.4.2** (AidData, 2017; IBRD/IDA projects approved 1995–2014): point locations only, with actual start and end dates and CRS purpose codes (21020 = road transport) *(field names from a secondary source; to be confirmed in the release files)*. It is used for timing only, since points do not locate the road.
   - AidData's newer "China's Global Loans and Grants Dataset 1.0" (2025; commitments 2000–2023) has no geospatial version yet.
5. **Event classes used in the analysis:**
   - *confirmed construction or upgrade*: the primary treatment;
   - *unconfirmed*: used in a sensitivity run;
   - *mapping burst*: used as a placebo event;
   - *downgrade or deletion*: decreasing access, kept only if imagery or tags support a real change. The 2015–2020 regional test showed that most slower road cells came from reclassification or surface tags, not deterioration.

**Gate T.** Per agro-ecological zone:
- the share of OSM new-way and upgrade events confirmed by imagery within ±1 year;
- the share explained by mapping bursts.

Zones below the threshold are analysed only at the long-term level (E3).

## Phase 1: land-use outcomes

Phase 1 of the earlier design is kept unchanged as the source of E1, with a longer pre-period and an outcome table per cell and year.

- **Kept unchanged from the earlier design:** GLAD cropland 2015–2024, Hansen GFC baseline at 30% canopy with 10% as a check, JRC TMF in humid forest, the conversion rule (loss in *t*, not cropland in *t*−1, cropland in one of *t* to *t*+2), the validation sample, cross-checks with GACED30, AFCD, GLC_FCS30D and WRI drivers, and Gate A.
- **Per cell and year:** confirmed conversion area, conversion as a share of the forest remaining, tree-cover loss without confirmed conversion, and new cropland from other natural vegetation.
- **Pre-period for trend tests:**
  - Hansen tree-cover loss from 2001;
  - GACED30 cropland from 2000, which extends the conversion series before 2015 where it agrees with GLAD over 2015–2024.
- **Logging and plantations:** in the Congo Basin, many roads are logging roads, and a large share of roads in concessions are abandoned within a few years (Kleinschroth et al. 2019). Concession areas are flagged and analysed separately, so that logging-road effects are not read as agricultural access effects.

## Phase 2: yield outcomes

Yields are prepared in three tiers that trade coverage for attribution. Results that agree across tiers carry the most weight.

### Tier 1: admin panels (E2a)

- HarvestStat Africa (FEWS NET-based, 1980–2022, 33 countries) and GROW-Africa v2.0, harmonised and screened as in Phase 2a of the earlier design: seasons, units, and the independence labels for agreement checks.
- **Treatment of a unit:** access change weighted by cropland (Phase 1 stable mask) and, as an alternative, by rural population.
- **Admin yields are production divided by harvested area.** They change when cropland expands onto poorer land, so the share of the unit's cropland that is newly converted is a covariate and a heterogeneity dimension.

### Tier 2: LSMS-ISA data aggregated to enumeration areas (E2b)

The unit of analysis is the enumeration area (EA), the survey cluster whose coordinates the public files give. Household and plot records are only inputs to the EA values.

- **Countries and waves:**
  - Eight LSMS-ISA countries. Only EAs surveyed in at least two waves with access change between them are used. The EA, not the household, is the panel unit: most panels revisit the same EAs, but several were refreshed, which breaks EA continuity. Checked on the World Bank Microdata Library:

    | Country | Waves | Waves sharing EAs | Break |
    | --- | --- | --- | --- |
    | Ethiopia (ESS) | 2011/12, 2013/14, 2015/16, 2018/19, 2021/22 | 2011–2015 (urban EAs from 2013/14); 2018/19–2021/22 (Tigray and some EAs missing in 2021/22) | 2018/19 is a new panel |
    | Malawi (IHPS) | 2010, 2013, 2016, 2019 | 102 EAs across all four waves (204 in 2010–2013) | None; panel reduced in 2016 |
    | Nigeria (GHS-Panel) | 2010/11, 2012/13, 2015/16, 2018/19, 2023/24 | 500 EAs 2010–2015; 159 "long-panel" EAs to 2018/19; 2018/19–2023/24 | 360 new EAs in 2018/19 |
    | Tanzania (NPS) | 2008/09, 2010/11, 2012/13, 2014/15, 2019/20, 2020/21 | 2008–2012 cohort (re-clustered in 2012/13); 2014/15–2020/21 cohort | New sample in 2014/15 |
    | Uganda (UNPS) | 2009/10 to 2019/20 (7 waves) | 322 EAs from 2009/10 | A third of the sample refreshed from 2013/14 (EA or household level: to confirm) |
    | Niger | ECVMA 2011, 2014; EHCVM 2018/19, 2021/22 | 2011–2014 household panel; 2018/19–2021/22 cluster panel | Between ECVMA and EHCVM |
    | Mali | EAC-I 2014/15, 2017/18; EHCVM 2018/19, 2021/22 | EHCVM 2018/19–2021/22 (same clusters, 12 households each) | EAC-I rounds are cross-sections |
    | Burkina Faso | EHCVM 2018/19, 2021/22 | Half of the 2018/19 households (3,227); movers not followed | — |

  - Under the EA design, a refresh is handled by using each continuous segment as its own panel. Tracked movers are dropped from the EA aggregates, since they no longer farm in the EA.
- **Aggregation to EA × crop × season:**
  - **Yield:** total production of the crop in the EA ÷ total GPS-measured area of the plots growing it (a ratio of sums, not a mean of plot yields). Plot areas are GPS-measured in all countries checked except where the household refused, the terrain was too difficult or the plot was far away; there the self-reported area is used and flagged.
  - **Harvest units:** quantities are converted to kg with the surveys' conversion factors (e.g. Nigeria `sa3iq6_conv`, Uganda AGSEC5A, Malawi seasonal crop conversion files). For intercropped plots, the crop's area is the plot area times the reported share planted to the crop (Tanzania, Uganda), and intercropped observations are also analysed separately.
  - **Value of output per hectare**, all crops together, as a crop-agnostic outcome.
  - **Minimum sample:** a minimum number of households and plots per EA-crop-season, fixed in advance; below it the observation is dropped.
  - **Weights:** EA observations are weighted by the number of contributing plots; survey weights are used as an alternative.
  - **Composition:** the crop's share of cultivated area in the EA is reported alongside its yield, since EA yield can move with which plots grow the crop.
  - **Sensitivity:** EA values recomputed from households observed in both waves only, to separate yield change from changes in who is sampled.
- **Location and treatment:**
  - Public EA coordinates are displaced: 0–2 km in urban areas and small towns, 0–5 km in rural areas, and 0–10 km for 1% of EAs, constrained within the zone (Ethiopia study documentation). The other countries state only that coordinates are offset; their parameters are to be read in each Basic Information Document.
  - Plot coordinates are not released; public plot geovariable files carry only derived values (distance to the household, slope, elevation, wetness). The one possible exception, Tanzania 2020/21 plot GPS fields, is to be checked.
  - The 1% of EAs moved up to 10 km are a known source of treatment error. The displacement simulation includes them.
  - The treatment is the cropland-weighted mean access change of the 0.01° cells within 5 km of the displaced point, consistent with the EA as unit. The remaining bias is estimated by simulating the displacement on the access maps.
  - True coordinates are not needed for this design; they would only tighten the treatment.
- **Covariates:** EA means of plot characteristics (plot size, slope, irrigation, intercropping, soil from the plot modules or iSDAsoil), plus rainfall and prices at the EA point.
- **Mechanisms, as EA shares:** share of plots with inorganic fertiliser and improved seed, share of households hiring labour, share of output sold, crop mix, local input and output prices, and extension contact.
  - Extension contact matters because Ethiopian evidence suggests roads and extension complement each other.
- **Fixed effects:** EA fixed effects absorb time-invariant soil, climate and location. Wave × region fixed effects absorb weather and price shocks.

### Tier 3: NDVI on pure-crop footprints (E2c)

- **Kept unchanged from the earlier design:** Phases 2a–2d (screening, purity rules, the Sentinel-2/MODIS agreement test, the pilot model, Gate B).
- Only crops passing Gate B are used, with the seasonal NDVI features as the outcome directly or as predicted yield.
- A crop-agnostic fallback, integrated NDVI on stable cropland, is reported as "cropland productivity", not yield.
- **Roots and tubers** (cassava, yams) are expected to fail Gate B. For them, Tier 1 and Tier 2 are the only yield evidence.

## Identification strategy and controls

Effects are estimated by comparing units that gain access at different times, with controls chosen and fixed before outcomes are examined, and a causal label is used only when the checks of Gate C pass.

### Designs

1. **Staggered event study (primary, annual treatment).**
   - Estimators robust to heterogeneous effects across treatment cohorts: Callaway and Sant'Anna for binary events; Callaway, Goodman-Bacon and Sant'Anna for continuous doses (R package `contdid`); Sun and Abraham as a check.
   - Controls are never-treated and not-yet-treated units, with unit fixed effects and region × year fixed effects. Event-time coefficients run from −5 to +5 years.
   - Two-way fixed effects regressions are reported only for comparison, because they can be biased with staggered timing.
2. **Long differences (E3, three epochs).**
   - Δ outcome on Δ log travel time for 2015→2020, 2020→2025 and 2015→2025, with differenced covariates (rainfall, population, prices).
   - Robust to dating errors of one to two years and to short-run OSM noise.
3. **Synthetic control or synthetic difference-in-differences** for a few large, well-dated projects, such as a major corridor or bridge with known completion.

### Control units, in order of preference

| Control | Definition | Threat it addresses | Weakness |
| --- | --- | --- | --- |
| Not-yet-treated (pipeline) | Units on roads built later in the window, or on planned corridors | Selection of road locations | Planned-but-late roads may differ |
| Matched never-treated | Matched on 2015 travel time, distance to roads, population, slope, rainfall, soils, forest cover, protected status, and pre-2015 trends of loss and NDVI (coarsened exact matching or entropy balancing) | Observable differences | Unobserved targeting |
| Spatial bands | 0–5 km of a new segment vs 10–30 km, excluding a spillover band | Regional shocks | Spillovers beyond the band |
| Placebo events | Mapping bursts; placebo roads drawn at random, or shifted along the same corridor | Measurement and timing artefacts | — |

### Endogenous road placement

Roads are built where returns, or forest rents, are expected. The design addresses this in three ways:

- **Timing within corridors.** Comparisons are restricted to units along roads that were all eventually built, so that only the timing varies.
- **Upgrades on existing ways.** The location is fixed by history; only the timing of paving or reclassification varies.
- **An instrument for location.** Least-cost or straight-line routes between large cities, excluding the endpoint areas ("inconsequential units"). This is an established design for road placement *(recalled; the specific references are to be added)*.

### Spillovers and inference

- **Spillovers:** market-access changes reach far beyond the road. Distance bands and the market-access treatment test for this; units near a treated unit are excluded from its controls.
- **Inference:**
  - standard errors robust to spatial correlation (Conley), and clustering by road project or admin-2 unit;
  - randomisation inference with placebo road networks;
  - multiple-testing control across crops and outcomes.

### Gate C

A result is labelled causal only if all of these pass; otherwise it is reported as an association.

1. Pre-event coefficients are jointly insignificant and small relative to the effect.
2. Placebo events (mapping bursts, random roads) show no effect of comparable size.
3. The effect keeps its sign and is of similar size under at least two control definitions and both treatment versions (total and road-only).
4. Confirmed-construction events and the long-difference design give the same sign.

## Covariates and confounders

Every covariate has one primary source and one alternative, as in the earlier design. All are time-varying where possible.

| Variable | Primary | Alternative |
| --- | --- | --- |
| Rainfall | CHIRPS v3.0 (0.05°, 1981–present, CC BY 4.0; v2.0 only through 2026) | ERA5-Land |
| Temperature | ERA5-Land | MODIS land surface temperature |
| Conflict | ACLED (free registration; event-level data needs a research tier; no redistribution of raw data) | UCDP-GED 26.1 (CC BY 4.0) |
| Population | GHS-POP R2023A (5-year epochs) | WorldPop Global2 R2025A (annual 2015–2030; alpha release) |
| Prices | FEWS NET price bulletins | WFP VAM |
| Protected areas | WDPA | — |
| Soils | iSDAsoil (30 m; weak in dense Central African forest) | SoilGrids 2.0 (250 m) |
| Irrigation | WorldCereal 2021 irrigation | FAO global irrigated areas |
| Logging concessions | GFW managed forest concessions v2025 (Cameroon, CAR, DRC, Equatorial Guinea, Gabon, Rep. Congo; Gabon view-only) | WRI national Forest Atlases |
| Governance | WGI Control of Corruption (as in v3) | — |

Checked against the providers on 2026-10-27. Other rows (ERA5-Land, MODIS LST, FEWS NET, WFP VAM, WDPA, WorldCereal irrigation, FAO GMIA v5) are available as listed, with these restrictions:
- **FEWS NET** prices have 2025 gaps that cannot be backfilled.
- **WFP VAM** update status could not be read.
- **WDPA** forbids redistribution and commercial use.
- **WorldCereal** irrigation covers 2021 only.

The covariate rows are now checked, with the restrictions above.

## Default thresholds (proposed, to be approved before any outcome data are examined)

Each threshold has a default, a reason and a sensitivity range. Once approved they are frozen, and changes after outcomes are seen are reported as deviations.

| Item | Default | Rationale | Sensitivity |
| --- | --- | --- | --- |
| Access event | Travel time to cities_11 falls by ≥ 20% **and** ≥ 15 min, and stays below for ≥ 2 years | 15 min exceeds the noise from re-tagging one road class within a 1 km cell; 20% stops very remote cells from dominating; persistence removes edit-and-revert noise | 10% / 10 min; 30% / 30 min |
| Mapping burst | Per 0.1° cell-year: ≥ 25 km of new highway ways with ≥ 80% of the length from ≤ 3 users or changesets, or any changeset tagged with a HOT project hashtag or `data_used` MapWithAI/Esri | Signatures of campaigns and AI-assisted imports in the changeset tags; tunable on known HOT projects | 10 km; 50 km |
| Imagery confirmation | Construction signal in years *t*−2 to *t* (OSM year *t*) | Mapping usually lags construction and rarely precedes it | *t*−3 to *t*+1 |
| Gate T | ≥ 60% of new and upgraded road events confirmed per zone, and ≤ 50% of events inside mapping bursts | Above 60%, misdated events dilute event-study estimates without overturning them; below it, only the long-term analysis is used | 50%; 70% |
| Gate A | User's and producer's accuracy ≥ 70% for the gain and conversion classes per zone; 95% CI half-width ≤ 15 points; ≥ 50 sample points per change class per zone | Change classes are far less accurate than overall accuracy; 70% is a common floor for change maps | 60%; 80% |
| Phase 2a alignment | Within 25% level; anomaly r ≥ 0.6; bias ≤ 20%; ≥ 5 overlapping seasons | Kept from the earlier design | 15% / 35% (trade-off curve) |
| Minimum footprints (Phase 2b) | ≥ 30 footprints over ≥ 3 seasons per crop | Minimum for stable leave-one-season-out validation | 20; 50 |
| Sensor agreement | Seasonal-feature r ≥ 0.9; zone bias ≤ 0.05 NDVI | Near published Sentinel-2/MODIS agreement; small relative to seasonal amplitude (~0.3–0.5) | r ≥ 0.8 |
| Gate B | Kept from the earlier design (RMSE −15% vs best baseline; anomaly R² ≥ 0.3; stable sign; held-out zone skill) | — | — |
| LSMS EA observation | ≥ 5 households and ≥ 8 plots per EA × crop × season; EA in ≥ 2 waves of one continuous panel segment | Keeps the EA ratio estimate stable while retaining most rural EAs (10–12 households sampled per EA) | 3 / 5; 8 / 12 |
| Matching balance | Standardised mean difference < 0.1 on every matching variable | Standard balance criterion | < 0.2 |
| Spatial bands | Treated 0–5 km from a new segment; control 10–30 km; 5–10 km excluded | Separates direct effects from local spillovers | 0–3 / 15–40 km |
| Inference | Conley standard errors, 50 km cutoff; Benjamini–Hochberg q = 0.10 across crops and outcomes | Spatial correlation of outcomes; many crops and outcomes tested | 25 km; 100 km |
| Gate C | Pre-period joint test p > 0.10 and every pre coefficient < ⅓ of the post effect; placebo effect not significant and < ½ of the main estimate; same sign under ≥ 2 control definitions and in the long-term analysis | Makes the causal label hard to earn | — |

## Pilot selection rule and compute platform

- **Pilot (rule-based; NDVI tier only).** For each crop:
  - rank agro-ecological zones by the number of footprints passing Phases 2a and 2b;
  - keep the top three, plus the lowest-density zone that still has ≥ 30 footprints;
  - hold out one further qualifying zone, drawn at random with a recorded seed.
  - The land-use and access analyses use all zones.
- **Compute.** Everything runs on the HPC node (90 cores, ~485–533 GB RAM, ~25 TB disk), with the same script conventions as `global_accessibility_v3.py`. Earth Engine is used only for spot checks.

## LSMS-ISA data inventory (author's local files)

The author holds the LSMS zips listed in `sources.csv`, at Windows OneDrive paths. They must be copied to the HPC before use.

- **Enabled and usable for EA panels:**
  - Ethiopia 2011, 2013, 2018, 2021;
  - Nigeria GHS-Panel W1–W4 (2010, 2012, 2015, 2018);
  - Tanzania NPS 2010, 2012, 2014, 2020;
  - Uganda UNPS 2010, 2011, 2013, 2015, 2018, 2019;
  - Niger ECVMA 2011, 2014 and EHCVM 2018, 2021;
  - Mali EHCVM 2018, 2021 (EAC-I 2014/2017 are cross-sections);
  - Burkina Faso EHCVM 2018, 2021.
- **Additional EHCVM countries:** Benin, Côte d'Ivoire, Guinea-Bissau, Senegal, Togo (2018 and 2021). Whether their 2021/22 round revisits the 2018/19 clusters, as in Mali and Burkina Faso, is to be checked.
- **Gaps that break panel segments:**
  - Ethiopia 2015 is disabled; it is needed for the 2011–2015 segment.
  - Malawi: the IHPS panel releases (2010–2013, 2016, 2019) are absent or disabled. IHS-III, IV and V are cross-sections, apart from their panel subsamples, so the Malawi panel needs IHPS catalog 2248 and 3819.
  - Tanzania 2008 is disabled; it is needed for the 2008–2012 cohort.
  - Nigeria Wave 5 (2023/24, catalog 6410) is not listed.
  - Uganda 2009/10 is disabled.
  - Côte d'Ivoire EHCVM 2018 is disabled; it is needed for any CIV panel.
- **Not used:** RHoMIS (cross-sections, no EA panel), Nigeria LSS 2018, Nigeria FAMVS 2013, South Africa 1993, Côte d'Ivoire 1985/1988.

## Validation, robustness and cross-check protocol

Every primary choice is rerun with its alternatives, and a result counts as robust only if it passes a rule written down before the run. All thresholds are placeholders to fix before analysis.

| Choice | Primary | Alternatives | Decision rule |
| --- | --- | --- | --- |
| Access version | Road-only | Total (with settlement growth) | Opposite signs → report both, interpret road-only |
| Destination layer | cities_11 | cities_12; ports_5; market access (θ varied) | Report all; headline only if same sign |
| Event dating | Imagery-confirmed | All OSM events; externally dated projects | Effect shrinks to zero when unconfirmed events dominate → measurement artefact |
| Weiss completion | Off (annual); on (long-term, as in v3) | On / off | Difference > 25% → report a range |
| Treatment form | Binary event | Continuous dose | Same sign required |
| Timing design | Annual event study | Long differences | Same sign required |
| Controls | Not-yet-treated | Matched never-treated; spatial bands | Gate C, criterion 3 |
| Yield tier | Tier 2 (LSMS EA panels) | Tier 1; Tier 3 | Disagreement → report by tier, do not pool |
| EA aggregation | Ratio of sums, all plots | Households in both waves only; survey weights | Material change → report both |
| Cropland mask | GLAD stable cropland | GACED30; AFCD | As in the earlier design |
| Forest definition | Hansen 30% | Hansen 10%; TMF (humid) | As in the earlier design |

Each run, its inputs and its outcome are logged, including failed checks.

## Required changes to `global_accessibility_v3.py`

The access maps exist; the treatment layer needs four additions to the script.

1. **`--fixed-destinations <epoch>`.** Hold settlements, population weights, land cover and the governance factor at one epoch, so that the road network is the only thing changing between years. This touches `stage_friction` and `stage_traveltime`.
2. **Sequential annual runs with the Weiss completion optional per year.** `--years` already accepts any list. The completion rule in `stage_friction` needs a switch, so that annual runs can use OSM as mapped.
3. **Way-level event table from the OSM history:** first appearance, tag changes and deletions per way, aggregated per 0.01° cell and year, with user and changeset metadata where available. This is a new step next to `osm_history_plan`.
4. **Store entries for the treatment.** Event class and year per cell, and annual travel-time change, added to `store_items`, so that the analysis scripts read them with `load_store`.

## Limitations and risks

- **Mapping is not construction.** Even with imagery confirmation, some events will be misdated. Where Gate T fails, only long differences are interpreted.
- **Mapping effort is not random.** Campaigns follow crises, NGOs and donor interest, which can be correlated with outcomes. The placebo events test this, but do not remove it.
- **Reverse causality.** Cropland expansion and settlement attract roads. Pre-trends and pipeline controls detect this, but cannot fully rule it out.
- **Logging roads.** In humid forest, roads are often built for logging and later abandoned. Effects there are not effects of agricultural access.
- **LSMS limits.** Location displacement blurs treatment. Aggregating to EAs hides differences between households and lets EA yield move with crop and plot composition. Panels are short and cover eight countries, so external validity across Sub-Saharan Africa is limited.
- **Admin yields** mix yield change with cropland expansion onto different land, and with the provenance issues of the earlier design.
- **Short records.** The Sentinel-2 track (2017–2023) and the cropland series (2015–2024) give few post-event years for late events.
- **Prior evidence is thin.** Africa-specific evidence on roads and deforestation is mostly correlational: road density is the strongest correlate of forest loss in the Congo Basin, and road building almost always preceded local loss there.
  - The closest causal template comes from India: new rural roads had no detectable effect on forest cover, while highway upgrades had large negative effects (Asher, Garg and Novosad).
  - For yields, Ethiopian studies report productivity gains from road expansion that vary with remoteness and extension.
  - The results here should be read against these, not assumed to match them.

## Open items

Checked against providers on 2026-10-27; the remaining items need either the data in hand or a decision.

### Verified or corrected (earlier design)

- **SPAM reference years.**
  - SPAM 2010 uses 2009–2011 averages (closest years 2005–2015 where missing).
  - SPAM 2020 uses 2019–2021 averages.
  - SPAM 2017 covers 2016–2018 (an averaging statement was not found).
  - The SPAM versions are not meant to be compared across time; they are used as level checks only.
- **WorldCereal:** still 2021 only (temporary crops, maize, winter and spring cereals, active cropland, irrigation). More products are announced "by the end of 2026", including separate wheat, barley and rye, and sorghum, millet, sunflower, rapeseed and soybean. None is released yet. The classification module (openEO) and reference data 2021–2025 are available for making one's own maps.
- **GACED30:** no Africa-specific accuracy is published. Globally the overall accuracy is 0.965 (F1 0.844; user's 0.883, producer's 0.808). By agro-ecological zone, F1 ranges from 0.631 to 0.913; it is weakest in the humid tropics, through missed cropland. Phase 1 must therefore measure its accuracy in Africa itself.
- **JRC TMF:** latest version v1_2025 (1990–2025, Landsat Collection 2, 30 m).
  - **Correction:** the native spacing appears to be 1 arc-second (≈0.000269°), not the GLAD grid (0.00025°), so TMF is resampled like Hansen.
- **MODIS and VIIRS:** MOD13Q1 and MYD13Q1 were still produced in October 2026. NASA's latest schedule ends science data in February 2027 (Terra) and September 2027 (Aqua). Older pages give earlier dates.
  - Suomi NPP VIIRS products end on 2 November 2026; NOAA-21 (VJ213A1) and NOAA-20 (VJ113A1) are the successors, at 500 m.
- **Sentinel-2 L2A 2017–2018:** Digital Earth Africa serves L2A from 2017. The Earth Engine collection warns that 2017–2018 coverage is not global. ESA's Collection-1 reprocessing (2024) provides L2A from 2015 to 2021 on the Copernicus Data Space Ecosystem. Gaps are therefore a platform question, to be checked over the pilot area once it is chosen.
- **GROW-Africa provenance:**
  - Admin yields are aggregated mainly from FAOSTAT and Agro-MAPS, HarvestStat (FEWS NET) and ReSAKSS eAtlases, plus national statistics. The overlap with HarvestStat that the independence rule worried about is therefore confirmed, and shared-source labels are needed.
  - "Year" is the agricultural or harvest year; the handling of two seasons per year is not documented.
  - Point records carry a spatial precision column (km).
  - **Overlap with Tier 2:** LSMS points in GROW-Africa are jittered as above, so GROW-Africa LSMS records and Tier 2 are the same data and must not both enter an analysis.

### Verified (this revision)

- OSM history metadata and changeset join (Phase 0, mapping bursts).
- AidData and World Bank geocoded project dates (Phase 0, externally dated projects).
- LSMS-ISA panel structure, displacement and plot data (Tier 2).
- Covariate sources (covariate table).

### Still to check, from the data files once downloaded

- [ ] GeoGCDF v3: road projects as line geometries; World Bank v1.4.2: column definitions (actual versus revised end dates).
- [ ] LSMS-ISA:
  - displacement parameters in each country's Basic Information Document;
  - whether Uganda's 2013/14 refresh replaced EAs or households, and which sample the 2018/19 and 2019/20 waves use;
  - whether Niger's EHCVM 2021/22 re-interviews households;
  - Tanzania 2020/21 plot GPS values;
  - crop-module structure for Ethiopia and the EHCVM countries.
- [ ] GROW-Africa: how multiple seasons are coded; meaning of the QC flags.
- [ ] Sentinel-2 coverage over the pilot area in 2017–2018, on the chosen platform.

### Needs a test in Phase 0

- [ ] Imagery road-dating: transfer of the Valle et al. (2024) method to savanna and cropland, scored against Slagter et al. (2024).

### Needs a decision or action by the author

- [x] ACLED registration (done by the author; credentials are kept out of the repository and read from environment variables on the HPC).
- [x] Pilot subset and held-out zones: rule-based (section "Pilot selection rule").
- [x] Compute platform: HPC node.
- [ ] Approve or change the default thresholds (section "Default thresholds").
- [ ] Copy the LSMS zips to the HPC, and fill the panel gaps listed in "LSMS-ISA data inventory" (Ethiopia 2015, Malawi IHPS, Tanzania 2008, Nigeria W5, Uganda 2009, Côte d'Ivoire 2018).
- [ ] Register for Copernicus CDS (ERA5-Land) and NASA Earthdata.

## Sources

Checked on 2026-10-27 (search results and provider pages). Items tagged *(unverified)* in the text are not covered here. Sources of the earlier design (version of 27 Oct 2026) still apply and are not repeated.

- [Asher, Garg & Novosad, The ecological footprint of transportation infrastructure (India)](https://www.greenfinanceplatform.org/sites/default/files/downloads/resource/Asher_The%20Ecological%20Footprint%20of%20Transportation%20Infrastructure.pdf)
- [Kleinschroth et al. 2019, Congo Basin roads](https://mahb.stanford.edu/wp-content/uploads/2019/06/Kleinschroth-et-al.-2019-Congo-roads.pdf)
- [Review of road impacts on ecosystems in Africa, The Conversation](https://theconversation.com/africas-growing-road-network-may-affect-ecosystems-we-reviewed-the-evidence-171835)
- [Sprawling roads and tropical forest loss 2001–2020, Communications Earth & Environment 2025](https://www.nature.com/articles/s43247-025-02158-8)
- [Global impacts of transportation infrastructure on forest degradation and loss, Nature Communications 2026](https://www.nature.com/articles/s41467-026-69150-4)
- [Mapping land uses following deforestation across Africa, Scientific Reports 2024](https://www.nature.com/articles/s41598-024-52138-9)
- [Adamopoulos, Spatial integration and agricultural productivity (Ethiopia), AEJ: Macroeconomics](https://www.aeaweb.org/articles?id=10.1257%2Fmac.20200149)
- [Rural roads, agricultural extension, and productivity, Journal of Development Economics 2023](https://www.sciencedirect.com/science/article/abs/pii/S0304387823000032)
- [Gains from market integration: new rural roads in Ethiopia, Journal of Development Economics 2024](https://www.sciencedirect.com/science/article/abs/pii/S0304387824000014)
- [Rural roads, poverty, and resilience: evidence from Ethiopia, World Bank](https://openknowledge.worldbank.org/server/api/core/bitstreams/b4a8d8e9-618b-50fc-a844-d8dd663a4f9a/content)
- [Callaway, Goodman-Bacon & Sant'Anna, Difference-in-differences with a continuous treatment](https://arxiv.org/abs/2107.02637v5) and [R package contdid](https://cloud.r-project.org/web/packages/contdid/index.html)
- [Slagter et al. 2024, Congo Basin forest roads 2019–2023](https://zenodo.org/records/13739812)
- [Valle et al. 2024, Landsat-based road construction years (via DOAJ)](https://doaj.org/article/80944b2aed75473aa4e24fd862f6f11c)
- [AidData geocoded Chinese official finance to Africa](https://www.aiddata.org/data/aiddatas-chinese-official-finance-to-africa-dataset-version-1-1-1)
- [LSMS-ISA displacement of enumeration-area coordinates (research paper)](https://arxiv.org/pdf/2409.07506) and [World Bank data blog](https://blogs.worldbank.org/en/opendata/exploring-youth-s-role-and-engagement-african-rural-economies)
- [Temporal accuracy of OpenStreetMap, State of the Map 2021](https://api.media.ccc.de/v/sotm2021-academic-10398-towards-understanding-the-temporal-accuracy-of-openstreetmap-a-quantitative-experiment)
- [OpenStreetMap planet and changeset files](https://planet.openstreetmap.org/)
- [OSM full-history planet](https://wiki.openstreetmap.org/wiki/Planet.osm/full), [Geofabrik metadata note](https://download.geofabrik.de/technical.html) and [changeset tags](https://wiki.openstreetmap.org/wiki/Changeset)
- [AidData Geospatial GCDF v3](https://www.aiddata.org/data/aiddatas-geospatial-global-chinese-development-finance-dataset-version-3-0) and [data repository](https://github.com/aiddata/gcdf-geospatial-data)
- [World Bank Geocoded Research Release v1.4.2](https://www.aiddata.org/data/world-bank-geocoded-research-release-level-1-v1-4-2)
- LSMS-ISA study pages, World Bank Microdata Library: [Ethiopia ESS 2018/19](https://microdata.worldbank.org/index.php/catalog/3823), [Nigeria GHS W4](https://microdata.worldbank.org/index.php/catalog/3557), [Tanzania NPS 2014/15](https://microdata.worldbank.org/index.php/catalog/2862), [Uganda UNPS 2015/16](https://microdata.worldbank.org/index.php/catalog/3460), [Malawi IHPS 2019](https://microdata.worldbank.org/index.php/catalog/3819), [Burkina Faso EHCVM 2021/22](https://microdata.worldbank.org/index.php/catalog/6224)
- [CHIRPS v3](https://www.chc.ucsb.edu/data/chirps3), [UCDP downloads](https://ucdp.uu.se/downloads/), [ACLED EULA](https://acleddata.com/eula/), [WorldPop](https://hub.worldpop.org/), [WDPA legal](https://www.protectedplanet.net/en/legal), [GFW managed forests](https://data-api.globalforestwatch.org/dataset/gfw_managed_forests)
- [SPAM 2010, ESSD](https://essd.copernicus.org/articles/12/3545/2020/), [SPAM 2017 Dataverse](https://doi.org/10.7910/DVN/FSSKBW), [WorldCereal global maps](https://esa-worldcereal.org/en/products/global-maps), [GACED30](https://essd.copernicus.org/articles/18/7071/2026/), [JRC TMF data](https://forobs.jrc.ec.europa.eu/TMF/data.php), [Terra end of mission](https://science.nasa.gov/science-research/earth-science/terra-the-end-of-an-era/), [Sentinel-2 Collection 1](https://sentinels.copernicus.eu/-/sentinel-2-collection-1-products-availability), [GROW-Africa paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC12215972/)

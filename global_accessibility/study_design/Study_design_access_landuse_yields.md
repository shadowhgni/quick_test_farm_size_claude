# Study design: accessibility change, land-use change and crop yields in Sub-Saharan Africa

Revision of "NDVI-based crop yield estimation and land-use change in Sub-Saharan Africa" (27 Oct 2026) · @Deo-Gratias Judrita Mawugnon HOUGNI

## What changed in this revision

The study now asks whether changes in travel time to cities and markets are associated with, and where the evidence allows, cause forest conversion to cropland and yield change. The earlier land-use mapping and NDVI yield work become outcome layers for that question.

- **New treatment layer.** Annual travel-time maps for 2015–2026 come from `global_accessibility_v3.py`, plus a road-only version with destinations held fixed. A long-term level uses 2015, 2020 and 2025.
- **The treatment is dated and checked before any outcome is examined.** The year a road appears in OpenStreetMap (OSM) is the year it was mapped, not necessarily the year it was built.
- **Yields come in three tiers:**
  1. Admin panels (HarvestStat, GROW-Africa);
  2. LSMS-ISA household and plot panels;
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
| E2b | Yield, households and plots | LSMS-ISA plot or household × crop × season | Access change around the enumeration area | Survey waves 2008–2024 |
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
   - Burst thresholds are fixed in advance. *(unverified: whether the public full-history planet carries user and changeset IDs; if not, the separate changeset dump on planet.openstreetmap.org is joined by changeset ID.)*
3. **Imagery confirmation.** A new-way or upgrade event is confirmed when a road-construction signal appears in the 1–2 years before or at the OSM date:
   - in Landsat or Sentinel-2 time series along the segment: a bare-soil fraction jump, or a new linear feature;
   - the model is the Landsat road-dating method of Valle et al. (2024), developed on the Transamazon highway.
   - The ground check for the method is the Congo Basin forest-road dataset (Slagter et al. 2024), which gives the month of opening for 46,311 km of roads built 2019–2023.
4. **Externally dated projects.** These form a subsample with independent timing and planned location:
   - World Bank geocoded projects, *(unverified: release and fields)*;
   - AidData geocoded Chinese official finance (Africa 2000–2012, global 2000–2014; whether completion dates are included is to be checked in the codebook).
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

### Tier 2: LSMS-ISA household and plot panels (E2b)

- **Countries and waves:**
  - Eight LSMS-ISA countries: Burkina Faso, Ethiopia, Malawi, Mali, Niger, Nigeria, Tanzania and Uganda. The country list is from World Bank presentations and is to be checked against the Microdata Library for each panel.
  - Only panels that revisit the same households across years with access change between waves are used.
- **Location:**
  - Public files give enumeration-area coordinates, displaced by up to 2 km (urban) or 5 km (rural). *(Offsets from a World Bank blog and a research paper; check each country's documentation.)*
  - The treatment is the mean access change over a 5 km disc around the displaced point. The bias this introduces is estimated by simulating the displacement on the access maps.
  - Restricted-access true coordinates are requested where the World Bank allows it.
- **Outcomes:**
  - Plot yield per crop: production / GPS-measured area, with GPS area preferred over self-reported area, which diverges strongly in validation studies.
  - Household value of output per hectare.
- **Mechanisms:** fertiliser and improved seed use, hired labour, share of output sold, crop choice, input and output prices, and extension contact.
  - Extension contact matters because Ethiopian evidence suggests roads and extension complement each other.
- **Fixed effects:** plot (or household × parcel) fixed effects absorb soil and management. Wave × region fixed effects absorb weather and price shocks.

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
| Rainfall | CHIRPS | ERA5-Land |
| Temperature | ERA5-Land | MODIS land surface temperature |
| Conflict | ACLED | UCDP-GED |
| Population | GHS-POP (epochs) | WorldPop |
| Prices | FEWS NET price bulletins | WFP VAM |
| Protected areas | WDPA | — |
| Soils | iSDAsoil | SoilGrids |
| Irrigation | WorldCereal 2021 irrigation | FAO global irrigated areas |
| Logging concessions | Congo Basin concession maps *(source to confirm)* | — |
| Governance | WGI Control of Corruption (as in v3) | — |

Sources in this table have not yet been checked against the providers and count as *(unverified)* until then.

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
| Yield tier | Tier 2 (LSMS) | Tier 1; Tier 3 | Disagreement → report by tier, do not pool |
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
- **LSMS limits.** Location displacement blurs treatment. Panels are short and cover eight countries, so external validity across Sub-Saharan Africa is limited.
- **Admin yields** mix yield change with cropland expansion onto different land, and with the provenance issues of the earlier design.
- **Short records.** The Sentinel-2 track (2017–2023) and the cropland series (2015–2024) give few post-event years for late events.
- **Prior evidence is thin.** Africa-specific evidence on roads and deforestation is mostly correlational: road density is the strongest correlate of forest loss in the Congo Basin, and road building almost always preceded local loss there.
  - The closest causal template comes from India: new rural roads had no detectable effect on forest cover, while highway upgrades had large negative effects (Asher, Garg and Novosad).
  - For yields, Ethiopian studies report productivity gains from road expansion that vary with remoteness and extension.
  - The results here should be read against these, not assumed to match them.

## Open items to verify before starting

- [ ] Whether the OSM full-history planet includes user and changeset IDs; otherwise, how to join the changeset dump.
- [ ] Imagery road-dating: transfer of the Valle et al. (2024) method to African savanna and cropland contexts; accuracy against Slagter et al. (2024) road-opening dates.
- [ ] Completion dates in AidData and World Bank geocoded project data.
- [ ] LSMS-ISA: panel structure and waves per country, displacement rules, access to restricted coordinates (registration).
- [ ] Covariate sources and versions (table above).
- [ ] All placeholder thresholds: event definition, burst rule, Gate T and Gate C criteria, matching variables.
- [ ] All open items of the earlier design (GROW-Africa provenance, SPAM reference years, Sentinel-2 2017–2018 coverage, WorldCereal 2024/2025, GACED30 accuracy for Africa, TMF grid, thresholds, pilot definition, compute platform).

## Sources

Checked through search results on 2026-10-27. Items tagged *(unverified)* in the text are not covered here. Sources of the earlier design (version of 27 Oct 2026) still apply and are not repeated.

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

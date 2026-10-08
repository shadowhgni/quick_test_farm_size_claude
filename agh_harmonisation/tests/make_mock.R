# Builds a small mock project (LSMS-like zip + DDI, French codebook, RHoMIS-like
# wide file, Carob-like terminag file) under `root`. Used by tests/run_mock_test.R.
library(haven); library(dplyr)
d <- file.path(root, "data"); dir.create(file.path(d, "lsms"), recursive = TRUE, showWarnings = FALSE)
lab <- function(x, l) labelled(x, l)
set.seed(1)
hh <- tibble(case_id = c("A1","A2","A3"), hh_wgt = c(100,120,90),
             region = lab(c(1,2,2), c(North=1, South=2)), ea_id = c("e1","e2","e2"))
attr(hh$case_id,"label") <- "Unique Household Identifier"; attr(hh$hh_wgt,"label") <- "Household sampling weight"
plots <- tibble(case_id = c("A1","A1","A2","A3"), gardenid = c(1,1,1,1), plotid = c(1,2,1,1),
                ag_c04a = c(1.5, 0.5, 2, 1), ag_c04b = lab(c(1,1,2,3), c(ACRE=1, HECTARE=2, "SQUARE METERS"=3)),
                ag_c04c = c(1.2, NA, 1.8, NA))
plotd <- tibble(case_id = c("A1","A1","A2","A3"), gardenid = 1, plotid = c(1,2,1,1),
                ag_d14 = lab(c(1,2,1,1), c(CULTIVATED=1, "LEFT FALLOW"=2, "RENTED OUT"=3)),
                ag_d36 = lab(c(1,2,1,2), c(YES=1, NO=2)), ag_d37a = c(200, NA, 3, NA),
                ag_d37b = lab(c(1,NA,4,NA), c(KILOGRAM=1, "OX CART"=4)),
                ag_d38 = lab(c(1,2,1,1), c(YES=1, NO=2)),
                ag_d39a = lab(c(1,NA,2,1), c("NPK (23:21:0+4S/CHITOWE)"=1, UREA=2)),
                ag_d39c = c(50, NA, 25, 100), ag_d39d = lab(c(1,NA,1,5), c(KILOGRAM=1, "50 KG BAG"=5)),
                ag_d40a = lab(c(2,NA,NA,NA), c("NPK (23:21:0+4S/CHITOWE)"=1, UREA=2)), ag_d40c = c(50,NA,NA,NA),
                ag_d40d = lab(c(1,NA,NA,NA), c(KILOGRAM=1)))
crops <- tibble(case_id = c("A1","A1","A2","A3"), gardenid = 1, plotid = c(1,1,1,1),
                crop_code = lab(c(1,11,1,5), c("MAIZE LOCAL"=1, "GROUNDNUT CG7"=11, "PIGEONPEA"=5)),
                ag_g13a = c(500, 80, 1200, 300), ag_g13b = lab(c(1,1,2,1), c(KILOGRAM=1, "50 KG BAG"=2)))
lv <- tibble(case_id = c("A1","A1","A2","A3","A3"),
             ag_r0a = lab(c(301,302,307,301,311), c("CALF"=301, "STEER/HEIFER"=302, "GOAT"=307, "LOCAL HEN"=311)),
             ag_r02 = c(2, 3, 5, 1, 12), ag_r17 = c(0,1,2,0,3))
write_dta(hh, file.path(d,"lsms","hh_mod_a_filt.dta")); write_dta(plots, file.path(d,"lsms","ag_mod_c.dta"))
write_dta(plotd, file.path(d,"lsms","ag_mod_d.dta")); write_dta(crops, file.path(d,"lsms","ag_mod_g.dta"))
write_dta(lv, file.path(d,"lsms","ag_mod_r1.dta"))
old <- setwd(d); utils::zip("lsms_mock.zip", list.files("lsms", full.names = TRUE), flags = "-q"); setwd(old)

# French-labelled DDI-only study (catalog coverage) + DDI for the mock LSMS
ddi <- function(title, files, vars) paste0('<?xml version="1.0" encoding="UTF-8"?>\n<codeBook xmlns="ddi:codebook:2_5" version="2.5"><stdyDscr><citation><titlStmt><titl>', title,
  '</titl><IDNo>X</IDNo></titlStmt></citation><stdyInfo><sumDscr><collDate date="2019-04-01"/><nation>Malawi</nation></sumDscr></stdyInfo></stdyDscr>',
  files, '<dataDscr>', vars, '</dataDscr></codeBook>')
f <- function(id, n, desc) sprintf('<fileDscr ID="%s"><fileTxt><fileName>%s.dta</fileName><fileCont>%s</fileCont></fileTxt></fileDscr>', id, n, desc)
v <- function(n, file, l, cats = NULL) sprintf('<var ID="V%s" name="%s" files="%s"><labl>%s</labl>%s</var>', n, n, file, l,
  if (is.null(cats)) "" else paste(sprintf('<catgry><catValu>%s</catValu><labl>%s</labl></catgry>', cats, names(cats)), collapse = ""))
files <- paste0(f("F1","hh_mod_a_filt","Household identification"), f("F2","ag_mod_c","Plot roster"), f("F3","ag_mod_d","Plot details rainy season"),
               f("F4","ag_mod_g","Crops rainy season"), f("F5","ag_mod_r1","Livestock"))
vars <- paste0(
  v("case_id","F1","Unique Household Identifier"), v("hh_wgt","F1","Household sampling weight"), v("region","F1","Region"), v("ea_id","F1","Enumeration area ID"),
  v("case_id","F2","Unique Household Identifier"), v("gardenid","F2","Garden ID"), v("plotid","F2","Plot ID"),
  v("ag_c04a","F2","What is the area of this plot according to the farmer?"), v("ag_c04b","F2","Area unit (farmer estimate)", c(ACRE=1,HECTARE=2)),
  v("ag_c04c","F2","GPS area of plot (acres)"),
  v("case_id","F3","Unique Household Identifier"), v("gardenid","F3","Garden ID"), v("plotid","F3","Plot ID"),
  v("ag_d14","F3","What was the main use of this plot?", c(CULTIVATED=1,"LEFT FALLOW"=2)),
  v("ag_d36","F3","Did you use any organic fertilizer on this plot?"), v("ag_d37a","F3","Quantity of organic fertilizer applied"),
  v("ag_d37b","F3","Unit of organic fertilizer quantity"), v("ag_d38","F3","Did you use any inorganic fertilizer on this plot?"),
  v("ag_d39a","F3","Type of inorganic fertilizer (first)"), v("ag_d39c","F3","Quantity of inorganic fertilizer applied (first)"),
  v("ag_d39d","F3","Unit of inorganic fertilizer quantity (first)"),
  v("ag_d40a","F3","Type of inorganic fertilizer (second)"), v("ag_d40c","F3","Quantity of inorganic fertilizer applied (second)"),
  v("ag_d40d","F3","Unit of inorganic fertilizer quantity (second)"),
  v("case_id","F4","Unique Household Identifier"), v("gardenid","F4","Garden ID"), v("plotid","F4","Plot ID"), v("crop_code","F4","Crop code"),
  v("ag_g13a","F4","Quantity harvested"), v("ag_g13b","F4","Harvest unit"),
  v("case_id","F5","Unique Household Identifier"), v("ag_r0a","F5","Livestock code"),
  v("ag_r02","F5","How many of these animals does the household currently own?"), v("ag_r17","F5","How many were sold in the last 12 months?"))
dir.create(file.path(root, "agh_meta/ddi"), recursive = TRUE, showWarnings = FALSE)
writeLines(ddi("Mock Integrated Household Survey 2019", files, vars), file.path(root, "agh_meta/ddi/wb_9001.xml"))
fr_files <- paste0(f("F1","s16a_me_bfa","Superficie des parcelles"), f("F2","s17_me_bfa","Elevage"))
fr_vars <- paste0(v("grappe","F1","Grappe"), v("menage","F1","Numero du menage"), v("s16aq02","F1","Identifiant de la parcelle"),
  v("s16aq09a","F1","Superficie de la parcelle declaree"), v("s16aq09b","F1","Unite de superficie"), v("s16aq10","F1","Superficie mesuree GPS (ha)"),
  v("s16aq17","F1","Mode d acquisition de la parcelle"), v("s16aq30","F1","Avez-vous utilise de la fumure organique sur cette parcelle?"),
  v("s16aq20","F1","La parcelle est-elle en jachere?"),
  v("s17q02","F2","Code de l espece animale"), v("s17q05","F2","Nombre de tetes possedees actuellement"))
writeLines(sub("Malawi","Burkina Faso", ddi("Enquete Harmonisee sur le Conditions de Vie des Menages 2018", fr_files, fr_vars)),
           file.path(root, "agh_meta/ddi/wb_9002.xml"))
readr::write_csv(tibble(server="wb", base_url="https://microdata.worldbank.org", id=c("9001","9002"), idno=c("MOCK1","MOCK2"),
  title=c("Mock Integrated Household Survey 2019","Enquete Harmonisee 2018"), country=c("Malawi","Burkina Faso"),
  year_start=c("2019","2018"), year_end=c("2020","2019"),
  ddi_file=c(file.path(root, "agh_meta/ddi/wb_9001.xml"),file.path(root, "agh_meta/ddi/wb_9002.xml")), ddi_ok=TRUE),
  file.path(root, "agh_meta/study_catalog.csv"))

# RHoMIS-like wide file + table dictionary
rh <- tibble(id_unique = c("r1","r2"), hh_size_members = c(5, 7),
  crop_name_1 = c("maize","beans"), crop_harvest_kg_per_year_1 = c(400, 60), crop_name_2 = c("cassava", NA), crop_harvest_kg_per_year_2 = c(900, NA),
  livestock_name_1 = c("cattle","goats"), livestock_heads_1 = c(4, 6), livestock_name_2 = c("chicken", NA), livestock_heads_2 = c(20, NA))
readr::write_csv(rh, file.path(d, "rhomis_processed.csv"))
readr::write_csv(tibble(name = names(rh), description = c("Unique household id", "Household size (members)",
  rep(c("Crop name", "Crop harvest quantity (kg per year)"), 2), rep(c("Livestock type", "Number of livestock heads"), 2))),
  file.path(d, "rhomis_dictionary.csv"))

# Carob-like terminag file
readr::write_csv(tibble(hhid = c("c1","c1","c2"), plot_id = c("p1","p2","p1"), crop = c("maize","maize","sorghum"),
  yield = c(3200, 2500, 900), OM_used = c(TRUE, FALSE, TRUE), OM_type = c("farmyard manure", NA, "compost"), OM_amount = c(5000, NA, 2500),
  fertilizer_amount = c(150, 100, 0), plot_area = c(100, 80, 120), country = "Kenya"), file.path(d, "carob_mock.csv"))

# Files for a local mock NADA server (step 1 test): search + DDI export + AGM pointer
nd <- file.path(root, "nada")
dir.create(file.path(nd, "index.php/api/catalog"), recursive = TRUE, showWarnings = FALSE)
writeLines('{"result":{"found":2,"rows":[{"id":9001,"idno":"MOCK1","title":"Mock Integrated Household Survey 2019","nation":"Malawi","year_start":2019,"year_end":2020},{"id":9002,"idno":"MOCK2","title":"Enquete Harmonisee 2018","nation":"Burkina Faso","year_start":2018,"year_end":2019}]}}',
           file.path(nd, "index.php/api/catalog/search"))
for (i in c("9001", "9002")) {
  dir.create(file.path(nd, "index.php/metadata/export", i), recursive = TRUE, showWarnings = FALSE)
  file.copy(file.path(root, sprintf("agh_meta/ddi/wb_%s.xml", i)), file.path(nd, "index.php/metadata/export", i, "ddi"))
}
dir.create(file.path(nd, "agm/index.php/api/catalog"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(nd, "agm/index.php/metadata/export/994"), recursive = TRUE, showWarnings = FALSE)
writeLines('{"result":{"found":1,"rows":[{"id":994,"idno":"rwa-nisr-cdc-1978-v1","title":"NISR Central Data Catalog","nation":"Rwanda"}]}}',
           file.path(nd, "agm/index.php/api/catalog/search"))
writeLines(sprintf('<?xml version="1.0"?><codeBook xmlns="ddi:codebook:2_5"><stdyDscr><dataAccs><setAvail><accsPlac URI="%s/index.php/catalog">NISR</accsPlac></setAvail></dataAccs></stdyDscr></codeBook>',
                   Sys.getenv("NADA_MOCK_URL", "http://127.0.0.1:8765")),
           file.path(nd, "agm/index.php/metadata/export/994/ddi"))

"""Tests of access_effects_v01.py: unit tests of the treatment rules and an end-to-end run of every
stage on the regional travel-time store of the CI test (test_results/store), with small synthetic
stand-ins for the downloads (Hansen, GACED30, CHIRPS, UCDP, GeoGCDF, HarvestStat).
    cd global_accessibility/study_workflow && python -m pytest dev -q"""
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import access_effects_v01 as ae  # noqa: E402

import geopandas as gpd  # noqa: E402
import rasterio  # noqa: E402
from rasterio.transform import from_origin  # noqa: E402
from shapely.geometry import LineString, box  # noqa: E402

STORE = HERE.parents[1] / "test_results"
BBOX = (0.0, 6.0, 3.0, 9.0)


# --- treatment rules -----------------------------------------------------------------------------
def test_access_events_gain_persistence_and_loss():
    years = [2015, 2016, 2017, 2018, 2019]
    tt = np.array([[100, 100, 70, 70, 70],      # gain in 2017, persists
                   [100, 100, 70, 100, 100],    # gain reverted the next year: no event
                   [100, 90, 90, 90, 90],       # -10%: below the threshold
                   [40, 40, 30, 30, 30],        # -25% but only 10 minutes: no event
                   [100, 100, 100, 100, 70],    # gain in the last year: kept, not checked
                   [60, 60, 90, 90, 90]], np.float32)   # loss (travel time up 50%, 30 min)
    ref, chk = ae.access_events(tt, years)
    assert list(ref) == [2017, 0, 0, 0, 2019, 0]
    assert chk[0] and not chk[4]
    ref, _ = ae.access_events(tt, years, direction="loss")
    assert list(ref) == [0, 2018, 0, 0, 0, 2017]


def test_access_events_sparse_years_need_the_next_year():
    tt = np.array([[100, 70, 70], [100, 70, 100]], np.float32)
    ref, chk = ae.access_events(tt, [2015, 2020, 2025])
    assert list(ref) == [2020, 0] and chk[0]


def test_local_road_change_and_distance():
    codes = np.zeros((21, 21), np.uint8)
    codes[10, 10] = 1            # new road cell
    codes[10, 11] = 17           # new road cell inside a burst
    n, share = ae.local_road_change(codes, 2)
    assert n[10, 10] == 2 and share[10, 10] == pytest.approx(0.5)
    assert n[0, 0] == 0 and np.isnan(share[0, 0])
    g = ae.Grid(0, 1, 1 / 120, 21, 21)
    d = ae.distance_to_change(codes, g, 0, 40)
    assert d[10, 10] == 0 and d[10, 0] == pytest.approx(10 * 111.32 / 120 * np.cos(np.radians(1 - 10.5 / 120)), rel=0.02)


def test_cem_weights_balance():
    s = pd.DataFrame({"x": np.r_[np.ones(10), np.zeros(10), np.ones(30)], "w": 1.0})
    treated = np.r_[np.ones(10, bool), np.zeros(40, bool)]
    w, st = ae.cem_weights(s, treated, ["x"], bins=2)
    assert np.isnan(w[10:20]).all()                         # controls in a stratum without treated
    assert w[20:].sum() == pytest.approx(10)                # controls reweighted to the treated count


# --- synthetic inputs ------------------------------------------------------------------------------
def write_tif(path, arr, west, north, res, nodata=None, count=None):
    arr = arr if arr.ndim == 3 else arr[None]
    with rasterio.open(path, "w", driver="GTiff", height=arr.shape[1], width=arr.shape[2], count=arr.shape[0],
                       dtype=arr.dtype, crs="EPSG:4326", transform=from_origin(west, north, res, res),
                       nodata=nodata) as dst:
        dst.write(arr)


def make_inputs(root, ga_store):
    rng = np.random.default_rng(5)
    src = root / "src"
    src.mkdir()
    res = 0.005                       # coarser than Hansen (0.00025) to keep the test small
    n = int(10 / res)
    tc = np.where(rng.random((n, n)) < 0.4, 60, 5).astype(np.uint8)
    ly = np.where((tc >= 30) & (rng.random((n, n)) < 0.08), rng.integers(1, 25, (n, n)), 0).astype(np.uint8)
    tc[200:300, 400:600], ly[200:300, 400:600] = 5, 0          # a stable cropland block (lat 8.5-9, lon 2-3)
    for layer, a in (("treecover2000", tc), ("lossyear", ly), ("datamask", np.ones((n, n), np.uint8))):
        write_tif(src / Path(ae.hansen_url(layer, "10N_000E")).name, a, 0, 10, res)
    # GACED30: one 3 x 3 degree tile, 25 bands (2000-2024), cropland where loss happened 0-2 years before
    m = int(3 / res)
    tc_t, ly_t = tc[200:800, 0:m], ly[200:800, 0:m].astype(np.int32)
    crop = np.zeros((25, m, m), np.uint8)
    for b in range(25):
        y = 2000 + b
        crop[b] = np.where(((ly_t > 0) & (2000 + ly_t <= y)) | (tc_t < 30) & (rng.random((m, m)) < 0.3), 10, 0)
    crop[:, 0:100, 400:600] = 10
    write_tif(src / "Crop_0_6.tif", crop, 0, 9, res, nodata=255)
    # AFCD (annual crops only): GACED30 cropland except west of 0.5 E, where cropland is "tree crops"
    for y in range(2014, 2023):
        af = np.where(crop[y - 2000] == 10, 1, 0).astype(np.uint8)
        af[:, 0:100] = 0
        write_tif(src / f"AFCD_{y}.tif", af, 0, 9, res, nodata=3)
    # GLC_FCS30D v2 tile E0N10 (0-5 E, 5-10 N), 23 bands 2000-2022
    gt, gl_ = tc[0:1000, 0:1000], ly[0:1000, 0:1000].astype(np.int32)
    glc = np.zeros((23, 1000, 1000), np.uint8)
    for b in range(23):
        y = 2000 + b
        forest = (gt >= 30) & ((gl_ == 0) | (2000 + gl_ > y))
        lost = (gt >= 30) & (gl_ > 0) & (2000 + gl_ <= y)
        band = np.full((1000, 1000), 130, np.uint8)
        band[forest] = 52
        band[lost] = 10
        band[lost & (np.arange(1000)[None, :] < 100)] = 12
        band[200:300, 400:600] = 10
        glc[b] = band
    write_tif(src / "GLC_FCS30D_20002022_E0N10_Annual_V1.1.tif", glc, 0, 10, res)
    with zipfile.ZipFile(src / ae.glc_zip_names(0, 3)[0], "w") as zf:
        zf.write(src / "GLC_FCS30D_20002022_E0N10_Annual_V1.1.tif", "GLC_FCS30D_20002022_E0N10_Annual_V1.1.tif")
    # Masolele: land use of the forest lost 2001-2020 (cacao west of 0.5 E, small-scale cropland elsewhere)
    ms = np.where((ly_t >= 1) & (ly_t <= 20), 4, 0).astype(np.uint8)
    ms[:, 0:100] = np.where(ms[:, 0:100] > 0, 15, 0)
    write_tif(src / Path(ae.MASOLELE_URL.split("/content")[0]).name, ms, 0, 9, res)
    # Descals oil palm planting year: one year after the loss, west of 0.5 E
    yop = np.where(ly_t > 0, 2000 + ly_t + 1, 0).astype(np.uint16)
    yop[:, 100:] = 0
    write_tif(src / "GlobalOilPalm_OP-YoP_1.tif", yop, 0, 9, res)
    with zipfile.ZipFile(src / "GlobalOilPalm_OP-YoP.zip", "w") as zf:
        zf.write(src / "GlobalOilPalm_OP-YoP_1.tif", "GlobalOilPalm_OP-YoP_1.tif")
    # Earth Engine vigour exports (MODIS 2001-2024, Sentinel-2 2017-2024), 8 bands on the 30" grid
    (src / "ndvi").mkdir()
    base = rng.uniform(2.5, 3.5, (360, 360)).astype(np.float32)
    year_signal = {y: rng.normal(0, 0.1, (360, 360)).astype(np.float32) for y in range(2001, 2025)}
    for sensor, years in (("modis", range(2001, 2025)), ("s2", range(2017, 2025))):
        for y in years:
            yr = year_signal[y]                          # the same weather signal seen by both sensors
            v = base + 0.02 * (y - 2001) + yr + (rng.normal(0, 0.02, (360, 360)) if sensor == "s2" else 0)
            bands = np.stack([v, v / 4, v / 5, v * 0.6, np.full_like(v, 1.0), v * 0.8,
                              np.full_like(v, 0.8), np.full_like(v, 5.0)]).astype(np.float32)
            write_tif(src / "ndvi" / f"vigour_{sensor}_{y}.tif", bands, 0, 9, 1 / 120, nodata=-9999)
    with zipfile.ZipFile(src / ae.gaced_zip_name(0), "w") as zf:
        zf.write(src / "Crop_0_6.tif", "Crop_0_6.tif")
    for y in ae.COV_YEARS:
        write_tif(src / f"chirps-v3.0.{y}.tif", rng.uniform(600, 1400, (60, 60)).astype(np.float32), 0, 9, 0.05, nodata=-9999)
    ev = pd.DataFrame({"year": rng.integers(2001, 2025, 300), "latitude": rng.uniform(6, 9, 300),
                       "longitude": rng.uniform(0, 3, 300), "best": 1, "type_of_violence": 1})
    ev.to_csv(src / "ged.csv", index=False)
    with zipfile.ZipFile(src / Path(ae.UCDP_GED_URL).name, "w") as zf:
        zf.write(src / "ged.csv", "GEDEvent_v26_1.csv")
    proj = gpd.GeoDataFrame({"id": ["1", "2"], "Sector.Name": ["TRANSPORT AND STORAGE"] * 2,
                             "Title": ["Road upgrade", "Bridge"], "Completion.Year": [2018, 2022],
                             "Recipient.ISO-3": ["BEN", "TGO"]},
                            geometry=[LineString([(1.0, 7.0), (2.0, 7.5)]), LineString([(0.5, 8.0), (1.5, 8.2)])],
                            crs=4326)
    proj.to_file(src / "all_combined_global.gpkg")
    with zipfile.ZipFile(src / Path(ae.GCDF_URL).name, "w") as zf:
        zf.write(src / "all_combined_global.gpkg", "all_combined_global.gpkg")
    units = gpd.GeoDataFrame({"fnid": ["BJ2001A101", "BJ2001A102", "TG2001A101"], "country": ["Benin"] * 2 + ["Togo"],
                              "country_code": ["BJ", "BJ", "TG"], "admin_1": ["a", "b", "c"], "admin_2": [None] * 3},
                             geometry=[box(1.5, 6.2, 2.5, 7.5), box(1.5, 7.5, 2.5, 9.0), box(0.2, 6.2, 1.5, 9.0)],
                             crs=4326)
    units.to_file(src / Path(ae.HARVESTSTAT_GPKG_URL).name)
    rows = []
    for f in units.fnid:
        for y in range(2005, 2023):
            rows.append({"fnid": f, "country": "x", "country_code": f[:2], "admin_1": "a", "admin_2": None,
                         "product": "Maize", "season_name": "Main", "planting_year": y, "planting_month": 5,
                         "harvest_year": y, "harvest_month": 9, "crop_production_system": "All",
                         "qc_flag": 0, "area": 1000.0, "production": 1200.0, "yield": rng.uniform(0.8, 1.6)})
            rows.append(dict(rows[-1], product="Cassava", area=500.0, production=4000.0, **{"yield": 8.0}))
    pd.DataFrame(rows).to_csv(src / Path(ae.HARVESTSTAT_CSV_URL).name, index=False)
    # LSMS harmonised panel: 6 EAs x 12 households x 2 plots, waves 1-4 (Nigeria years 2010-2018)
    import pyreadstat
    pc, pl = [], []
    for ea in range(6):
        lat, lon = 6.5 + ea * 0.4, 1.0 + (ea % 3) * 0.6
        for wave in (1, 2, 3, 4):
            for hh in range(12):
                for plot in range(2):
                    pid = f"{ea}-{hh}-{plot}"
                    pc.append({"country": "Nigeria", "wave": wave, "season": 1, "plot_id_obs": pid,
                               "household_id_obs": f"{ea}-{hh}", "ea_id_obs": ea, "crop_name": "Maize",
                               "harvest_kg": float(rng.uniform(500, 2000)), "harvest_value_USD": 300.0,
                               "improved": float(rng.random() < 0.3), "lat_modified": lat + rng.normal(0, 0.01),
                               "lon_modified": lon + rng.normal(0, 0.01), "pw": 100.0})
                    pl.append({"country": "Nigeria", "wave": wave, "season": 1, "plot_id_obs": pid,
                               "plot_area_GPS": float(rng.uniform(0.3, 1.5)), "intercropped": 0.0,
                               "nb_seasonal_crop": 1.0, "inorganic_fertilizer": float(rng.random() < 0.5),
                               "total_hired_labor_days": 2.0, "share_kg_sold": 0.3, "irrigated": 0.0,
                               "plot_slope": 2.0})
    pyreadstat.write_dta(pd.DataFrame(pc), str(src / "Plotcrop_dataset.dta"))
    pyreadstat.write_dta(pd.DataFrame(pl), str(src / "Plot_dataset.dta"))
    return src


def local_download(src):
    def download(url, dest, sess=None, retries=5, headers=None):
        name = Path(url.split("/content")[0]).name.replace("%2B", "+") if "zenodo" in url else Path(url).name
        f = src / name
        if not f.exists():
            raise ae.RemoteUnavailable(f"HTTP 404 for {url}")
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            shutil.copy(f, dest)
        return dest
    return download


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if not (STORE / "store" / "manifest.json").exists():
        pytest.skip("test_results/store not found")
    root = tmp_path_factory.mktemp("ae")
    src = make_inputs(root, STORE)
    mp = pytest.MonkeyPatch()
    mp.setattr(ae, "download", local_download(src))
    mp.setattr(ae, "GA_RESULTS", [str(STORE)])
    mp.setattr(ae, "MAX_WORKERS", 2)
    mp.setattr(ae, "E1_SAMPLE_TREATED", 4000)
    mp.setattr(ae, "E1_SAMPLE_CONTROL", 4000)
    mp.setattr(ae, "CONFLICT_SOURCE", "ucdp")
    mp.setattr(ae, "BOOTSTRAP_ITERS", 99)
    mp.setattr(ae, "TMF_ENABLED", False)
    mp.setattr(ae, "NDVI_DIR", str(src / "ndvi"))
    ctx = ae.make_ctx(root / "work", root / "results", BBOX)
    want = [s for s in ae.STAGES if s not in ("estimate", "gate_c")]
    ae.run_stages(ctx, want)
    yield ctx
    mp.undo()


def test_stages_write_tables(run):
    w, r = run["work"], run["results"]
    t = pd.read_parquet(w / "treatment" / f"{run['tiles'][0]['tile']}.parquet")
    assert {"ev_roadonly_cities_11", "evclass_roadonly_cities_11", "dnew_2020"} <= set(t.columns)
    lu = pd.read_parquet(w / "landuse" / f"{run['tiles'][0]['tile']}.parquet")
    assert lu.forest2000_km2.sum() > 0 and lu.filter(like="loss_km2_").to_numpy().sum() > 0
    assert lu.filter(like="conv_km2_").to_numpy().sum() > 0
    # conversion is a subset of loss
    for y in range(2015, 2025):
        assert (lu[f"conv_km2_{y}"] <= lu[f"loss_km2_{y}"] + 1e-6).all()
    tile = run["tiles"][0]["tile"]
    cov = pd.read_parquet(w / "covariates" / f"{tile}.parquet")    # (the folder also holds conflict_events)
    assert cov.rain_2010.between(600, 1400).all() and cov.filter(like="conflict_").to_numpy().sum() > 0
    pr = pd.read_parquet(w / "projects" / f"{run['tiles'][0]['tile']}.parquet")
    assert set(pr.proj_year.unique()) >= {0, 2018}
    assert (r / "tables" / "gate_t.csv").exists()
    e1 = pd.read_parquet(r / "panels" / "e1_cells.parquet")
    assert {"id", "year", "g__roadonly_cities_11", "conv_share", "w", "w_cem", "region"} <= set(e1.columns)
    assert e1.year.min() == 2001 and e1.groupby("id").size().nunique() == 1
    assert (e1.g__roadonly_cities_11 >= -1).all()
    e2a = pd.read_parquet(r / "panels" / "e2a_admin.parquet")
    assert e2a.id.nunique() == 6 and "g__roadonly_cities_11" in e2a           # 3 units x 2 crops
    e3 = pd.read_parquet(r / "panels" / "e3_longdiff.parquet")
    assert {"E1_cells", "E2a_admin"} <= set(e3.dataset) and "d_access__roadonly_cities_11" in e3
    assert (r / "tables" / "e1_matching_balance.csv").exists()
    e2b = pd.read_parquet(r / "panels" / "e2b_ea.parquet")
    assert e2b.ea.nunique() == 6 and set(e2b.year) == {2010, 2012, 2015, 2018}
    assert {"g__roadonly_cities_11", "log_yield", "n_hh", "n_plots"} <= set(e2b.columns)
    assert "E2b_ea" in set(e3.dataset)
    # --- revision 2 -------------------------------------------------------------------------------------
    tile = run["tiles"][0]["tile"]
    la = pd.read_parquet(w / "landcover_alt" / f"{tile}.parquet").merge(lu, on="cell")
    for y in range(2015, 2022):
        split = la[f"conv_annual_km2_{y}"] + la[f"conv_tree_km2_{y}"] + la[f"conv_unres_km2_{y}"]
        ok = split.notna()
        assert np.allclose(split[ok], la.loc[ok, f"conv_km2_{y}"], atol=1e-6)      # the split is complete
    assert la.filter(like="conv_tree_km2_").to_numpy().sum() > 0 and la.filter(like="conv_annual_km2_").to_numpy().sum() > 0
    for y in range(2001, 2021):
        tot = sum(la[f"repl_{g}_km2_{y}"] for g in ae.REPL_GROUPS + ["unclassified"])
        assert np.allclose(tot.fillna(0), la[f"loss_km2_{y}"], atol=1e-6)         # every lost pixel classified once
    assert la.filter(like="repl_tree_km2_").to_numpy().sum() > 0
    assert la.filter(like="palm_after_loss_km2_").to_numpy().sum() > 0
    assert la.filter(like="glc_conv_km2_").to_numpy().sum() > 0 and la.stable2_km2.sum() > 0
    assert "conv_annual_share" in e1 and "conv_tree_share" in e1
    e1c = pd.read_parquet(r / "panels" / "e1c_replacement.parquet")
    shares = e1c[[f"repl_{g}" for g in ae.REPL_GROUPS + ["unclassified"]]].sum(axis=1)
    assert np.allclose(shares, 1, atol=1e-4) and e1c.year.max() <= 2020
    e2d = pd.read_parquet(r / "panels" / "e2d_vigour.parquet")
    assert {"ndvi_integral", "ndvi_dry_integral", "ndvi_noncrop_integral", "g__roadonly_cities_11"} <= set(e2d.columns)
    assert e2d.year.min() == 2001 and e2d.year.max() == 2024
    gv = pd.read_csv(r / "panels" / "gate_v_inputs.csv")
    assert (gv.source.str.startswith("sensor_")).any() and (gv.r_sensor.dropna() > 0.8).all()
    e2e = pd.read_parquet(r / "panels" / "e2e_admin.parquet")
    assert np.allclose(e2e.share_maize, 2 / 3) and np.allclose(e2e.share_cassava, 1 / 3)
    assert {"g__roadonly_cities_11", "shannon"} <= set(e2e.columns)
    e2e_ea = pd.read_parquet(r / "panels" / "e2e_ea.parquet")
    assert np.allclose(e2e_ea.share_maize, 1) and "share_sold" in e2e_ea


def r_ready():
    rs = shutil.which("Rscript")
    if not rs:
        return False
    r = subprocess.run([rs, "-e", "q(status = !all(vapply(c('did','fixest','nanoparquet','dplyr'), "
                        "requireNamespace, logical(1), quietly = TRUE)))"], capture_output=True)
    return r.returncode == 0


@pytest.mark.skipif(not r_ready(), reason="Rscript with did, fixest, nanoparquet, dplyr not available")
def test_estimate_recovers_simulated_effect(tmp_path):
    import simulate_panels
    p = simulate_panels.simulate(tmp_path / "panels", effect=0.02, seed=3)
    out = tmp_path / "est"
    r = subprocess.run(["Rscript", str(HERE.parent / "estimate_effects.R"), str(p), str(out)],
                       capture_output=True, text=True, timeout=1800)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    est = pd.read_csv(out / "estimates.csv")
    cs = est[(est.estimator == "cs") & (est.control == "notyettreated") & (est.term == "overall")
             & (est.spec == "roadonly_cities_11") & (est.outcome == "conv_share")]
    assert cs.estimate.iloc[0] == pytest.approx(0.02, abs=0.004)
    plc = est[(est.estimator == "cs_placebo_burst") & (est.term == "overall") & (est.outcome == "conv_share")]
    assert abs(plc.estimate.iloc[0]) < 0.004
    ld = est[(est.estimator == "longdiff") & (est.outcome == "conv_share")]
    assert ld.estimate.iloc[0] == pytest.approx(0.5, abs=0.05)
    gc = pd.read_csv(out / "gate_c.csv")
    row = gc[(gc.dataset == "E1_cells") & (gc.outcome == "conv_share")].iloc[0]
    assert bool(row.c1_pretrends) and bool(row.c2_placebo) and bool(row.c3_controls_versions)


@pytest.mark.skipif(not r_ready(), reason="Rscript with did, fixest, nanoparquet, dplyr not available")
def test_estimate_stage_on_pipeline_panels(run):
    info = ae.stage_estimate(run)
    assert info["coefficients"] > 0
    ae.stage_gate_c(run)
    assert (run["results"] / "estimates" / "gate_c.csv").exists()


def test_unit_treatment_falls_back_where_cropland_is_zero():
    sums = pd.DataFrame({"uid": [1, 1, 2, 2], "weight": ["cropland", "equal", "cropland", "equal"],
                         "w": [2.0, 10.0, 0.0, 5.0],
                         "s_tt_roadonly_cities_11_2015": [2 * np.log1p(100), 10 * np.log1p(90), 0.0, 5 * np.log1p(50)],
                         "s_tt_roadonly_cities_11_2020": [2 * np.log1p(60), 10 * np.log1p(60), 0.0, 5 * np.log1p(50)]})
    tr = ae.unit_treatment(sums, "cropland", fallback="equal").set_index("uid")
    assert tr.loc[1, "weight_used"] == "cropland" and tr.loc[2, "weight_used"] == "equal"
    assert tr.loc[1, "tt_roadonly_cities_11_2015"] == pytest.approx(100, rel=1e-4)
    assert tr.loc[1, "ev_roadonly_cities_11"] == 2019 and tr.loc[2, "ev_roadonly_cities_11"] == 0


def test_project_lines_beyond_the_tile_edge_count(tmp_path):
    g = gpd.GeoDataFrame({"project": ["1"], "iso3": ["BEN"], "completion": [2018], "start": [2015],
                          "geom_type": ["LineString"]},
                         geometry=[LineString([(1.005, 6.0), (1.005, 7.0)])], crs=4326)   # 0.55 km east of the tile
    g.to_file(tmp_path / "p.gpkg")
    res = 1 / 120
    t = pd.DataFrame({"cell": [1, 2], "row": [10, 10], "col": [119, 60]})   # a cell at the east edge, one inside
    t.to_parquet(tmp_path / "t.parquet")
    job = {"tile": "x", "win": (0, 0, 120, 120), "treatment": str(tmp_path / "t.parquet"),
           "transform": from_origin(0.0, 7.0, res, res), "shape": (120, 120), "res": res, "north": 7.0,
           "bounds_halo": (-0.1, 5.9, 1.1, 7.1), "projects": str(tmp_path / "p.gpkg"),
           "out": str(tmp_path / "o.parquet")}
    ae.projects_job(job)
    o = pd.read_parquet(tmp_path / "o.parquet")
    assert list(o.proj_year) == [2018, 0]


@pytest.mark.skipif(not r_ready(), reason="Rscript with did, fixest, nanoparquet, dplyr not available")
def test_crop_mix_shift_labels_yield_composite(tmp_path):
    import simulate_panels
    p = simulate_panels.simulate(tmp_path / "panels", effect=0.05, seed=4, n=300, mix_shift=0.10)
    out = tmp_path / "est"
    r = subprocess.run(["Rscript", str(HERE.parent / "estimate_effects.R"), str(p), str(out)],
                       capture_output=True, text=True, timeout=1800)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    est = pd.read_csv(out / "estimates.csv")
    mix = est[(est.dataset == "E2e_admin") & (est.outcome == "share_maize") & (est.estimator == "cs")
              & (est.control == "notyettreated") & (est.term == "overall")]
    assert mix.estimate.iloc[0] == pytest.approx(0.10, abs=0.01)
    gc = pd.read_csv(out / "gate_c.csv")
    row = gc[(gc.dataset == "E2a_admin") & (gc.outcome == "log_yield")].iloc[0]
    assert bool(row.crop_mix_shift) and "composite" in row.label
    assert (out / "gate_v.csv").exists()


def test_vigour_nodata_without_tag_is_nan(tmp_path, monkeypatch):
    """Earth Engine exports may carry no nodata tag: -9999 must still read as missing, not as a value."""
    d = tmp_path / "ndvi"; d.mkdir()
    bands = np.full((8, 12, 12), 3.0, np.float32)
    bands[:, :6, :] = -9999.0
    write_tif(d / "vigour_modis_2020.tif", bands, 0, 1, 1 / 12, nodata=None)
    monkeypatch.setattr(ae, "NDVI_DIR", str(d))
    pd.DataFrame({"cell": [1, 2], "row": [0, 11], "col": [0, 0]}).to_parquet(tmp_path / "t.parquet")
    job = {"tile": "x", "win": (0, 0, 12, 12), "treatment": str(tmp_path / "t.parquet"),
           "transform": from_origin(0, 1, 1 / 12, 1 / 12), "shape": (12, 12), "inventory": ae.vigour_inventory(),
           "out": str(tmp_path / "o.parquet")}
    ae.ndvi_job(job)
    o = pd.read_parquet(tmp_path / "o.parquet")
    assert np.isnan(o.ndvi_integral_modis_2020[0]) and o.ndvi_integral_modis_2020[1] == 3.0
    # a later export (another sensor) makes the tile table be rebuilt
    write_tif(d / "vigour_s2_2020.tif", bands, 0, 1, 1 / 12, nodata=None)
    job["inventory"] = ae.vigour_inventory()
    ae.ndvi_job(job)
    assert "ndvi_integral_s2_2020" in pd.read_parquet(tmp_path / "o.parquet")

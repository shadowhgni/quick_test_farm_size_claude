Every grid of the run, as Cloud Optimized GeoTIFFs on the 30 arc-second grid (EPSG:4326).
manifest.json lists each file with its year, layer, units, data type and nodata value.
Travel times are in traveltime/<year>/<layer>.tif (float32 minutes, full precision; -9999 =
unreachable). Read them with load_store() from global_accessibility_v3.py, e.g.
    arr, profile = load_store('ga_results', 'friction', 2020)
    arr, profile = load_store('ga_results', 'traveltime', 2026, 'cities_11', bbox=(-1, 5.5, 4.5, 13.5))
or with any GIS (rasterio, terra, QGIS). Tables (countries, settlements, corruption,
checkpoints, OSM plan) are in tables/.

# Quickstart

## Installation

```sh
pip install road-centerline

# Optional: to_networkx() support
pip install road-centerline[network]
```

## CLI usage

```sh
road-centerline Road.shp Road_Centerline.shp --densify-distance 10
```

Build a connected network instead of disconnected per-polygon lines:

```sh
road-centerline Road.shp Road_Centerline.gpkg --build-network --snap-tolerance 1.0
```

Run `road-centerline --help` for all options, including `--target-crs`,
`--assume-crs`, `--no-densify`, `--on-error`, `--n-jobs`,
`--build-network`/`--snap-tolerance`, and the `pygeoops.centerline`
pass-through options (`--extend`, `--min-branch-length`,
`--simplify-tolerance`, `--pygeoops-densify-distance`).

## Python API

```python
from road_centerline import process_file

process_file("Road.shp", "Road_Centerline.shp", densify_distance=10.0)
```

Or work with a `GeoDataFrame` directly:

```python
import geopandas as gpd
from road_centerline import compute_centerlines

gdf = gpd.read_file("Road.shp")
centerlines = compute_centerlines(gdf, densify_distance=10.0)
centerlines.to_file("Road_Centerline.shp")
```

## CRS handling

Distance-based operations (densifying by a fixed distance, computing a
centerline, attribute/network computation) only make sense in a
metric/projected CRS. `road-centerline` resolves a working CRS as follows:

1. If the input has no CRS, you must pass `assume_crs` (Python API) /
   `--assume-crs` (CLI) to state what CRS the coordinates are actually in.
   This is a hard error otherwise — silently guessing would risk producing
   plausible-looking but wrong output.
2. If `target_crs` / `--target-crs` is given, it's used for the working math.
3. Otherwise, if the CRS is geographic, a local UTM zone is auto-selected via
   `GeoDataFrame.estimate_utm_crs()`.
4. Otherwise (already projected), the input CRS is used as-is.

The output is always reprojected back to match the input's original CRS.
`length`/`est_width` are in the working CRS's linear unit (meters, under
auto-UTM). [`build_network()`](network.md)'s `snap_tolerance` is a distance
in whatever CRS you pass it — pass metric-CRS centerlines, not reprojected
geographic ones.

## Supported formats

Any format geopandas can read/write via its I/O backend (pyogrio), inferred
from the file extension — including `.shp`, `.geojson`, and `.gpkg`.

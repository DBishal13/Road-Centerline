# road-centerline

Extract road centerlines from polygon geometries (road contours) — worldwide,
in any input CRS, in any format geopandas can read or write.

Given a polygon representing a road's outline, `road-centerline` optionally
densifies its edges (adding vertices so long, straight edges don't starve the
skeletonization algorithm of detail) and then computes the medial-axis
centerline using [`pygeoops.centerline`](https://pygeoops.readthedocs.io/en/stable/api/pygeoops.centerline.html).

## Features

- **CRS-aware, globally**: if the input CRS is geographic (e.g. WGS84
  lat/lon), distances are computed in an automatically-estimated local UTM
  zone, then the result is reprojected back to the original CRS. Works
  anywhere on Earth — no manual projection setup required. A CRS is always
  required (see [CRS handling](#crs-handling) below).
- **Any format geopandas supports**: Shapefile, GeoJSON, GeoPackage, and more
  — the format is inferred from the file extension.
- **Vectorized**: geometry densification is vectorized with numpy, and
  centerlines are computed for an entire layer in a single `pygeoops.centerline`
  call rather than row by row.
- **CLI and Python API**: use it as a command-line tool or import it as a
  library.

## Installation

```sh
pip install road-centerline
```

## CLI usage

```sh
road-centerline Road.shp Road_Centerline.shp --densify-distance 10
```

Run `road-centerline --help` for all options, including `--target-crs`,
`--assume-crs`, `--no-densify`, and the `pygeoops.centerline` pass-through
options (`--extend`, `--min-branch-length`, `--simplify-tolerance`,
`--pygeoops-densify-distance`).

## Python API usage

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
centerline) only make sense in a metric/projected CRS. `road-centerline`
resolves a working CRS as follows:

1. If the input has no CRS, you must pass `assume_crs` (Python API) /
   `--assume-crs` (CLI) to state what CRS the coordinates are actually in.
   This is a hard error otherwise — silently guessing would risk producing
   plausible-looking but wrong output.
2. If `target_crs` / `--target-crs` is given, it's used for the working math.
3. Otherwise, if the CRS is geographic, a local UTM zone is auto-selected via
   `GeoDataFrame.estimate_utm_crs()`.
4. Otherwise (already projected), the input CRS is used as-is.

The output is always reprojected back to match the input's original CRS.

## Supported formats

Any format geopandas can read/write via its I/O backend (pyogrio), inferred
from the file extension — including `.shp`, `.geojson`, and `.gpkg`.

## Development

```sh
pip install -e ".[dev]"
pytest
ruff check .
```

See [`Notebooks/centerline.ipynb`](Notebooks/centerline.ipynb) for a runnable
walkthrough.

## License

MIT — see [LICENSE](LICENSE).

# road-centerline

Extract road centerlines from polygon geometries (road contours) — worldwide,
in any input CRS, in any format geopandas can read or write.

> **Status:** not yet published to PyPI. Install from source (see
> [Development](#development)) until the first release is uploaded.

Given a polygon representing a road's outline, `road-centerline` optionally
densifies its edges (adding vertices so long, straight edges don't starve the
skeletonization algorithm of detail) and then computes the medial-axis
centerline using [`pygeoops.centerline`](https://pygeoops.readthedocs.io/en/stable/api/pygeoops.centerline.html).
On top of that it repairs invalid input, derives per-road attributes, and can
snap adjoining centerlines into a connected network — see
[How this compares](#how-this-compares).

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
  call rather than row by row (opt into `n_jobs` for parallel chunking on
  very large batches).
- **Robust by default**: invalid input polygons are auto-repaired
  (`shapely.make_valid`); `on_error="skip"` drops a genuinely unusable row
  and logs it instead of failing the whole batch.
- **Road attributes**: `length` and `est_width` (area/length average-width
  estimate) columns are added by default.
- **Network building**: `build_network()` snaps centerline endpoints that
  share a junction into a connected edges/nodes graph, with an optional
  `to_networkx()` export — rather than the disconnected per-polygon lines
  you get from calling `pygeoops.centerline` directly.
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

Build a connected network instead of disconnected per-polygon lines:

```sh
road-centerline Road.shp Road_Centerline.gpkg --build-network --snap-tolerance 1.0
```

Run `road-centerline --help` for all options, including `--target-crs`,
`--assume-crs`, `--no-densify`, `--on-error`, `--n-jobs`,
`--build-network`/`--snap-tolerance`, and the `pygeoops.centerline`
pass-through options (`--extend`, `--min-branch-length`,
`--simplify-tolerance`, `--pygeoops-densify-distance`).

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

### Building a connected network

```python
from road_centerline import compute_centerlines, build_network, to_networkx

# Network building is distance-based, so do it before reprojecting to a
# geographic CRS — process_file(..., build_network=True) handles this for
# you automatically.
centerlines = compute_centerlines(gdf, target_crs="EPSG:32633")
edges, nodes = build_network(centerlines, snap_tolerance=1.0)

# Optional: pip install road-centerline[network]
graph = to_networkx(edges, nodes)
```

## Robustness options

```python
compute_centerlines(
    gdf,
    repair_invalid=True,   # default: shapely.make_valid on input polygons
    on_error="skip",       # default "raise": drop unusable rows instead of failing
    n_jobs=-1,              # default 1: chunk across all CPU cores for large batches
)
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
auto-UTM). `build_network()`'s `snap_tolerance` is a distance in whatever CRS
you pass it — pass metric-CRS centerlines, not reprojected geographic ones.

## Supported formats

Any format geopandas can read/write via its I/O backend (pyogrio), inferred
from the file extension — including `.shp`, `.geojson`, and `.gpkg`.

## How this compares

`pygeos` isn't a live comparison target — it was merged into Shapely 2.0 in
2021 and has no independent development; this project already sits on
`shapely>=2.0`. The real comparators are the library road-centerline wraps
([`pygeoops`](https://github.com/pygeoops/pygeoops)) and the other dedicated
PyPI package for this task ([`centerline`](https://github.com/fitodic/centerline)).

Measured with `benchmarks/compare.py` against the 86 real OSM road polygons
in `tests/fixtures/utrecht_roads.geojson`:

| | wall time | valid/non-empty output |
|---|---|---|
| **road-centerline** | 551 ms | 86/86 |
| raw `pygeoops.centerline` | 279 ms | 86/86 |
| `centerline` (fitodic) | 5759 ms | 86/86 |

road-centerline is slower than calling `pygeoops` directly — that gap is the
cost of CRS resolution, densification, geometry repair, and attribute
computation happening automatically. It's ~10x faster than `centerline`,
which computes a Voronoi diagram per polygon in a Python loop rather than
vectorizing across the layer.

The clean fixture above doesn't show the more common real-world failure
mode: a self-intersecting road polygon. Raw `pygeoops.centerline` propagates
the GEOS exception and aborts the whole batch; road-centerline's default
`repair_invalid=True` fixes it transparently:

```python
>>> pygeoops.centerline(gdf_with_one_bad_polygon.geometry)
GEOSException: TopologyException: side location conflict ...
>>> compute_centerlines(gdf_with_one_bad_polygon)  # succeeds, all rows valid
```

Neither `pygeoops` nor `centerline` produce a connected road network —
each polygon becomes an independent line, even where two road polygons
visibly meet at a junction. `build_network()` is what turns that into an
actual graph (see [Building a connected network](#building-a-connected-network)).

## Development

```sh
pip install -e ".[dev]"
pytest
ruff check .
```

See [`Notebooks/centerline.ipynb`](Notebooks/centerline.ipynb) for a runnable
walkthrough, and `benchmarks/compare.py` for the comparison above (add
`pip install centerline` to include the third column).

### Releasing

```sh
python -m build
twine check dist/*
twine upload dist/*
```

## License

MIT — see [LICENSE](LICENSE).

# road-centerline

[![PyPI](https://img.shields.io/pypi/v/road-centerline)](https://pypi.org/project/road-centerline/)
[![CI](https://github.com/DBishal13/Road-Centerline/actions/workflows/ci.yml/badge.svg)](https://github.com/DBishal13/Road-Centerline/actions/workflows/ci.yml)
[![Docs](https://github.com/DBishal13/Road-Centerline/actions/workflows/docs.yml/badge.svg)](https://dbishal13.github.io/Road-Centerline/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Extract road centerlines from polygon geometries (road contours) — worldwide,
in any input CRS, in any format geopandas can read or write.

**[Documentation](https://dbishal13.github.io/Road-Centerline/)** ·
[Demo](https://dbishal13.github.io/Road-Centerline/demo/) ·
[How this compares](https://dbishal13.github.io/Road-Centerline/comparison/) ·
[Changelog](CHANGELOG.md)

A real motorway exit ramp and loop near Utrecht: the OSM road-surface
polygon (cyan fill) with its extracted centerline (magenta line) overlaid,
on actual aerial imagery:

<img src="https://raw.githubusercontent.com/DBishal13/Road-Centerline/main/docs/assets/img/real-interchange-satellite.jpg" width="600" alt="A real motorway interchange: the road-surface polygon in cyan, with its extracted centerline in magenta overlaid on top, both on real satellite imagery">

Given a polygon representing a road's outline, `road-centerline` optionally
densifies its edges (adding vertices so long, straight edges don't starve the
skeletonization algorithm of detail) and then computes the medial-axis
centerline using [`pygeoops.centerline`](https://pygeoops.readthedocs.io/en/stable/api/pygeoops.centerline.html).
On top of that it repairs invalid input, derives per-road attributes, and can
snap adjoining centerlines into a connected network.

## Features

- **CRS-aware, globally**: if the input CRS is geographic (e.g. WGS84
  lat/lon), distances are computed in an automatically-estimated local UTM
  zone, then the result is reprojected back to the original CRS. Works
  anywhere on Earth — no manual projection setup required.
- **Any GDAL/OGR vector format**: Shapefile, GeoJSON, GeoPackage, FlatGeobuf,
  GML, KML, MapInfo, and dozens more — see
  [Supported formats](https://dbishal13.github.io/Road-Centerline/quickstart/#supported-formats).
- **Vectorized**: centerlines are computed for an entire layer in a single
  `pygeoops.centerline` call rather than row by row (opt into `n_jobs` for
  parallel chunking on very large batches).
- **Robust by default**: invalid input polygons are auto-repaired;
  `on_error="skip"` drops a genuinely unusable row instead of failing the
  whole batch.
- **Road attributes**: `length` and `est_width` columns are added by
  default.
- **Network building**: `build_network()` snaps centerline endpoints that
  share a junction into a connected edges/nodes graph, rather than the
  disconnected per-polygon lines you get from calling `pygeoops.centerline`
  directly.
- **CLI and Python API**.

Full details on each: [Quickstart](https://dbishal13.github.io/Road-Centerline/quickstart/) ·
[Building a network](https://dbishal13.github.io/Road-Centerline/network/) ·
[Robustness at scale](https://dbishal13.github.io/Road-Centerline/robustness/).

## Installation

```sh
pip install road-centerline
```

## Quick usage

```sh
road-centerline Road.shp Road_Centerline.shp --densify-distance 10
```

```python
import geopandas as gpd
from road_centerline import compute_centerlines

gdf = gpd.read_file("Road.shp")
centerlines = compute_centerlines(gdf, densify_distance=10.0)
centerlines.to_file("Road_Centerline.shp")
```

See the [Quickstart](https://dbishal13.github.io/Road-Centerline/quickstart/)
for all CLI/API options and CRS handling, or the
[Demo](https://dbishal13.github.io/Road-Centerline/demo/) for a full
walkthrough against real OSM road polygons
([runnable notebook](Notebooks/centerline.ipynb)).

## How this compares

`pygeos` isn't a live comparison target — it was merged into Shapely 2.0 in
2021 and has no independent development. The real comparators are
[`pygeoops`](https://github.com/pygeoops/pygeoops) (the library
road-centerline wraps) and [`centerline`](https://github.com/fitodic/centerline)
(the other dedicated PyPI package for this task):

<img src="https://raw.githubusercontent.com/DBishal13/Road-Centerline/main/docs/assets/img/benchmark-chart.png" width="480" alt="Wall time comparison: road-centerline, raw pygeoops, and the centerline package">

road-centerline is slower than calling `pygeoops` directly — that gap is the
cost of CRS resolution, densification, repair, and attributes happening
automatically — but ~10x faster than `centerline`, and (unlike either) it
repairs invalid input automatically and can build a connected network
instead of disconnected per-polygon lines. Full comparison, including how
each approach handles a self-intersecting road polygon:
[How this compares](https://dbishal13.github.io/Road-Centerline/comparison/).

## Development

```sh
pip install -e ".[dev]"
pytest
ruff check .
mkdocs serve  # docs site at http://127.0.0.1:8000, needs pip install -e ".[docs]"
```

### Releasing

Releases are published by [`.github/workflows/release.yml`](.github/workflows/release.yml)
whenever a `v*` tag is pushed, via [PyPI trusted publishing](https://docs.pypi.org/trusted-publishers/)
(no API token needed). See [CHANGELOG.md](CHANGELOG.md) for the version
history. To cut a release:

1. Move the `[Unreleased]` entries in `CHANGELOG.md` under a new
   `## [X.Y.Z] - YYYY-MM-DD` heading, and add its compare/tag links at the
   bottom of the file.
2. Bump `version` in `pyproject.toml` to match.
3. Commit, then tag and push:
   ```sh
   git commit -am "Release vX.Y.Z"
   git tag vX.Y.Z
   git push origin main vX.Y.Z
   ```
4. CI builds, runs `twine check`, and publishes to PyPI automatically — the
   tag must match `pyproject.toml`'s version or the workflow fails fast
   before it builds anything.

To build and check a release locally without publishing:

```sh
python -m build
twine check dist/*
```

## License

MIT — see [LICENSE](LICENSE).

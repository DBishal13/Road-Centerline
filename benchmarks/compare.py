"""Compare road-centerline against raw pygeoops and the `centerline` package.

Standalone script, not part of the pytest suite (the `centerline` package is
a comparison-only dependency, not something the CI test matrix should
require). Run with the repo's dev environment active:

    python benchmarks/compare.py

Reports wall time and output validity/completeness for each approach on the
86 real OSM road polygons in tests/fixtures/utrecht_roads.geojson.
"""

from __future__ import annotations

import time
from pathlib import Path

import geopandas as gpd
import pygeoops

from road_centerline import compute_centerlines
from road_centerline.crs import resolve_working_crs

FIXTURE = Path(__file__).parent.parent / "tests" / "fixtures" / "utrecht_roads.geojson"


def _report(name: str, elapsed: float, geoms: gpd.GeoSeries, n_input: int) -> None:
    valid = geoms.is_valid.sum()
    non_empty = (~geoms.is_empty).sum()
    print(
        f"{name:<22} {elapsed * 1000:>8.1f} ms   "
        f"valid {valid}/{n_input}   non-empty {non_empty}/{n_input}"
    )


def main() -> None:
    gdf = gpd.read_file(FIXTURE)
    n = len(gdf)
    print(f"Benchmarking against {n} real road polygons from {FIXTURE.name}\n")

    start = time.perf_counter()
    rc_result = compute_centerlines(gdf)
    _report("road-centerline", time.perf_counter() - start, rc_result.geometry, n)

    working_gdf, _ = resolve_working_crs(gdf)
    start = time.perf_counter()
    raw = pygeoops.centerline(working_gdf.geometry)
    _report("raw pygeoops", time.perf_counter() - start, gpd.GeoSeries(raw), n)

    try:
        from centerline.geometry import Centerline

        start = time.perf_counter()
        lines = []
        for geom in working_gdf.geometry:
            try:
                lines.append(Centerline(geom).geometry)
            except Exception:  # noqa: BLE001 - best-effort per-polygon, any failure -> skip
                lines.append(None)
        _report("centerline (fitodic)", time.perf_counter() - start, gpd.GeoSeries(lines), n)
    except ImportError:
        print("centerline (fitodic)  not installed, skipped (pip install centerline)")


if __name__ == "__main__":
    main()

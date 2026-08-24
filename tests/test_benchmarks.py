"""Light regression guard: road-centerline should never be less complete than
raw pygeoops.centerline on the same real input. No `centerline` package
dependency here — see benchmarks/compare.py for the full 3-way comparison.
"""

from pathlib import Path

import geopandas as gpd
import pygeoops

from road_centerline import compute_centerlines
from road_centerline.crs import resolve_working_crs

FIXTURE = Path(__file__).parent / "fixtures" / "utrecht_roads.geojson"


def test_road_centerline_at_least_as_complete_as_raw_pygeoops():
    gdf = gpd.read_file(FIXTURE)

    rc_result = compute_centerlines(gdf)
    rc_valid_non_empty = (rc_result.geometry.is_valid & ~rc_result.geometry.is_empty).sum()

    working_gdf, _ = resolve_working_crs(gdf)
    raw = gpd.GeoSeries(pygeoops.centerline(working_gdf.geometry))
    raw_valid_non_empty = (raw.is_valid & ~raw.is_empty).sum()

    assert rc_valid_non_empty >= raw_valid_non_empty

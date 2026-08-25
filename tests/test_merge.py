from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

from road_centerline.merge import merge_parallel_polygons

FIXTURE = Path(__file__).parent / "fixtures" / "utrecht_roads.geojson"


def test_parallel_gapped_rectangles_merge_into_one():
    # two 10x100 strips, 5m apart, both running along x -> same "road"
    a = box(0, 0, 100, 10)
    b = box(0, 15, 100, 25)
    gdf = gpd.GeoDataFrame({"id": [1, 2]}, geometry=[a, b], crs="EPSG:32633")

    result = merge_parallel_polygons(gdf, gap_threshold=8.0)

    assert len(result) == 1
    assert result["merged_count"].iloc[0] == 2
    assert result.geometry.iloc[0].geom_type == "Polygon"
    # merged shape should be a single seamless polygon, not two disjoint parts
    assert len(list(result.geometry.iloc[0].interiors)) == 0


def test_perpendicular_rectangles_do_not_merge_despite_proximity():
    # two strips meeting at a right angle, close together -> different roads crossing
    a = box(0, 0, 100, 10)
    b = box(45, -50, 55, 60)
    gdf = gpd.GeoDataFrame({"id": [1, 2]}, geometry=[a, b], crs="EPSG:32633")

    result = merge_parallel_polygons(gdf, gap_threshold=8.0, angle_threshold=15.0)

    assert len(result) == 2
    assert result["merged_count"].tolist() == [1, 1]


def test_parallel_rectangles_beyond_gap_threshold_do_not_merge():
    a = box(0, 0, 100, 10)
    b = box(0, 50, 100, 60)  # 40m gap
    gdf = gpd.GeoDataFrame({"id": [1, 2]}, geometry=[a, b], crs="EPSG:32633")

    result = merge_parallel_polygons(gdf, gap_threshold=8.0)

    assert len(result) == 2


def test_aggfunc_controls_attribute_aggregation():
    a = box(0, 0, 100, 10)
    b = box(0, 15, 100, 25)
    gdf = gpd.GeoDataFrame({"lanes": [2, 3]}, geometry=[a, b], crs="EPSG:32633")

    result = merge_parallel_polygons(gdf, gap_threshold=8.0, aggfunc="sum")

    assert result["lanes"].iloc[0] == 5


def test_real_fixture_merging_reduces_row_count_without_raising():
    gdf = gpd.read_file(FIXTURE).to_crs(gpd.read_file(FIXTURE).estimate_utm_crs())

    merged = merge_parallel_polygons(gdf)

    assert 0 < len(merged) <= len(gdf)
    assert merged.geometry.is_valid.all()

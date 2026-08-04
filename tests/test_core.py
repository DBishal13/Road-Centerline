from unittest import mock

import geopandas as gpd
import pytest
from shapely.geometry import LineString

from road_centerline.core import compute_centerlines, process_file


def _fake_centerlines(geometry, **kwargs):
    lines = [LineString([(0, 0), (1, 1)]) for _ in range(len(geometry))]
    return gpd.GeoSeries(lines, index=geometry.index, crs=geometry.crs)


def test_geographic_input_round_trip_crs(road_gdf_geographic):
    # densify_distance is in the metric working CRS (meters), applied after
    # reprojection out of the geographic input CRS.
    result = compute_centerlines(road_gdf_geographic, densify_distance=5.0)
    assert result.crs == road_gdf_geographic.crs


def test_pygeoops_centerline_called_exactly_once(road_gdf_projected):
    with mock.patch(
        "road_centerline.core.pygeoops.centerline", side_effect=_fake_centerlines
    ) as mocked:
        compute_centerlines(road_gdf_projected)
    assert mocked.call_count == 1


def test_default_branch_pruning_does_not_truncate_junction(y_junction_polygon):
    # pygeoops' own auto min_branch_length (-1) scales off average polygon
    # width, which on a compact junction like this collapses the centerline
    # to a single short trunk that never reaches any of the three arms. The
    # fixed default (10.0) must recover the full branching centerline.
    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[y_junction_polygon], crs="EPSG:32633")

    result = compute_centerlines(gdf, densify=True, densify_distance=10.0)
    line = result.geometry.iloc[0]

    assert line.geom_type == "MultiLineString"
    assert len(line.geoms) >= 3
    assert line.length > 200


def test_densify_false_still_produces_centerlines(road_gdf_projected):
    result = compute_centerlines(road_gdf_projected, densify=False)
    assert len(result) == len(road_gdf_projected)
    assert result.geometry.notna().all()


@pytest.mark.parametrize("ext", ["geojson", "gpkg", "shp"])
def test_process_file_roundtrip(tmp_path, road_gdf_projected, ext):
    input_path = tmp_path / f"road.{ext}"
    output_path = tmp_path / f"road_centerline.{ext}"
    road_gdf_projected.to_file(input_path)

    result = process_file(str(input_path), str(output_path), densify_distance=5.0)

    assert output_path.exists() or (ext == "shp" and (tmp_path / "road_centerline.shx").exists())
    assert len(result) == len(road_gdf_projected)
    reloaded = gpd.read_file(output_path)
    assert len(reloaded) == len(road_gdf_projected)

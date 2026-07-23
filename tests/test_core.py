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

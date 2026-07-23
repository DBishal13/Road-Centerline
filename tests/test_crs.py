import pyproj
import pytest

from road_centerline.crs import resolve_working_crs
from road_centerline.exceptions import MissingCRSError


def test_projected_input_passes_through_unchanged(road_gdf_projected):
    working, original = resolve_working_crs(road_gdf_projected)
    assert working.crs == road_gdf_projected.crs
    assert original == road_gdf_projected.crs


def test_geographic_input_reprojects_to_projected_utm(road_gdf_geographic):
    working, original = resolve_working_crs(road_gdf_geographic)
    assert original == road_gdf_geographic.crs
    assert working.crs.is_projected
    assert not working.crs.is_geographic


def test_explicit_target_crs_overrides_auto_selection(road_gdf_geographic):
    target = pyproj.CRS.from_epsg(32645)  # UTM zone 45N, covers Kathmandu
    working, original = resolve_working_crs(road_gdf_geographic, target_crs=target)
    assert working.crs == target
    assert original == road_gdf_geographic.crs


def test_missing_crs_raises_without_assume(road_gdf_no_crs):
    with pytest.raises(MissingCRSError):
        resolve_working_crs(road_gdf_no_crs)


def test_missing_crs_succeeds_with_assume_crs(road_gdf_no_crs):
    working, original = resolve_working_crs(road_gdf_no_crs, assume_crs="EPSG:32633")
    assert working.crs == pyproj.CRS.from_epsg(32633)
    assert original == pyproj.CRS.from_epsg(32633)

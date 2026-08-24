from unittest import mock

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import LineString, Polygon

from road_centerline.core import compute_centerlines, process_file


def _append_row(gdf: gpd.GeoDataFrame, **row) -> gpd.GeoDataFrame:
    extra = gpd.GeoDataFrame({k: [v] for k, v in row.items()}, crs=gdf.crs)
    return gpd.GeoDataFrame(pd.concat([gdf, extra], ignore_index=True), crs=gdf.crs)


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


def test_on_error_raise_reports_unusable_row(road_gdf_projected):
    gdf = _append_row(road_gdf_projected, id=99, geometry=Polygon())

    with pytest.raises(ValueError, match="unusable"):
        compute_centerlines(gdf)


def test_on_error_skip_drops_unusable_row_and_keeps_rest(road_gdf_projected):
    gdf = _append_row(road_gdf_projected, id=99, geometry=Polygon())

    result = compute_centerlines(gdf, on_error="skip")

    assert len(result) == len(road_gdf_projected)
    assert 99 not in result["id"].tolist()


def test_add_attributes_default_adds_length_and_width(road_gdf_projected):
    result = compute_centerlines(road_gdf_projected)

    assert "length" in result.columns
    assert "est_width" in result.columns
    assert (result["length"] > 0).all()


def test_n_jobs_parallel_matches_sequential(road_gdf_projected):
    sequential = compute_centerlines(road_gdf_projected, n_jobs=1)
    parallel = compute_centerlines(road_gdf_projected, n_jobs=2)

    assert np.array_equal(
        sequential.geometry.geom_equals_exact(parallel.geometry, tolerance=1e-6).to_numpy(),
        np.ones(len(sequential), dtype=bool),
    )


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


def test_process_file_build_network_writes_edges_and_nodes(tmp_path, road_gdf_geographic):
    input_path = tmp_path / "road.geojson"
    output_path = tmp_path / "road_centerline.gpkg"
    road_gdf_geographic.to_file(input_path)

    edges = process_file(
        str(input_path), str(output_path), build_network=True, densify_distance=5.0
    )

    assert edges.crs == road_gdf_geographic.crs
    reloaded_edges = gpd.read_file(output_path, layer="edges")
    reloaded_nodes = gpd.read_file(output_path, layer="nodes")
    assert reloaded_edges.crs == road_gdf_geographic.crs
    assert set(reloaded_edges["u"]) | set(reloaded_edges["v"]) <= set(reloaded_nodes["node_id"])


def test_process_file_build_network_non_gpkg_writes_sibling_nodes_file(
    tmp_path, road_gdf_geographic
):
    input_path = tmp_path / "road.geojson"
    output_path = tmp_path / "road_centerline.geojson"
    road_gdf_geographic.to_file(input_path)

    process_file(str(input_path), str(output_path), build_network=True, densify_distance=5.0)

    nodes_path = tmp_path / "road_centerline_nodes.geojson"
    assert output_path.exists()
    assert nodes_path.exists()
    reloaded_nodes = gpd.read_file(nodes_path)
    assert reloaded_nodes.crs == road_gdf_geographic.crs

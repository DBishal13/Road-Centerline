import logging

import numpy as np
import pytest
from shapely.geometry import LineString, MultiPolygon, Polygon

from road_centerline.densify import (
    densify_geometry,
    densify_geoseries,
    densify_polygon,
    densify_ring,
)


def _max_segment_length(coords: np.ndarray) -> float:
    diffs = np.diff(coords, axis=0)
    return float(np.max(np.linalg.norm(diffs, axis=1)))


def test_densify_ring_no_segment_exceeds_max_distance():
    ring = np.array([[0, 0], [100, 0], [100, 10], [0, 10], [0, 0]], dtype=float)
    densified = densify_ring(ring, max_distance=5.0)
    assert _max_segment_length(densified) <= 5.0 + 1e-9


def test_densify_ring_short_edge_gets_no_extra_points():
    ring = np.array([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]], dtype=float)
    densified = densify_ring(ring, max_distance=10.0)
    assert len(densified) == len(ring)


def test_densify_ring_uneven_edges_scale_independently():
    # One long edge, one short edge in the same ring: each should be
    # densified according to its own length, not a shared perimeter-derived count.
    ring = np.array([[0, 0], [100, 0], [100, 1], [0, 1], [0, 0]], dtype=float)
    densified = densify_ring(ring, max_distance=10.0)
    assert _max_segment_length(densified) <= 10.0 + 1e-9
    # The short top/bottom edges (length 1) should not have been subdivided.
    assert len(densified) < 2 * (100 / 10 + 2)


def test_densify_polygon_stays_valid(simple_road_polygon):
    result = densify_polygon(simple_road_polygon, distance=5.0)
    assert result.is_valid
    assert result.area == pytest.approx(simple_road_polygon.area, rel=1e-6)


def test_densify_geometry_dispatch_polygon(simple_road_polygon):
    result = densify_geometry(simple_road_polygon, distance=5.0)
    assert isinstance(result, Polygon)


def test_densify_geometry_dispatch_multipolygon(simple_road_polygon):
    mp = MultiPolygon([simple_road_polygon, Polygon([(0, 20), (10, 20), (10, 30), (0, 30)])])
    result = densify_geometry(mp, distance=5.0)
    assert isinstance(result, MultiPolygon)
    assert len(result.geoms) == 2


def test_densify_geometry_passthrough_with_warning(caplog):
    line = LineString([(0, 0), (10, 0)])
    with caplog.at_level(logging.WARNING):
        result = densify_geometry(line, distance=5.0)
    assert result == line
    assert "not a Polygon/MultiPolygon" in caplog.text


def test_densify_geoseries_matches_elementwise(road_gdf_projected):
    result = densify_geoseries(road_gdf_projected.geometry, distance=5.0)
    expected = road_gdf_projected.geometry.apply(lambda g: densify_geometry(g, 5.0))
    assert list(result.geom_equals(expected))


def test_densify_polygon_empty_passthrough():
    empty = Polygon()
    assert densify_polygon(empty, distance=5.0).is_empty

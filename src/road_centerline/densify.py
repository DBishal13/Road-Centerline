from __future__ import annotations

import logging

import geopandas as gpd
import numpy as np
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry

logger = logging.getLogger(__name__)


def densify_ring(coords: np.ndarray, max_distance: float) -> np.ndarray:
    """Insert points along a closed ring so no segment exceeds max_distance.

    The number of points inserted on each segment is derived from that
    segment's own length, so a short edge and a long edge in the same ring
    are densified independently (rather than by a single count derived from
    the ring's total perimeter). Fully vectorized: no Python loop over
    vertices.
    """
    coords = np.asarray(coords, dtype=float)
    if max_distance is None or max_distance <= 0 or len(coords) < 2:
        return coords

    starts = coords[:-1]
    ends = coords[1:]
    seg_vec = ends - starts
    seg_len = np.linalg.norm(seg_vec, axis=1)

    # Number of output points taken from the start of each segment (>=1).
    n = np.maximum(1, np.ceil(seg_len / max_distance)).astype(int)
    total_points = int(n.sum())

    seg_idx = np.repeat(np.arange(len(n)), n)
    segment_start_offset = np.repeat(np.cumsum(n) - n, n)
    position_in_segment = np.arange(total_points) - segment_start_offset
    fraction = position_in_segment / np.repeat(n, n)

    new_points = starts[seg_idx] + seg_vec[seg_idx] * fraction[:, None]
    return np.vstack([new_points, coords[-1]])


def densify_polygon(polygon: Polygon, distance: float) -> Polygon:
    """Densify a polygon's exterior and interior rings."""
    if polygon.is_empty:
        return polygon

    exterior = densify_ring(np.array(polygon.exterior.coords), distance)
    interiors = [
        densify_ring(np.array(ring.coords), distance) for ring in polygon.interiors
    ]
    return Polygon(exterior, interiors)


def densify_geometry(geometry: BaseGeometry, distance: float) -> BaseGeometry:
    """Densify a Polygon or MultiPolygon; other geometry types pass through unchanged."""
    if isinstance(geometry, Polygon):
        return densify_polygon(geometry, distance)
    if isinstance(geometry, MultiPolygon):
        return MultiPolygon([densify_polygon(part, distance) for part in geometry.geoms])

    logger.warning(
        "densify_geometry: geometry type %s is not a Polygon/MultiPolygon; "
        "passing through unchanged.",
        geometry.geom_type,
    )
    return geometry


def densify_geoseries(geometries: gpd.GeoSeries, distance: float) -> gpd.GeoSeries:
    """Densify every geometry in a GeoSeries.

    Shapely geometry construction is inherently per-object, so this is the
    one place a per-geometry Python-level loop (via .apply) is unavoidable;
    the per-ring interpolation math itself is vectorized in densify_ring.
    """
    return geometries.apply(lambda geom: densify_geometry(geom, distance))

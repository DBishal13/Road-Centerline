from __future__ import annotations

import geopandas as gpd
import numpy as np
import shapely


def repair_geometries(geoseries: gpd.GeoSeries) -> gpd.GeoSeries:
    """Repair invalid geometries in-place-equivalent (returns a new GeoSeries).

    Vectorized via `shapely.make_valid`, run once over the whole series
    rather than per-row. `None` entries pass through unchanged (make_valid
    has no meaningful action on a missing geometry).
    """
    repaired = shapely.make_valid(geoseries.values)
    return gpd.GeoSeries(repaired, index=geoseries.index, crs=geoseries.crs)


def find_unusable(geoseries: gpd.GeoSeries) -> np.ndarray:
    """Boolean mask for geometries that are None, empty, or not a (Multi)Polygon.

    Meant to run after `repair_geometries`: what's still unusable at that
    point (e.g. a degenerate input that collapsed to a point or line under
    make_valid) can't produce a centerline and should be skipped or reported,
    not silently passed to pygeoops.
    """
    values = geoseries.values
    is_none = shapely.is_missing(values)
    is_empty = shapely.is_empty(values)
    geom_types = shapely.get_type_id(values)
    is_polygonal = np.isin(geom_types, [shapely.GeometryType.POLYGON, shapely.GeometryType.MULTIPOLYGON])
    return is_none | is_empty | ~is_polygonal

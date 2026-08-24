from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd


def add_road_attributes(
    centerlines: gpd.GeoDataFrame, polygon_areas: pd.Series
) -> gpd.GeoDataFrame:
    """Add `length` and `est_width` columns, computed in the geometry's own CRS units.

    `est_width` is the standard area/length average-width estimate for a
    roughly-constant-width strip polygon (its source polygon's area divided
    by its centerline's length). `NaN` where length is 0 (e.g. an empty
    centerline).

    Must be called while `centerlines` is still in the metric working CRS —
    reprojecting to a geographic CRS first would make `length` and
    `polygon_areas` meaningless.
    """
    result = centerlines.copy()
    length = result.geometry.length.to_numpy()
    result["length"] = length
    with np.errstate(divide="ignore", invalid="ignore"):
        est_width = polygon_areas.to_numpy() / length
    result["est_width"] = np.where(length > 0, est_width, np.nan)
    return result

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString

from road_centerline.attributes import add_road_attributes


def test_length_and_est_width_are_exact_for_known_geometry():
    # A 100m-long centerline for a polygon of area 1000 -> width 10.
    centerlines = gpd.GeoDataFrame(
        {"id": [1]}, geometry=[LineString([(0, 0), (100, 0)])], crs="EPSG:32633"
    )
    polygon_areas = pd.Series([1000.0])

    result = add_road_attributes(centerlines, polygon_areas)

    assert result["length"].iloc[0] == 100.0
    assert result["est_width"].iloc[0] == 10.0


def test_zero_length_centerline_gives_nan_width():
    centerlines = gpd.GeoDataFrame(
        {"id": [1]}, geometry=[LineString([(0, 0), (0, 0)])], crs="EPSG:32633"
    )
    polygon_areas = pd.Series([500.0])

    result = add_road_attributes(centerlines, polygon_areas)

    assert result["length"].iloc[0] == 0.0
    assert np.isnan(result["est_width"].iloc[0])

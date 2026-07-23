import geopandas as gpd
import pytest
from shapely.geometry import Polygon


def _road_rectangle(x0: float, y0: float, length: float, width: float) -> Polygon:
    return Polygon(
        [
            (x0, y0),
            (x0 + length, y0),
            (x0 + length, y0 + width),
            (x0, y0 + width),
        ]
    )


@pytest.fixture
def simple_road_polygon() -> Polygon:
    """A simple long, thin rectangle representing a road segment (meters)."""
    return _road_rectangle(0, 0, 100, 10)


@pytest.fixture
def road_gdf_projected() -> gpd.GeoDataFrame:
    """Two road polygons in a projected (metric) CRS."""
    geoms = [_road_rectangle(0, 0, 100, 10), _road_rectangle(200, 0, 50, 8)]
    return gpd.GeoDataFrame({"id": [1, 2]}, geometry=geoms, crs="EPSG:32633")


@pytest.fixture
def road_gdf_geographic() -> gpd.GeoDataFrame:
    """Two road polygons in a geographic CRS (degrees), near Kathmandu."""
    geoms = [
        _road_rectangle(85.3000, 27.7000, 0.0010, 0.0001),
        _road_rectangle(85.3100, 27.7000, 0.0005, 0.00008),
    ]
    return gpd.GeoDataFrame({"id": [1, 2]}, geometry=geoms, crs="EPSG:4326")


@pytest.fixture
def road_gdf_no_crs() -> gpd.GeoDataFrame:
    """A road polygon with no CRS set at all."""
    geoms = [_road_rectangle(0, 0, 100, 10)]
    return gpd.GeoDataFrame({"id": [1]}, geometry=geoms, crs=None)

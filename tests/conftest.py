import geopandas as gpd
import pytest
from shapely.geometry import Polygon


def _y_junction(arm_length: float = 45.0, arm_width: float = 30.0) -> Polygon:
    """A three-way branching polygon (e.g. a lane split/merge), hub at the origin.

    Wide relative to each arm's length, so pygeoops' average-width-scaled
    auto branch pruning (min_branch_length=-1) prunes all three arms down
    to a stub that never reaches the polygon's ends.
    """
    import math

    from shapely.ops import unary_union

    half_w = arm_width / 2
    arms = []
    for angle_deg in (90, 210, 330):
        angle = math.radians(angle_deg)
        dx, dy = math.cos(angle), math.sin(angle)
        px, py = -dy, dx
        tip = (dx * arm_length, dy * arm_length)
        near = (dx * half_w * 0.5, dy * half_w * 0.5)
        arms.append(
            Polygon(
                [
                    (near[0] + px * half_w, near[1] + py * half_w),
                    (tip[0] + px * half_w, tip[1] + py * half_w),
                    (tip[0] - px * half_w, tip[1] - py * half_w),
                    (near[0] - px * half_w, near[1] - py * half_w),
                ]
            )
        )
    return unary_union(arms).buffer(half_w * 0.3).buffer(-half_w * 0.3)


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
def y_junction_polygon() -> Polygon:
    """A wide three-way branching polygon (lane split/merge), in a metric CRS."""
    return _y_junction()


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

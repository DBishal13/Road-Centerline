import geopandas as gpd
from shapely.geometry import Polygon

from road_centerline.validate import find_unusable, repair_geometries


def test_repair_fixes_self_intersecting_polygon():
    bowtie = Polygon([(0, 0), (2, 2), (2, 0), (0, 2)])
    assert not bowtie.is_valid

    repaired = repair_geometries(gpd.GeoSeries([bowtie]))

    assert repaired.iloc[0].is_valid


def test_repair_passes_none_through_unchanged():
    repaired = repair_geometries(gpd.GeoSeries([None]))
    assert repaired.iloc[0] is None


def test_find_unusable_flags_none_and_empty():
    good = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    geoseries = gpd.GeoSeries([good, None, Polygon()])

    mask = find_unusable(geoseries)

    assert mask.tolist() == [False, True, True]

import pytest

from road_centerline.exceptions import AmbiguousDriverError
from road_centerline.formats import resolve_output_driver


def test_explicit_driver_passes_through_unchanged():
    assert resolve_output_driver("anything.xyz", "KML") == "KML"


def test_unambiguous_extension_infers_driver():
    assert resolve_output_driver("out.geojson", None) == "GeoJSON"
    assert resolve_output_driver("out.gpkg", None) == "GPKG"
    assert resolve_output_driver("out.shp", None) == "ESRI Shapefile"


def test_ambiguous_extension_raises_with_actionable_message():
    with pytest.raises(AmbiguousDriverError, match="driver"):
        resolve_output_driver("out.kml", None)


def test_unrecognized_extension_raises():
    with pytest.raises(AmbiguousDriverError):
        resolve_output_driver("out.totallymadeupext", None)

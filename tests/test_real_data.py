from pathlib import Path

import geopandas as gpd

from road_centerline.core import process_file

FIXTURE = Path(__file__).parent / "fixtures" / "utrecht_roads.geojson"


def test_real_road_polygons_produce_valid_centerlines(tmp_path):
    output_path = tmp_path / "utrecht_centerlines.geojson"

    result = process_file(str(FIXTURE), str(output_path))

    source = gpd.read_file(FIXTURE)
    assert len(result) == len(source)
    assert result.crs == source.crs
    assert result.geometry.is_valid.all()
    assert (~result.geometry.is_empty).all()
    assert result.geometry.notna().all()

    reloaded = gpd.read_file(output_path)
    assert len(reloaded) == len(source)

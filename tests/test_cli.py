import geopandas as gpd
from click.testing import CliRunner
from shapely.geometry import box

from road_centerline.cli import main


def test_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "densify" in result.output


def test_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0


def test_success_run(tmp_path, road_gdf_projected):
    input_path = tmp_path / "road.geojson"
    output_path = tmp_path / "road_centerline.geojson"
    road_gdf_projected.to_file(input_path)

    runner = CliRunner()
    result = runner.invoke(main, [str(input_path), str(output_path), "--densify-distance", "5"])

    assert result.exit_code == 0, result.output
    assert output_path.exists()


def test_missing_input_file_nonzero_exit(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        main, [str(tmp_path / "does_not_exist.geojson"), str(tmp_path / "out.geojson")]
    )
    assert result.exit_code != 0


def test_ambiguous_output_extension_nonzero_exit_without_driver(tmp_path, road_gdf_projected):
    input_path = tmp_path / "road.geojson"
    output_path = tmp_path / "road_centerline.kml"
    road_gdf_projected.to_file(input_path)

    runner = CliRunner()
    result = runner.invoke(main, [str(input_path), str(output_path)])

    assert result.exit_code != 0
    assert not output_path.exists()


def test_driver_flag_writes_requested_format(tmp_path, road_gdf_projected):
    input_path = tmp_path / "road.geojson"
    output_path = tmp_path / "road_centerline.kml"
    road_gdf_projected.to_file(input_path)

    runner = CliRunner()
    result = runner.invoke(main, [str(input_path), str(output_path), "--driver", "KML"])

    assert result.exit_code == 0, result.output
    assert output_path.is_file()
    assert output_path.read_text()[:5] == "<?xml"


def test_merge_parallel_flag_reduces_row_count(tmp_path):
    a = box(0, 0, 100, 10)
    b = box(0, 15, 100, 25)
    gdf = gpd.GeoDataFrame({"id": [1, 2]}, geometry=[a, b], crs="EPSG:32633")
    input_path = tmp_path / "road.geojson"
    output_path = tmp_path / "road_centerline.geojson"
    gdf.to_file(input_path)

    runner = CliRunner()
    result = runner.invoke(main, [str(input_path), str(output_path), "--merge-parallel"])

    assert result.exit_code == 0, result.output
    reloaded = gpd.read_file(output_path)
    assert len(reloaded) == 1
    assert reloaded["merged_count"].iloc[0] == 2

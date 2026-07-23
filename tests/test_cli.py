from click.testing import CliRunner

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

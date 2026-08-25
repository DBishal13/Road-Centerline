from __future__ import annotations

import logging

import click

from road_centerline.core import process_file

logger = logging.getLogger(__name__)


def _level_from_count(count: int) -> int:
    return {0: logging.WARNING, 1: logging.INFO}.get(count, logging.DEBUG)


@click.command()
@click.argument("input_path", type=click.Path(exists=True, dir_okay=False))
@click.argument("output_path", type=click.Path(dir_okay=False))
@click.option(
    "--densify/--no-densify",
    default=True,
    show_default=True,
    help="Pre-densify polygon edges before computing centerlines.",
)
@click.option("--densify-distance", type=float, default=10.0, show_default=True)
@click.option(
    "--target-crs",
    default=None,
    help="Override auto UTM-zone selection for metric math (e.g. EPSG:32633).",
)
@click.option(
    "--assume-crs",
    default=None,
    help="CRS to assume if the input file has none set.",
)
@click.option(
    "--extend/--no-extend",
    default=False,
    show_default=True,
    help="Passed through to pygeoops.centerline.",
)
@click.option("--min-branch-length", type=float, default=10.0, show_default=True)
@click.option("--simplify-tolerance", type=float, default=-0.25, show_default=True)
@click.option("--pygeoops-densify-distance", type=float, default=-1, show_default=True)
@click.option(
    "--repair-invalid/--no-repair-invalid",
    default=True,
    show_default=True,
    help="Run make_valid on input polygons before processing.",
)
@click.option(
    "--on-error",
    type=click.Choice(["raise", "skip"]),
    default="raise",
    show_default=True,
    help="On an unusable/failing input row: raise, or skip it and log a warning.",
)
@click.option(
    "--attributes/--no-attributes",
    default=True,
    show_default=True,
    help="Add 'length' and 'est_width' columns to the output.",
)
@click.option(
    "--n-jobs",
    type=int,
    default=1,
    show_default=True,
    help="Parallel workers for the centerline computation (-1 for all cores). "
    "Only worth it for large inputs.",
)
@click.option(
    "--build-network/--no-build-network",
    default=False,
    show_default=True,
    help="Snap centerline endpoints into a connected edges/nodes network instead "
    "of disconnected per-polygon lines.",
)
@click.option("--snap-tolerance", type=float, default=1.0, show_default=True)
@click.option(
    "--driver",
    default=None,
    help="GDAL/OGR driver to write with, overriding extension-based detection. Required for "
    "extensions that map to more than one driver (e.g. .kml: KML vs LIBKML). See "
    "https://gdal.org/en/stable/drivers/vector/ for driver names.",
)
@click.option("-v", "--verbose", count=True, help="Increase log verbosity (-v, -vv).")
@click.version_option()
def main(
    input_path: str,
    output_path: str,
    densify: bool,
    densify_distance: float,
    target_crs: str | None,
    assume_crs: str | None,
    extend: bool,
    min_branch_length: float,
    simplify_tolerance: float,
    pygeoops_densify_distance: float,
    repair_invalid: bool,
    on_error: str,
    attributes: bool,
    n_jobs: int,
    build_network: bool,
    snap_tolerance: float,
    driver: str | None,
    verbose: int,
) -> None:
    """Compute road centerlines from a polygon file (shapefile, GeoJSON, GeoPackage, ...)."""
    logging.basicConfig(
        level=_level_from_count(verbose), format="%(levelname)s %(name)s: %(message)s"
    )
    try:
        process_file(
            input_path,
            output_path,
            densify=densify,
            densify_distance=densify_distance,
            target_crs=target_crs,
            assume_crs=assume_crs,
            extend=extend,
            min_branch_length=min_branch_length,
            simplifytolerance=simplify_tolerance,
            pygeoops_densify_distance=pygeoops_densify_distance,
            repair_invalid=repair_invalid,
            on_error=on_error,
            add_attributes=attributes,
            n_jobs=n_jobs,
            build_network=build_network,
            snap_tolerance=snap_tolerance,
            driver=driver,
        )
    except Exception:
        logger.exception("Failed to compute centerlines")
        raise SystemExit(1) from None

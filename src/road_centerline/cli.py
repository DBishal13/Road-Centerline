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
@click.option("--min-branch-length", type=float, default=-1, show_default=True)
@click.option("--simplify-tolerance", type=float, default=-0.25, show_default=True)
@click.option("--pygeoops-densify-distance", type=float, default=-1, show_default=True)
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
        )
    except Exception:
        logger.exception("Failed to compute centerlines")
        raise SystemExit(1) from None

from __future__ import annotations

import logging
from pathlib import Path

import geopandas as gpd
import pygeoops

from road_centerline.crs import CRSLike, resolve_working_crs
from road_centerline.densify import densify_geoseries

logger = logging.getLogger(__name__)


def compute_centerlines(
    gdf: gpd.GeoDataFrame,
    *,
    densify: bool = True,
    densify_distance: float = 10.0,
    target_crs: CRSLike | None = None,
    assume_crs: CRSLike | None = None,
    pygeoops_densify_distance: float = -1,
    min_branch_length: float = -1,
    simplifytolerance: float = -0.25,
    extend: bool = False,
) -> gpd.GeoDataFrame:
    """Compute centerlines for a GeoDataFrame of polygons.

    CRS handling: math runs in a metric working CRS (an explicit
    `target_crs`, or an auto-estimated local UTM zone if the input is
    geographic, or the input's own CRS if already projected). The result is
    reprojected back to the input's original CRS before being returned.
    """
    working_gdf, original_crs = resolve_working_crs(gdf, target_crs, assume_crs)

    if densify:
        working_gdf = working_gdf.copy()
        working_gdf.geometry = densify_geoseries(working_gdf.geometry, densify_distance)

    centerlines = pygeoops.centerline(
        working_gdf.geometry,
        densify_distance=pygeoops_densify_distance,
        min_branch_length=min_branch_length,
        simplifytolerance=simplifytolerance,
        extend=extend,
    )

    result = working_gdf.set_geometry(centerlines, crs=working_gdf.crs)

    if original_crs is not None and result.crs != original_crs:
        result = result.to_crs(original_crs)

    return result


def process_file(
    input_path: str | Path,
    output_path: str | Path,
    **compute_centerlines_kwargs,
) -> gpd.GeoDataFrame:
    """Read polygons from `input_path`, compute centerlines, write to `output_path`.

    Input/output formats are inferred from file extension (e.g. .shp,
    .geojson, .gpkg) via geopandas' read_file/to_file.
    """
    logger.info("Reading polygons from %s", input_path)
    gdf = gpd.read_file(input_path)

    result = compute_centerlines(gdf, **compute_centerlines_kwargs)

    logger.info("Writing centerlines to %s", output_path)
    result.to_file(output_path)
    return result

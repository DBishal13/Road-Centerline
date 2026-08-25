from __future__ import annotations

import logging
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Literal

import geopandas as gpd
import numpy as np
import pygeoops
import shapely

from road_centerline.attributes import add_road_attributes
from road_centerline.crs import CRSLike, resolve_working_crs
from road_centerline.densify import densify_geoseries
from road_centerline.formats import resolve_output_driver
from road_centerline.network import build_network as _build_network
from road_centerline.validate import find_unusable, repair_geometries

logger = logging.getLogger(__name__)


def _centerline_worker(args: tuple[list[bytes], dict]) -> list[bytes]:
    """Picklable ProcessPoolExecutor target: WKB in, WKB out (no CRS needed for this math)."""
    wkb_list, kwargs = args
    geoms = shapely.from_wkb(wkb_list)
    result = pygeoops.centerline(geoms, **kwargs)
    return shapely.to_wkb(result)


def _run_centerline(
    geometry: gpd.GeoSeries,
    *,
    on_error: Literal["raise", "skip"],
    n_jobs: int,
    **pygeoops_kwargs,
) -> tuple[gpd.GeoSeries, np.ndarray]:
    """Run pygeoops.centerline, honoring on_error/n_jobs.

    Returns (centerlines for the kept rows, boolean keep-mask over the input).
    The vectorized single-call fast path is used whenever possible; a bad
    geometry only triggers a per-row fallback (and only when on_error="skip").
    """
    keep = np.ones(len(geometry), dtype=bool)

    if n_jobs != 1:
        num_workers = n_jobs if n_jobs > 0 else os.cpu_count() or 1
        num_chunks = min(num_workers, len(geometry)) or 1
        chunks = [c for c in np.array_split(geometry.to_numpy(), num_chunks) if len(c)]
        wkb_chunks = [shapely.to_wkb(c).tolist() for c in chunks]
        with ProcessPoolExecutor(max_workers=num_workers) as pool:
            results = list(pool.map(_centerline_worker, [(c, pygeoops_kwargs) for c in wkb_chunks]))
        centerlines = np.concatenate([shapely.from_wkb(r) for r in results])
        return gpd.GeoSeries(centerlines, index=geometry.index, crs=geometry.crs), keep

    try:
        centerlines = pygeoops.centerline(geometry, **pygeoops_kwargs)
        return gpd.GeoSeries(centerlines, index=geometry.index, crs=geometry.crs), keep
    except Exception:
        if on_error == "raise":
            raise
        logger.warning(
            "Vectorized pygeoops.centerline call failed; falling back to per-row "
            "processing to isolate the offending geometry (on_error='skip')."
        )

    results: list = []
    for pos, (idx, geom) in enumerate(zip(geometry.index, geometry.to_numpy())):
        try:
            results.append(pygeoops.centerline(geom, **pygeoops_kwargs))
        except Exception as e:  # noqa: BLE001 - isolate whichever geometry pygeoops rejects
            logger.warning("Skipping row %s: pygeoops.centerline failed (%s).", idx, e)
            keep[pos] = False

    return gpd.GeoSeries(results, index=geometry.index[keep], crs=geometry.crs), keep


def compute_centerlines(
    gdf: gpd.GeoDataFrame,
    *,
    densify: bool = True,
    densify_distance: float = 10.0,
    target_crs: CRSLike | None = None,
    assume_crs: CRSLike | None = None,
    pygeoops_densify_distance: float = -1,
    min_branch_length: float = 10.0,
    simplifytolerance: float = -0.25,
    extend: bool = False,
    repair_invalid: bool = True,
    on_error: Literal["raise", "skip"] = "raise",
    add_attributes: bool = True,
    n_jobs: int = 1,
) -> gpd.GeoDataFrame:
    """Compute centerlines for a GeoDataFrame of polygons.

    CRS handling: math runs in a metric working CRS (an explicit
    `target_crs`, or an auto-estimated local UTM zone if the input is
    geographic, or the input's own CRS if already projected). The result is
    reprojected back to the input's original CRS before being returned.

    min_branch_length defaults to a fixed 10m rather than pygeoops' own
    auto mode (average-width-scaled). On compact, wide polygons like
    highway lane splits/merges, average width is large relative to branch
    length, so the auto threshold prunes real branches down to a stub that
    never reaches the polygon's ends. A fixed value tied to densify_distance
    avoids that; verified against real road-surface polygons.

    repair_invalid: run `shapely.make_valid` on the working geometry before
    densifying/centerlining. on_error="skip" drops rows that are still
    unusable afterward (or that individually fail inside pygeoops) instead
    of raising for the whole batch; "raise" (default) preserves the original
    fail-fast behavior.

    add_attributes: adds `length` and `est_width` columns (working-CRS
    units), computed before reprojecting back to the original CRS.

    n_jobs: 1 (default) keeps the single vectorized pygeoops.centerline call.
    Any other value chunks the geometry across a ProcessPoolExecutor
    (n_jobs>0: that many workers; -1: all cores) — only worth it for large
    batches, since process startup has real overhead.

    If you plan to call `build_network()` on the result, do so before any
    reprojection back to a geographic CRS — its `snap_tolerance` is a
    distance in the GeoDataFrame's own CRS units, which is meaningless in
    degrees. `process_file(..., build_network=True)` already handles this
    correctly by networking in the metric working CRS.
    """
    result, original_crs = _compute_centerlines_metric(
        gdf,
        densify=densify,
        densify_distance=densify_distance,
        target_crs=target_crs,
        assume_crs=assume_crs,
        pygeoops_densify_distance=pygeoops_densify_distance,
        min_branch_length=min_branch_length,
        simplifytolerance=simplifytolerance,
        extend=extend,
        repair_invalid=repair_invalid,
        on_error=on_error,
        add_attributes=add_attributes,
        n_jobs=n_jobs,
    )
    if original_crs is not None and result.crs != original_crs:
        result = result.to_crs(original_crs)
    return result


def _compute_centerlines_metric(
    gdf: gpd.GeoDataFrame,
    *,
    densify: bool = True,
    densify_distance: float = 10.0,
    target_crs: CRSLike | None = None,
    assume_crs: CRSLike | None = None,
    pygeoops_densify_distance: float = -1,
    min_branch_length: float = 10.0,
    simplifytolerance: float = -0.25,
    extend: bool = False,
    repair_invalid: bool = True,
    on_error: Literal["raise", "skip"] = "raise",
    add_attributes: bool = True,
    n_jobs: int = 1,
) -> tuple[gpd.GeoDataFrame, object | None]:
    """Same as `compute_centerlines`, but returns (result, original_crs) without
    reprojecting back — used internally so network building can happen in metric
    units before the final reprojection.
    """
    working_gdf, original_crs = resolve_working_crs(gdf, target_crs, assume_crs)
    working_gdf = working_gdf.copy()

    if repair_invalid:
        working_gdf.geometry = repair_geometries(working_gdf.geometry)

    unusable = find_unusable(working_gdf.geometry)
    if unusable.any():
        if on_error == "raise":
            bad_idx = working_gdf.index[unusable].tolist()
            raise ValueError(
                f"{unusable.sum()} geometr{'y is' if unusable.sum() == 1 else 'ies are'} "
                f"unusable (None/empty/non-polygonal) after repair: {bad_idx}. "
                "Pass on_error='skip' to drop these rows instead."
            )
        logger.warning(
            "Dropping %d unusable geometr%s (None/empty/non-polygonal): %s",
            unusable.sum(),
            "y" if unusable.sum() == 1 else "ies",
            working_gdf.index[unusable].tolist(),
        )
        working_gdf = working_gdf.loc[~unusable]

    polygon_areas = working_gdf.geometry.area

    if densify:
        working_gdf.geometry = densify_geoseries(working_gdf.geometry, densify_distance)

    centerlines, keep = _run_centerline(
        working_gdf.geometry,
        on_error=on_error,
        n_jobs=n_jobs,
        densify_distance=pygeoops_densify_distance,
        min_branch_length=min_branch_length,
        simplifytolerance=simplifytolerance,
        extend=extend,
    )
    if not keep.all():
        working_gdf = working_gdf.loc[keep]
        polygon_areas = polygon_areas.loc[keep]

    result = working_gdf.set_geometry(centerlines, crs=working_gdf.crs)

    if add_attributes:
        result = add_road_attributes(result, polygon_areas)

    return result, original_crs


def process_file(
    input_path: str | Path,
    output_path: str | Path,
    *,
    build_network: bool = False,
    snap_tolerance: float = 1.0,
    driver: str | None = None,
    **compute_centerlines_kwargs,
) -> gpd.GeoDataFrame:
    """Read polygons from `input_path`, compute centerlines, write to `output_path`.

    Input format is auto-detected by GDAL from the file's own content/
    signature (not just its extension), so it handles virtually any GIS
    vector format geopandas/pyogrio can read — Shapefile, GeoJSON,
    GeoPackage, FlatGeobuf, GML, KML, MapInfo, and dozens more.

    Output format is inferred from `output_path`'s extension where that's
    unambiguous. Some extensions (`.kml` in particular, which matches both
    the KML and LIBKML drivers) aren't — pass `driver` explicitly (e.g.
    `driver="KML"`; CLI: `--driver KML`) for those, or `AmbiguousDriverError`
    is raised rather than silently writing the wrong format.

    If `build_network` is set, the centerlines are additionally run through
    `road_centerline.build_network()` (in the metric working CRS, so
    `snap_tolerance` is a sane distance regardless of the input's own CRS)
    and written as edges/nodes: as two layers ("edges", "nodes") in the same
    file if `output_path` is a `.gpkg`, otherwise as `output_path` (edges)
    and `<stem>_nodes<suffix>` (nodes). Returns the edges GeoDataFrame in
    that case, reprojected back to the input's original CRS.
    """
    logger.info("Reading polygons from %s", input_path)
    gdf = gpd.read_file(input_path)
    resolved_driver = resolve_output_driver(output_path, driver)

    if not build_network:
        result = compute_centerlines(gdf, **compute_centerlines_kwargs)
        logger.info("Writing centerlines to %s", output_path)
        result.to_file(output_path, driver=resolved_driver)
        return result

    metric_result, original_crs = _compute_centerlines_metric(gdf, **compute_centerlines_kwargs)
    edges, nodes = _build_network(metric_result, snap_tolerance=snap_tolerance)
    if original_crs is not None:
        edges = edges.to_crs(original_crs)
        nodes = nodes.to_crs(original_crs)
    output_path = Path(output_path)
    if output_path.suffix.lower() == ".gpkg":
        logger.info("Writing network edges/nodes to %s (layers 'edges'/'nodes')", output_path)
        edges.to_file(output_path, layer="edges", driver=resolved_driver)
        nodes.to_file(output_path, layer="nodes", driver=resolved_driver)
    else:
        nodes_path = output_path.with_name(f"{output_path.stem}_nodes{output_path.suffix}")
        logger.info("Writing network edges to %s, nodes to %s", output_path, nodes_path)
        edges.to_file(output_path, driver=resolved_driver)
        nodes.to_file(nodes_path, driver=resolved_driver)
    return edges

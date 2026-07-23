from __future__ import annotations

import logging

import geopandas as gpd
import pyproj

from road_centerline.exceptions import MissingCRSError

logger = logging.getLogger(__name__)

CRSLike = str | int | pyproj.CRS


def resolve_working_crs(
    gdf: gpd.GeoDataFrame,
    target_crs: CRSLike | None = None,
    assume_crs: CRSLike | None = None,
) -> tuple[gpd.GeoDataFrame, pyproj.CRS | None]:
    """Return (gdf reprojected to a metric working CRS, original CRS).

    - If gdf has no CRS: use `assume_crs` if given, else raise MissingCRSError.
    - If `target_crs` is given: reproject to it unconditionally.
    - Elif the (possibly assumed) CRS is geographic: reproject to an
      auto-selected local UTM zone via `estimate_utm_crs()`, which works
      anywhere on Earth.
    - Else the CRS is already projected: return the GeoDataFrame unchanged.
    """
    if gdf.crs is None:
        if assume_crs is None:
            raise MissingCRSError(
                "GeoDataFrame has no CRS set. Pass assume_crs to specify what "
                "CRS the coordinates are actually in."
            )
        logger.warning("Input has no CRS; assuming %s.", assume_crs)
        gdf = gdf.set_crs(assume_crs)

    original_crs = gdf.crs

    if target_crs is not None:
        logger.info("Reprojecting to explicit target CRS %s.", target_crs)
        return gdf.to_crs(target_crs), original_crs

    if original_crs.is_geographic:
        utm_crs = gdf.estimate_utm_crs()
        logger.info(
            "Input CRS %s is geographic; reprojecting to estimated UTM CRS %s "
            "for metric distance calculations.",
            original_crs,
            utm_crs,
        )
        return gdf.to_crs(utm_crs), original_crs

    return gdf, original_crs

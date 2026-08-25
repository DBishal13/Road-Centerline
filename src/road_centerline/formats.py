from __future__ import annotations

import pyogrio

from road_centerline.exceptions import AmbiguousDriverError


def resolve_output_driver(path: object, driver: str | None) -> str | None:
    """Resolve the OGR driver to use for writing `path`.

    If `driver` is given, it's returned as-is — GDAL raises its own clear
    error for a genuinely invalid driver name.

    Otherwise, infers the driver from the file extension via
    `pyogrio.detect_write_driver`. Deliberately does not fall back to
    `GeoDataFrame.to_file()`'s own inference: for an extension pyogrio can't
    resolve unambiguously (e.g. `.kml`, which matches both the KML and
    LIBKML drivers), geopandas silently defaults to ESRI Shapefile instead
    of raising, producing valid-looking output in the *wrong* format with
    no error or warning. Raising `AmbiguousDriverError` here instead means
    a bad output path fails loudly, not silently.
    """
    if driver is not None:
        return driver
    try:
        return pyogrio.detect_write_driver(str(path))
    except ValueError as e:
        raise AmbiguousDriverError(
            f"{e} (Python API: pass driver=\"...\"; CLI: --driver ...). "
            "See https://gdal.org/en/stable/drivers/vector/ for available driver names."
        ) from e

class MissingCRSError(ValueError):
    """Raised when a GeoDataFrame has no CRS and none was assumed/provided."""


class AmbiguousDriverError(ValueError):
    """Raised when an output file's GIS driver can't be inferred from its extension.

    Some extensions (e.g. `.kml`, which matches both the KML and LIBKML GDAL
    drivers) are ambiguous. `GeoDataFrame.to_file()` silently falls back to
    ESRI Shapefile in this situation instead of raising — producing
    valid-looking output in the *wrong* format with no error. Pass an
    explicit driver (Python API: `driver=`; CLI: `--driver`) instead.
    """

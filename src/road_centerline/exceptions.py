class MissingCRSError(ValueError):
    """Raised when a GeoDataFrame has no CRS and none was assumed/provided."""

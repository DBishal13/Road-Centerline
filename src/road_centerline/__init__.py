from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("road-centerline")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

from road_centerline.core import compute_centerlines, process_file
from road_centerline.crs import resolve_working_crs
from road_centerline.densify import densify_geometry, densify_geoseries
from road_centerline.exceptions import MissingCRSError

__all__ = [
    "compute_centerlines",
    "process_file",
    "densify_geometry",
    "densify_geoseries",
    "resolve_working_crs",
    "MissingCRSError",
    "__version__",
]

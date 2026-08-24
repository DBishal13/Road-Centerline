from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("road-centerline")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

from road_centerline.attributes import add_road_attributes
from road_centerline.core import compute_centerlines, process_file
from road_centerline.crs import resolve_working_crs
from road_centerline.densify import densify_geometry, densify_geoseries
from road_centerline.exceptions import MissingCRSError
from road_centerline.network import build_network, to_networkx
from road_centerline.validate import find_unusable, repair_geometries

__all__ = [
    "MissingCRSError",
    "__version__",
    "add_road_attributes",
    "build_network",
    "compute_centerlines",
    "densify_geometry",
    "densify_geoseries",
    "find_unusable",
    "process_file",
    "repair_geometries",
    "resolve_working_crs",
    "to_networkx",
]

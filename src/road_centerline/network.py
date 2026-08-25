from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import geopandas as gpd
import numpy as np
import shapely
from shapely import Point
from shapely.strtree import STRtree

from road_centerline._unionfind import UnionFind

if TYPE_CHECKING:
    import networkx as nx

logger = logging.getLogger(__name__)


def _cluster_points(points: np.ndarray, tolerance: float) -> np.ndarray:
    """Return a cluster id per point, merging points within `tolerance` (transitively)."""
    n = len(points)
    uf = UnionFind(n)
    tree = STRtree([Point(p) for p in points])
    for i, p in enumerate(points):
        for j in tree.query(Point(p), predicate="dwithin", distance=tolerance):
            if j != i:
                uf.union(i, int(j))
    raw_ids = np.array([uf.find(i) for i in range(n)])
    _, cluster_ids = np.unique(raw_ids, return_inverse=True)
    return cluster_ids


def build_network(
    centerlines: gpd.GeoDataFrame, snap_tolerance: float = 1.0
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Turn per-polygon centerlines into a connected edge/node network.

    `compute_centerlines` produces one (Multi)LineString per input polygon,
    independent of its neighbors. Where two road polygons actually meet at a
    junction, their centerline endpoints land close together but not
    identically. This explodes multi-part centerlines into single-LineString
    edges and snaps endpoints within `snap_tolerance` of each other
    (transitively, via union-find over an STRtree `dwithin` query) into
    shared nodes, so the result is an actual routable graph rather than a
    pile of disconnected segments.

    Returns `(edges, nodes)`:
    - `edges`: original centerline attributes plus `u`/`v` node-id columns.
    - `nodes`: one row per node, with `node_id` and Point geometry (the
      centroid of the endpoints snapped into it).

    `snap_tolerance` is a distance in `centerlines`'s own CRS units, so a
    geographic CRS (degrees) is almost always a mistake here — e.g.
    `compute_centerlines()`'s output is reprojected back to the input's
    original CRS, which may be geographic even though the math ran in a
    metric UTM zone. Reproject to a metric CRS first if so.
    """
    if centerlines.crs is not None and centerlines.crs.is_geographic:
        logger.warning(
            "build_network: input CRS %s is geographic; snap_tolerance=%s is being "
            "interpreted in degrees, not meters. Reproject to a metric CRS first.",
            centerlines.crs,
            snap_tolerance,
        )

    edges = centerlines.explode(index_parts=False).reset_index(drop=True)
    edges = edges[edges.geometry.geom_type == "LineString"].reset_index(drop=True)

    starts = shapely.get_point(edges.geometry.values, 0)
    ends = shapely.get_point(edges.geometry.values, -1)
    start_coords = shapely.get_coordinates(starts)
    end_coords = shapely.get_coordinates(ends)
    all_coords = np.concatenate([start_coords, end_coords])

    cluster_ids = _cluster_points(all_coords, snap_tolerance)
    n = len(edges)
    edges["u"] = cluster_ids[:n]
    edges["v"] = cluster_ids[n:]

    node_coords = np.stack(
        [np.bincount(cluster_ids, weights=all_coords[:, 0]), np.bincount(cluster_ids, weights=all_coords[:, 1])],
        axis=1,
    ) / np.bincount(cluster_ids)[:, None]
    node_ids = np.arange(len(node_coords))
    nodes = gpd.GeoDataFrame(
        {"node_id": node_ids},
        geometry=[Point(xy) for xy in node_coords],
        crs=centerlines.crs,
    )

    return edges, nodes


def to_networkx(edges: gpd.GeoDataFrame, nodes: gpd.GeoDataFrame) -> nx.MultiGraph:
    """Build a `networkx.MultiGraph` from `build_network`'s output.

    Requires the optional `networkx` package: `pip install road-centerline[network]`.
    """
    try:
        import networkx as nx
    except ImportError as e:
        raise ImportError(
            "to_networkx requires the optional 'networkx' package. "
            "Install with `pip install road-centerline[network]`."
        ) from e

    graph = nx.MultiGraph()
    for row in nodes.itertuples(index=False):
        graph.add_node(row.node_id, geometry=row.geometry, x=row.geometry.x, y=row.geometry.y)

    reserved = {"geometry", "u", "v"}
    for row in edges.itertuples(index=False):
        row_dict = row._asdict()
        attrs = {k: v for k, v in row_dict.items() if k not in reserved}
        attrs["length"] = row.geometry.length
        graph.add_edge(row.u, row.v, geometry=row.geometry, **attrs)

    return graph

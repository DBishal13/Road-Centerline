from __future__ import annotations

import math
import warnings
from itertools import pairwise

import geopandas as gpd
import numpy as np
from shapely.ops import unary_union
from shapely.strtree import STRtree

from road_centerline._unionfind import UnionFind


def _orientation(geom) -> float:
    """Angle (degrees, 0-180) of the longest edge of `geom`'s minimum rotated rectangle.

    Used as a cheap proxy for a road polygon's overall direction. Shapely's
    `oriented_envelope` occasionally raises a RuntimeWarning on some real
    polygons even though the result is still valid (checked on every case
    encountered) — an internal GEOS numerical quirk, not a real error, so
    it's suppressed here rather than left to leak into callers.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        mrr = geom.minimum_rotated_rectangle
    coords = list(mrr.exterior.coords)
    best_len, best_angle = 0.0, 0.0
    for (x0, y0), (x1, y1) in pairwise(coords):
        length = math.hypot(x1 - x0, y1 - y0)
        if length > best_len:
            best_len = length
            best_angle = math.degrees(math.atan2(y1 - y0, x1 - x0)) % 180
    return best_angle


def _angle_diff(a: float, b: float) -> float:
    """Smallest difference between two 0-180-degree orientations."""
    d = abs(a - b) % 180
    return min(d, 180 - d)


def merge_parallel_polygons(
    gdf: gpd.GeoDataFrame,
    *,
    gap_threshold: float = 8.0,
    angle_threshold: float = 15.0,
    buffer_distance: float | None = None,
    aggfunc="first",
) -> gpd.GeoDataFrame:
    """Merge polygons that likely represent the same physical road split into
    separate carriageways/lanes, before centerlining.

    Real road datasets (OSM in particular) frequently split one physical
    road into several polygons — opposing carriageways, lanes, ramps. Each
    gets its own independent centerline by default, which is individually
    correct but reads as chaotic overlapping lines at a busy interchange
    where several such polygons converge.

    Grouping rule: two polygons are merge candidates if they're within
    `gap_threshold` of each other *and* their overall orientations (the
    longest edge of each polygon's minimum rotated rectangle) differ by
    less than `angle_threshold`. This is deliberately not an area-overlap
    metric (e.g. IoU) — verified on real data that IoU can't tell the two
    cases apart: a same-road parallel-carriageway pair can score IoU=0
    (they don't overlap, just sit close together), while a genuinely
    different crossing pair can also score ~0 despite real overlap, because
    road polygons vary too much in scale for the union denominator to mean
    anything. Gap + orientation is what actually distinguishes "same road,
    split into carriageways" (close together, parallel) from "different
    roads that happen to cross" (meet briefly, at a sharp angle).

    Grouping transitively via union-find, so A-close-to-B and B-close-to-C
    merges all three even if A and C aren't direct neighbors.

    For each group of more than one polygon: plain `unary_union` is not
    enough when there's a real gap between them (e.g. a median strip) — it
    silently returns a `MultiPolygon` of the disjoint parts rather than one
    merged shape, and centerlining that produces spurious bridging lines
    across the gap instead of one clean line. Each member is buffered
    outward by `buffer_distance` (default `gap_threshold / 2 + 0.5`) to
    close the gap, unioned, then buffered back in by the same amount.

    Both `gap_threshold` and `buffer_distance` are distances in `gdf`'s own
    CRS units — call this on already-metric-CRS geometry, same requirement
    as `densify_distance` elsewhere in this package.

    Adds a `merged_count` column (1 for untouched rows, >1 for merged
    groups) and aggregates every other non-geometry column via `aggfunc`
    (anything `DataFrame.groupby.agg` accepts — default `"first"`).

    This changes the output's row count and attribute values, so it's a
    deliberate preprocessing step callers opt into, not a silent default.
    """
    if buffer_distance is None:
        buffer_distance = gap_threshold / 2 + 0.5

    geoms = gdf.geometry.to_numpy()
    n = len(geoms)
    orientations = [_orientation(g) for g in geoms]

    uf = UnionFind(n)
    tree = STRtree(geoms)
    for i, geom in enumerate(geoms):
        for j in tree.query(geom, predicate="dwithin", distance=gap_threshold):
            j = int(j)
            if j <= i:
                continue
            if _angle_diff(orientations[i], orientations[j]) < angle_threshold:
                uf.union(i, j)

    raw_ids = np.array([uf.find(i) for i in range(n)])
    _, cluster_ids = np.unique(raw_ids, return_inverse=True)

    result = gdf.copy()
    result["merged_count"] = 0  # filled in below
    geometry_col = result.geometry.name

    for cluster_id in np.unique(cluster_ids):
        members = np.where(cluster_ids == cluster_id)[0]
        result.iloc[members, result.columns.get_loc("merged_count")] = len(members)
        if len(members) > 1:
            closed = unary_union([geoms[i].buffer(buffer_distance) for i in members]).buffer(
                -buffer_distance, join_style="mitre"
            )
            for i in members:
                result.iloc[i, result.columns.get_loc(geometry_col)] = closed

    result["_merge_cluster"] = cluster_ids
    merged = result.dissolve(by="_merge_cluster", aggfunc=aggfunc).reset_index(drop=True)
    return merged

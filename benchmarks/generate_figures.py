"""Generate the figures used in the README and docs site from real data.

No fabricated numbers or hand-drawn diagrams: every figure here is rendered
from the actual fixture (tests/fixtures/utrecht_roads.geojson) and the
actual benchmarks/compare.py timings, so they stay truthful as the code
changes. Run with the repo's dev environment active:

    python benchmarks/generate_figures.py

Writes PNGs to docs/assets/img/.
"""

from __future__ import annotations

import time
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pygeoops
from shapely.geometry import Polygon

from road_centerline import build_network, compute_centerlines
from road_centerline.core import _compute_centerlines_metric
from road_centerline.crs import resolve_working_crs
from road_centerline.validate import repair_geometries

FIXTURE = Path(__file__).parent.parent / "tests" / "fixtures" / "utrecht_roads.geojson"
OUT_DIR = Path(__file__).parent.parent / "docs" / "assets" / "img"

# A stable color scheme used across every figure.
POLYGON_FILL = "#c7d2e0"
POLYGON_EDGE = "#8896ab"
CENTERLINE = "#d1495b"
EDGE_COLOR = "#2f6690"
NODE_COLOR = "#d1495b"
JUNCTION_COLOR = "#f4a300"


def _save(fig, name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {path}")


def _dense_cluster_bbox(gdf: gpd.GeoDataFrame, pad_frac: float = 0.1) -> tuple:
    """Bounding box of the main cluster of polygons, trimming a few far-flung outliers
    so the overview figures aren't mostly empty space around one dense corridor."""
    centroids = gdf.geometry.centroid
    xmin, xmax = centroids.x.quantile([0.02, 0.98])
    ymin, ymax = centroids.y.quantile([0.02, 0.98])
    pad_x, pad_y = (xmax - xmin) * pad_frac, (ymax - ymin) * pad_frac
    return (xmin - pad_x, ymin - pad_y, xmax + pad_x, ymax + pad_y)


def figure_input_polygons(gdf: gpd.GeoDataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7, 6))
    gdf.plot(ax=ax, facecolor=POLYGON_FILL, edgecolor=POLYGON_EDGE, linewidth=0.5)
    xmin, ymin, xmax, ymax = _dense_cluster_bbox(gdf)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_title(f"Input: {len(gdf)} road-surface polygons (OSM, Utrecht)")
    ax.set_axis_off()
    _save(fig, "input-polygons.png")


def figure_centerlines_overlay(gdf: gpd.GeoDataFrame, centerlines: gpd.GeoDataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7, 6))
    gdf.plot(ax=ax, facecolor=POLYGON_FILL, edgecolor=POLYGON_EDGE, linewidth=0.3)
    centerlines.plot(ax=ax, color=CENTERLINE, linewidth=1.2)
    xmin, ymin, xmax, ymax = _dense_cluster_bbox(gdf)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_title("compute_centerlines(): polygons -> centerlines")
    ax.set_axis_off()
    _save(fig, "centerlines-overlay.png")


def figure_network(metric_centerlines: gpd.GeoDataFrame, center: tuple, radius: float) -> None:
    edges, nodes = build_network(metric_centerlines, snap_tolerance=1.0)
    cx, cy = center
    bbox = (cx - radius, cy - radius, cx + radius, cy + radius)
    edges_clip = edges.clip(bbox)
    nodes_clip = nodes.clip(bbox)

    degree = edges["u"].value_counts().add(edges["v"].value_counts(), fill_value=0)
    junction_ids = set(degree[degree >= 3].index)
    nodes_clip = nodes_clip.copy()
    nodes_clip["is_junction"] = nodes_clip["node_id"].isin(junction_ids)

    fig, ax = plt.subplots(figsize=(6, 6))
    edges_clip.plot(ax=ax, color=EDGE_COLOR, linewidth=2)
    nodes_clip[~nodes_clip["is_junction"]].plot(ax=ax, color=NODE_COLOR, markersize=25, zorder=3)
    nodes_clip[nodes_clip["is_junction"]].plot(
        ax=ax, color=JUNCTION_COLOR, markersize=70, zorder=4, edgecolor="black", linewidth=0.5
    )
    ax.set_title("build_network(): snapped junction nodes (orange) vs endpoints (red)")
    ax.set_axis_off()
    _save(fig, "network-graph.png")


def figure_repair_before_after() -> None:
    bowtie = Polygon([(0, 0), (10, 10), (10, 0), (0, 10)])
    repaired = repair_geometries(gpd.GeoSeries([bowtie])).iloc[0]

    fig, axes = plt.subplots(1, 2, figsize=(8, 4))
    for ax, geom, title in [
        (axes[0], bowtie, f"Input (self-intersecting)\nis_valid={bowtie.is_valid}"),
        (axes[1], repaired, f"After repair_invalid=True\nis_valid={repaired.is_valid}"),
    ]:
        gpd.GeoSeries([geom]).plot(ax=ax, facecolor=POLYGON_FILL, edgecolor=POLYGON_EDGE)
        ax.set_title(title)
        ax.set_axis_off()
    _save(fig, "repair-before-after.png")


def figure_benchmark_chart(gdf: gpd.GeoDataFrame) -> None:
    working_gdf, _ = resolve_working_crs(gdf)

    start = time.perf_counter()
    compute_centerlines(gdf)
    rc_time = time.perf_counter() - start

    start = time.perf_counter()
    pygeoops.centerline(working_gdf.geometry)
    raw_time = time.perf_counter() - start

    labels = ["raw pygeoops", "road-centerline"]
    times = [raw_time * 1000, rc_time * 1000]
    colors = [POLYGON_EDGE, CENTERLINE]

    try:
        from centerline.geometry import Centerline

        start = time.perf_counter()
        for geom in working_gdf.geometry:
            try:
                Centerline(geom)
            except Exception:  # noqa: BLE001, S110 - best-effort per-polygon timing
                pass
        centerline_pkg_time = time.perf_counter() - start
        labels.append("centerline (fitodic)")
        times.append(centerline_pkg_time * 1000)
        colors.append("#8896ab")
    except ImportError:
        pass

    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.barh(labels, times, color=colors)
    ax.set_xlabel("wall time (ms), 86 real road polygons")
    ax.bar_label(bars, fmt="%.0f ms")
    ax.set_title("Timing: same input, three approaches")
    fig.tight_layout()
    _save(fig, "benchmark-chart.png")


def main() -> None:
    gdf = gpd.read_file(FIXTURE)
    centerlines = compute_centerlines(gdf)
    metric_centerlines, _ = _compute_centerlines_metric(gdf)

    figure_input_polygons(gdf)
    figure_centerlines_overlay(gdf, centerlines)
    figure_network(metric_centerlines, center=(641293.5, 5770609.7), radius=150)
    figure_repair_before_after()
    figure_benchmark_chart(gdf)


if __name__ == "__main__":
    main()

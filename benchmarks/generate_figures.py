"""Generate the figures used in the README and docs site.

Styled like pygeoops'/shapely's own documentation figures, not a designed
graphic: plain matplotlib defaults, visible axes, small synthetic shapes for
concept diagrams (real data doesn't demonstrate the mechanism as clearly at
a glance), captions live in the surrounding markdown rather than baked into
the image. Every figure is rendered by actually calling road_centerline's
public API — nothing is hand-drawn or fabricated. Run with the repo's dev
environment active:

    python benchmarks/generate_figures.py

Writes to docs/assets/img/. The satellite-overlay figure additionally needs
network access (fetches basemap tiles via contextily) and the `contextily`
package (`pip install -e ".[docs]"` covers it) — every other figure is
offline and dependency-light by comparison.
"""

from __future__ import annotations

import time
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pygeoops
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

from road_centerline import build_network, compute_centerlines
from road_centerline.crs import resolve_working_crs
from road_centerline.validate import repair_geometries

FIXTURE = Path(__file__).parent.parent / "tests" / "fixtures" / "utrecht_roads.geojson"
OUT_DIR = Path(__file__).parent.parent / "docs" / "assets" / "img"

CRS = "EPSG:32633"  # arbitrary projected CRS; these figures use schematic, unitless coordinates
POLYGON_FILL = "#dddddd"
POLYGON_EDGE = "#999999"


def _save(fig, name: str, dpi: int = 150, **kwargs) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    fig.savefig(path, dpi=dpi, bbox_inches="tight", **kwargs)
    plt.close(fig)
    print(f"wrote {path}")


def _plot_line(ax, line: LineString, **kwargs) -> None:
    xs, ys = line.xy
    ax.plot(xs, ys, marker="o", markersize=5, **kwargs)


def figure_concept_centerline() -> None:
    """A simple 4-way road-crossing polygon and its centerline (single panel,
    no in-image title — matches pygeoops.centerline's own basic example)."""
    horiz, vert = box(0, 4, 12, 6), box(5, 0, 7, 10)
    cross = unary_union([horiz, vert])
    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[cross], crs=CRS)
    result = compute_centerlines(gdf, densify_distance=1.0, min_branch_length=1.0)
    centerline = result.geometry.iloc[0]

    fig, ax = plt.subplots(figsize=(4, 4))
    gpd.GeoSeries([cross]).plot(ax=ax, facecolor=POLYGON_FILL, edgecolor=POLYGON_EDGE)
    for part in centerline.geoms if centerline.geom_type == "MultiLineString" else [centerline]:
        _plot_line(ax, part, color="tab:blue")
    ax.set_aspect("equal")
    _save(fig, "concept-centerline.png")


def figure_concept_network() -> None:
    """Three independent centerline segments approaching a junction with
    slightly different endpoints (a), snapped by build_network() into one
    shared node (b) — the actual mechanism build_network() implements,
    not a real-data crop that's harder to parse at a glance."""
    lines = [
        LineString([(0, 5), (6.0, 5.0)]),
        LineString([(10, 1), (6.3, 5.2)]),
        LineString([(6.15, 5.35), (6, 10)]),
    ]
    gdf = gpd.GeoDataFrame({"id": [1, 2, 3]}, geometry=lines, crs=CRS)
    colors = ["tab:blue", "tab:orange", "tab:green"]

    fig, axes = plt.subplots(1, 2, figsize=(8, 4))

    ax = axes[0]
    for line, color in zip(lines, colors):
        _plot_line(ax, line, color=color)
    ax.set_title("a) independent centerlines")

    ax = axes[1]
    edges, nodes = build_network(gdf, snap_tolerance=1.0)
    for row, color in zip(edges.itertuples(), colors):
        _plot_line(ax, row.geometry, color=color)
    degree = edges["u"].value_counts().add(edges["v"].value_counts(), fill_value=0)
    junction = nodes[nodes["node_id"].isin(degree[degree >= 3].index)]
    junction.plot(ax=ax, color="tab:red", markersize=60, zorder=3)
    ax.set_title("b) build_network(): snapped to one node")

    for ax in axes:
        ax.set_aspect("equal")
        ax.set_xlim(-0.5, 10.5)
        ax.set_ylim(-0.5, 10.5)
    fig.tight_layout()
    _save(fig, "concept-network.png")


def figure_repair_before_after() -> None:
    bowtie = gpd.GeoSeries([Polygon([(0, 0), (10, 10), (10, 0), (0, 10)])])
    repaired = repair_geometries(bowtie)

    fig, axes = plt.subplots(1, 2, figsize=(8, 4.5))
    for ax, geoms, letter in [
        (axes[0], bowtie, "a) input"),
        (axes[1], repaired, "b) after repair_invalid=True"),
    ]:
        geoms.plot(ax=ax, facecolor=POLYGON_FILL, edgecolor=POLYGON_EDGE)
        ax.set_title(f"{letter}\nis_valid={geoms.iloc[0].is_valid}")
        ax.set_aspect("equal")
    fig.tight_layout()
    _save(fig, "repair-before-after.png")


CROP_CENTER, CROP_RADIUS = (641293.5, 5770609.7), 120


def _crop_bbox() -> tuple:
    cx, cy = CROP_CENTER
    return (cx - CROP_RADIUS, cy - CROP_RADIUS, cx + CROP_RADIUS, cy + CROP_RADIUS)


# A full stack interchange (loop ramps, roundabout, motorway) near Utrecht —
# found by rendering the whole fixture and looking for the densest tangle,
# not cherry-picked from outside the dataset already used everywhere else.
INTERCHANGE_BBOX_WGS84 = (5.058, 52.058, 5.082, 52.078)


def figure_real_interchange_satellite(gdf: gpd.GeoDataFrame) -> None:
    """The messiest real interchange in the fixture, overlaid on actual
    aerial imagery: input road-surface polygons vs. the extracted
    centerlines, side by side on the same satellite basemap. Requires
    network access and the optional `contextily` dependency."""
    import contextily as cx

    centerlines = compute_centerlines(gdf)
    gdf_clip = gdf.clip(INTERCHANGE_BBOX_WGS84).to_crs(3857)
    centerlines_clip = centerlines.clip(INTERCHANGE_BBOX_WGS84).to_crs(3857)

    fig, axes = plt.subplots(1, 2, figsize=(11, 5.6))

    gdf_clip.plot(
        ax=axes[0], facecolor="#ffdd00", edgecolor="#ffdd00", alpha=0.55, linewidth=0.5, zorder=2
    )
    axes[0].set_title("Input: road-surface polygons (OSM)", fontsize=11)

    centerlines_clip.plot(ax=axes[1], color="#ffdd00", linewidth=1.5, zorder=2)
    axes[1].set_title("compute_centerlines()", fontsize=11)

    for ax in axes:
        cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, zoom=16, attribution=False)
        ax.set_axis_off()
    fig.text(
        0.005,
        0.01,
        "Imagery: Esri, Maxar, Earthstar Geographics, and the GIS User Community",
        fontsize=6,
        color="dimgray",
    )
    fig.tight_layout()
    _save(
        fig,
        "real-interchange-satellite.jpg",
        dpi=140,
        format="jpg",
        pil_kwargs={"quality": 82, "optimize": True},
    )


def figure_real_junction_crop(metric_centerlines: gpd.GeoDataFrame) -> None:
    """The same real crop's network output: centerline endpoints snapped
    into a shared junction node."""
    edges, nodes = build_network(metric_centerlines, snap_tolerance=1.0)
    bbox = _crop_bbox()
    edges_clip, nodes_clip = edges.clip(bbox), nodes.clip(bbox)

    degree = edges["u"].value_counts().add(edges["v"].value_counts(), fill_value=0)
    junction_ids = set(degree[degree >= 3].index)
    nodes_clip = nodes_clip.copy()
    nodes_clip["is_junction"] = nodes_clip["node_id"].isin(junction_ids)

    fig, ax = plt.subplots(figsize=(4, 4))
    edges_clip.plot(ax=ax, color="tab:blue", linewidth=2)
    nodes_clip[nodes_clip["is_junction"]].plot(ax=ax, color="tab:red", markersize=50, zorder=3)
    ax.set_axis_off()  # real UTM coordinates aren't meaningful axis labels here
    _save(fig, "real-junction-crop.png")


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
    colors = ["tab:gray", "tab:blue"]

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
        colors.append("tab:orange")
    except ImportError:
        pass

    fig, ax = plt.subplots(figsize=(6, 3.5))
    bars = ax.barh(labels, times, color=colors)
    ax.set_xlabel("wall time (ms), 86 real road polygons")
    ax.bar_label(bars, fmt="%.0f ms")
    fig.tight_layout()
    _save(fig, "benchmark-chart.png")


def main() -> None:
    gdf = gpd.read_file(FIXTURE)
    working_gdf, _ = resolve_working_crs(gdf)
    metric_centerlines = compute_centerlines(gdf).to_crs(working_gdf.crs)

    figure_concept_centerline()
    figure_concept_network()
    figure_repair_before_after()
    figure_real_junction_crop(metric_centerlines)
    figure_real_interchange_satellite(gdf)
    figure_benchmark_chart(gdf)


if __name__ == "__main__":
    main()

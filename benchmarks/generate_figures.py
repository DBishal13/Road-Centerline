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
from matplotlib import patheffects
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

    fig, axes = plt.subplots(1, 2, figsize=(6, 3))

    ax = axes[0]
    for line, color in zip(lines, colors):
        _plot_line(ax, line, color=color)
    ax.set_title("a) independent centerlines", fontsize=9)

    ax = axes[1]
    edges, nodes = build_network(gdf, snap_tolerance=1.0)
    for row, color in zip(edges.itertuples(), colors):
        _plot_line(ax, row.geometry, color=color)
    degree = edges["u"].value_counts().add(edges["v"].value_counts(), fill_value=0)
    junction = nodes[nodes["node_id"].isin(degree[degree >= 3].index)]
    junction.plot(ax=ax, color="tab:red", markersize=60, zorder=3)
    ax.set_title("b) build_network(): snapped", fontsize=9)

    for ax in axes:
        ax.set_aspect("equal")
        ax.set_xlim(-0.5, 10.5)
        ax.set_ylim(-0.5, 10.5)
    fig.tight_layout()
    _save(fig, "concept-network.png")


def figure_repair_before_after() -> None:
    """make_valid on a self-intersecting bowtie splits it into two triangles
    that occupy the exact same pixels as the original — so the fix has to be
    shown by coloring the resulting parts differently, not by the shape
    changing (it doesn't; only its validity and part count do)."""
    bowtie = Polygon([(0, 0), (10, 10), (10, 0), (0, 10)])
    repaired = repair_geometries(gpd.GeoSeries([bowtie])).iloc[0]

    fig, axes = plt.subplots(1, 2, figsize=(6, 3.4))

    ax = axes[0]
    gpd.GeoSeries([bowtie]).plot(ax=ax, facecolor=POLYGON_FILL, edgecolor=POLYGON_EDGE)
    ax.set_title(f"a) input\n{bowtie.geom_type}, is_valid={bowtie.is_valid}", fontsize=9)

    ax = axes[1]
    part_colors = ["tab:blue", "tab:orange"]
    for part, color in zip(repaired.geoms, part_colors):
        gpd.GeoSeries([part]).plot(ax=ax, facecolor=color, edgecolor="white", alpha=0.85)
    ax.set_title(
        f"b) after repair_invalid=True\n{repaired.geom_type} of {len(repaired.geoms)}, "
        f"is_valid={repaired.is_valid}",
        fontsize=9,
    )

    for ax in axes:
        ax.set_aspect("equal")
    fig.tight_layout()
    _save(fig, "repair-before-after.png")


CROP_CENTER, CROP_RADIUS = (641293.5, 5770609.7), 120


def _crop_bbox() -> tuple:
    cx, cy = CROP_CENTER
    return (cx - CROP_RADIUS, cy - CROP_RADIUS, cx + CROP_RADIUS, cy + CROP_RADIUS)


# One real road-surface polygon near a stack interchange outside Utrecht:
# a motorway segment with an attached exit ramp and a loop ramp, all as one
# connected polygon. Found by rendering the whole fixture, locating its
# densest tangle, then picking the single polygon responsible for the most
# structurally interesting part of it (main line + branch + loop) rather
# than cropping a bbox where ~20 separate carriageway/ramp polygons overlap
# — that reads as chaotic spaghetti even though each line is individually
# correct, since it's really N separate correct answers drawn on top of
# each other. One clearly-bounded polygon in, one branching+looping
# centerline out is a far more honest demonstration of the same mechanism.
INTERCHANGE_OSM_ID = 1029265257
# Crop to just the branch+loop cluster (where the exit ramp splits off and
# loops back), not this polygon's full ~2.9km extent, so it fills the frame
# and individual lanes/vehicles are visible rather than a thin sliver.
INTERCHANGE_BBOX_3857 = (563550, 6811650, 564900, 6812300)
INTERCHANGE_ZOOM = 18
# Cyan translucent fill for the input polygon, thin magenta line on top for
# the centerline — different enough in both hue and weight that the line
# reads as a distinct object sitting on the fill, not just a thicker outline
# of it. Neither color occurs naturally in satellite imagery, so both stay
# high-contrast against every real background (fields, dirt, pavement).
INPUT_COLOR = "#00c8ff"
CENTERLINE_COLOR = "#ff2079"


def figure_real_interchange_satellite(gdf: gpd.GeoDataFrame) -> None:
    """One real road-surface polygon (a motorway segment with a branching
    exit ramp and a loop ramp), overlaid on actual aerial imagery: the input
    polygon (translucent fill) with its extracted centerline (thin line) on
    top, in the same panel. Requires network access and the optional
    `contextily` dependency."""
    import contextily as cx

    row = gdf[gdf["osm_id"] == INTERCHANGE_OSM_ID]
    # The default simplifytolerance (-0.25, pygeoops' own auto mode) visibly
    # cuts the corner on this loop ramp's tight curve radius. Lowering just
    # the tolerance (tried -0.1, -0.05) re-exposed the Voronoi skeleton's
    # natural zigzag noise on this polygon's long straight run instead —
    # simplifytolerance alone can't fix both a tight curve and a straight
    # run at once. densify_distance is the other lever: finer pre-
    # densification (5.0 vs the 10.0 default) gives the skeleton a more
    # uniform, symmetric set of boundary points to work from, which turned
    # out to remove the zigzag far more effectively than more aggressive
    # simplification did — confirmed by testing densify_distance up to 50
    # and disabled entirely, which made the zigzag worse, not better.
    # densify_distance=5 + simplifytolerance=-0.15 was the cleanest of every
    # combination tested on both the loop and the straight run. Per-figure
    # tuning choice, not a change to the library's defaults.
    centerline = compute_centerlines(row, densify_distance=5.0, simplifytolerance=-0.15)
    row_clip = row.to_crs(3857).clip(INTERCHANGE_BBOX_3857)
    centerline_clip = centerline.to_crs(3857).clip(INTERCHANGE_BBOX_3857)

    x0, y0, x1, y1 = INTERCHANGE_BBOX_3857
    fig, ax = plt.subplots(figsize=(9, 9 * (y1 - y0) / (x1 - x0)))
    row_clip.plot(
        ax=ax, facecolor=INPUT_COLOR, edgecolor=INPUT_COLOR, alpha=0.45, linewidth=0.8, zorder=2
    )
    centerline_clip.plot(ax=ax, color=CENTERLINE_COLOR, linewidth=1.3, zorder=3)
    cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, zoom=INTERCHANGE_ZOOM, attribution=False)
    ax.set_axis_off()
    ax.text(
        0.01,
        0.02,
        "Imagery: Esri, Maxar, Earthstar Geographics, and the GIS User Community",
        transform=ax.transAxes,
        fontsize=6,
        color="white",
        path_effects=[patheffects.withStroke(linewidth=2, foreground="black")],
    )
    fig.tight_layout()
    _save(
        fig,
        "real-interchange-satellite.jpg",
        dpi=150,
        format="jpg",
        pil_kwargs={"quality": 88, "optimize": True},
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


# The same stack interchange used by figure_real_interchange_satellite, but
# the full area (not one isolated polygon) — this is where ~20 separate
# carriageway/ramp polygons genuinely converge, the case merge_parallel_
# polygons() targets. Self-contained: clips the fixture itself rather than
# depending on any file from outside the repo.
MERGE_AREA_BBOX_WGS84 = (5.058, 52.058, 5.082, 52.078)
MERGE_CROSSING_BBOX_3857 = (564450, 6811550, 565150, 6812450)


def figure_merge_before_after(gdf: gpd.GeoDataFrame) -> None:
    """The real interchange's busiest crossing point, before and after
    merge_parallel_polygons(): many individually-correct-but-overlapping
    centerlines vs. one clean line per physical road. Requires network
    access and the optional `contextily` dependency."""
    import contextily as cx

    area = gdf.clip(MERGE_AREA_BBOX_WGS84)
    before = compute_centerlines(area)
    after = compute_centerlines(area, merge_parallel=True)

    before_clip = before.to_crs(3857).clip(MERGE_CROSSING_BBOX_3857)
    after_clip = after.to_crs(3857).clip(MERGE_CROSSING_BBOX_3857)

    fig, axes = plt.subplots(1, 2, figsize=(9, 4.6))
    before_clip.plot(ax=axes[0], color=CENTERLINE_COLOR, linewidth=1.6, zorder=2)
    axes[0].set_title(f"Before: {len(before)} separate centerlines", fontsize=9)

    after_clip.plot(ax=axes[1], color=CENTERLINE_COLOR, linewidth=1.6, zorder=2)
    axes[1].set_title(f"After merge_parallel=True: {len(after)} centerlines", fontsize=9)

    for ax in axes:
        cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, zoom=17, attribution=False)
        ax.set_axis_off()
    axes[0].text(
        0.01,
        0.02,
        "Imagery: Esri, Maxar, Earthstar Geographics, and the GIS User Community",
        transform=axes[0].transAxes,
        fontsize=5,
        color="white",
        path_effects=[patheffects.withStroke(linewidth=2, foreground="black")],
    )
    fig.tight_layout()
    _save(
        fig,
        "merge-before-after.jpg",
        dpi=150,
        format="jpg",
        pil_kwargs={"quality": 88, "optimize": True},
    )


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
    figure_merge_before_after(gdf)
    figure_benchmark_chart(gdf)


if __name__ == "__main__":
    main()

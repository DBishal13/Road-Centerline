# Building a connected network

`compute_centerlines()` produces one (Multi)LineString per input polygon,
independent of its neighbors. Where two road polygons actually meet at a
junction, their centerline endpoints land close together but not
identically — neither `pygeoops` nor the `centerline` package resolve this;
each polygon just becomes its own disconnected line.

`build_network()` explodes multi-part centerlines into single-line edges and
snaps endpoints within `snap_tolerance` of each other (transitively) into
shared nodes, so the result is an actual routable graph:

![Centerline endpoints snapped into shared junction nodes](assets/img/network-graph.png)

Orange nodes are junctions (three or more edges meet there); red nodes are
plain endpoints. This is a real crop of the demo fixture — see [Demo](demo.md).

## Usage

```python
from road_centerline import compute_centerlines, build_network, to_networkx

# Network building is distance-based, so do it before reprojecting to a
# geographic CRS — process_file(..., build_network=True) handles this for
# you automatically.
centerlines = compute_centerlines(gdf, target_crs="EPSG:32633")
edges, nodes = build_network(centerlines, snap_tolerance=1.0)

# Optional: pip install road-centerline[network]
graph = to_networkx(edges, nodes)
```

`edges` keeps every original centerline attribute plus `u`/`v` node-id
columns; `nodes` has one row per node (`node_id`, Point geometry at the
centroid of the endpoints snapped into it).

## Via the CLI / `process_file`

```sh
road-centerline Road.shp Road_Centerline.gpkg --build-network --snap-tolerance 1.0
```

`process_file(..., build_network=True)` runs `build_network()` in the
metric working CRS (so `snap_tolerance` is a sane distance regardless of the
input's own CRS), then reprojects the result back. Output is written as two
layers (`edges`, `nodes`) if the output path is `.gpkg`, otherwise as the
given path plus a sibling `<stem>_nodes<suffix>` file.

## API reference

::: road_centerline.network.build_network

::: road_centerline.network.to_networkx

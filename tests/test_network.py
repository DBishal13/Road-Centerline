import geopandas as gpd
import pytest
from shapely.geometry import LineString

from road_centerline.network import build_network, to_networkx


def test_endpoints_within_tolerance_share_one_node():
    l1 = LineString([(0, 0), (10, 0)])
    l2 = LineString([(10.3, 0), (20, 0)])  # 0.3m from l1's end
    gdf = gpd.GeoDataFrame({"id": [1, 2]}, geometry=[l1, l2], crs="EPSG:32633")

    edges, nodes = build_network(gdf, snap_tolerance=1.0)

    assert len(nodes) == 3  # l1 start, shared junction, l2 end
    shared_node = edges.loc[edges["id"] == 1, "v"].iloc[0]
    assert edges.loc[edges["id"] == 2, "u"].iloc[0] == shared_node


def test_endpoints_beyond_tolerance_stay_separate():
    l1 = LineString([(0, 0), (10, 0)])
    l2 = LineString([(15, 0), (20, 0)])  # 5m from l1's end
    gdf = gpd.GeoDataFrame({"id": [1, 2]}, geometry=[l1, l2], crs="EPSG:32633")

    _edges, nodes = build_network(gdf, snap_tolerance=1.0)

    assert len(nodes) == 4


def test_multilinestring_centerline_explodes_into_edges():
    from shapely.geometry import MultiLineString

    branching = MultiLineString(
        [LineString([(0, 0), (10, 0)]), LineString([(10, 0), (10, 10)])]
    )
    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[branching], crs="EPSG:32633")

    edges, nodes = build_network(gdf, snap_tolerance=1.0)

    assert len(edges) == 2
    assert len(nodes) == 3
    assert set(edges["id"]) == {1}


def test_geographic_crs_logs_warning(caplog):
    l1 = LineString([(0, 0), (1, 0)])
    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[l1], crs="EPSG:4326")

    with caplog.at_level("WARNING"):
        build_network(gdf, snap_tolerance=1.0)

    assert "geographic" in caplog.text


def test_to_networkx_without_networkx_installed_raises_helpful_error(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "networkx":
            raise ImportError("no networkx")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    l1 = LineString([(0, 0), (10, 0)])
    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[l1], crs="EPSG:32633")
    edges, nodes = build_network(gdf)

    with pytest.raises(ImportError, match="road-centerline\\[network\\]"):
        to_networkx(edges, nodes)


def test_to_networkx_builds_graph_with_node_and_edge_attrs():
    pytest.importorskip("networkx")

    l1 = LineString([(0, 0), (10, 0)])
    l2 = LineString([(10, 0), (20, 0)])
    gdf = gpd.GeoDataFrame({"id": [1, 2]}, geometry=[l1, l2], crs="EPSG:32633")
    edges, nodes = build_network(gdf, snap_tolerance=1.0)

    graph = to_networkx(edges, nodes)

    assert graph.number_of_nodes() == len(nodes)
    assert graph.number_of_edges() == len(edges)
    u, v = edges[["u", "v"]].iloc[0]
    edge_data = graph.get_edge_data(u, v)[0]
    assert edge_data["id"] == 1
    assert edge_data["length"] == pytest.approx(10.0)

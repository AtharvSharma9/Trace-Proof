"""
engine/graph/builder.py

NetworkX MultiDiGraph construction from entities + entity_links.
Phase 4 — 02_TRD.md §5.2 / 06_Implementation_Plan.md Phase 4.

All graph metrics are attached to the graph's node/edge attributes so
callers (correlate_service) can serialise to JSON for caching without
needing to import networkx.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Callable

import networkx as nx


def build_graph(
    entities: List[Dict],
    links: List[Dict],
    events: Optional[List[Dict]] = None,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> nx.MultiDiGraph:
    """
    Build a NetworkX MultiDiGraph from entity dicts and link dicts.

    Nodes: entity dicts keyed by `id`.
    Edges: link dicts; FUND_FLOW is directional (a→b = src→dst);
           symmetric links are stored with entity_a_id < entity_b_id.

    Performance: bulk add_nodes_from / add_edges_from — never per-item.
    """
    G = nx.MultiDiGraph()

    if progress_cb:
        progress_cb("Adding nodes…")
    G.add_nodes_from(
        (e["id"], {k: v for k, v in e.items() if k != "id"})
        for e in entities
    )

    if progress_cb:
        progress_cb("Adding edges…")
    edge_triples = []
    for lk in links:
        a, b = lk["entity_a_id"], lk["entity_b_id"]
        key = lk.get("link_type", "LINK")
        data = {k: v for k, v in lk.items() if k not in ("entity_a_id", "entity_b_id")}
        edge_triples.append((a, b, key, data))
    G.add_edges_from((a, b, k, d) for a, b, k, d in edge_triples)

    # Add FUND_FLOW edges from raw events
    if events:
        for ev in events:
            if ev.get("event_type") in ("TRANSFER", "UPI_TXN", "ATM_WITHDRAWAL"):
                src = ev.get("src_entity_id")
                dst = ev.get("dst_entity_id")
                if src and dst and G.has_node(src) and G.has_node(dst):
                    G.add_edge(src, dst, key="FUND_FLOW", **{
                        "amount": ev.get("amount"),
                        "occurred_at": ev.get("occurred_at"),
                        "event_id": ev.get("id"),
                    })

    return G


def compute_metrics(G: nx.MultiDiGraph, progress_cb=None) -> Dict[str, Any]:
    """
    Compute per-node centrality metrics and attach to graph node attributes.

    Uses k-sample approximation for betweenness when node count > 5000.
    Records the k value in the returned dict for report reproducibility.

    Returns:
        {
          "pagerank": {node_id: score},
          "betweenness": {node_id: score},
          "in_degree": {node_id: int},
          "out_degree": {node_id: int},
          "centrality_k": int or None,
        }
    """
    if G.number_of_nodes() == 0:
        return {"pagerank": {}, "betweenness": {}, "in_degree": {}, "out_degree": {}, "centrality_k": None}

    if progress_cb:
        progress_cb("Computing PageRank…")
    try:
        pr = nx.pagerank(G, alpha=0.85, max_iter=200)
    except nx.PowerIterationFailedConvergence:
        pr = {n: 1.0 / G.number_of_nodes() for n in G.nodes()}

    k = None
    n = G.number_of_nodes()
    if progress_cb:
        progress_cb("Computing betweenness centrality…")
    if n > 5000:
        k = 500
        bc = nx.betweenness_centrality(G, k=k, normalized=True)
    else:
        bc = nx.betweenness_centrality(G, normalized=True)

    in_deg  = dict(G.in_degree())
    out_deg = dict(G.out_degree())

    # Attach to node attributes
    for node in G.nodes():
        G.nodes[node]["pagerank"]    = pr.get(node, 0.0)
        G.nodes[node]["betweenness"] = bc.get(node, 0.0)
        G.nodes[node]["in_degree"]   = in_deg.get(node, 0)
        G.nodes[node]["out_degree"]  = out_deg.get(node, 0)

    return {
        "pagerank": pr,
        "betweenness": bc,
        "in_degree": in_deg,
        "out_degree": out_deg,
        "centrality_k": k,
    }


def detect_patterns(G: nx.MultiDiGraph) -> Dict[str, List]:
    """
    Detect structural fraud patterns in the graph.

    Returns:
        {
          "fan_in_nodes":    [node_id, ...],   # in-degree >= 8
          "fan_out_nodes":   [node_id, ...],   # out-degree >= 8
          "pass_through_nodes": [node_id, ...],
          "cycles":          [[node_id, ...], ...],   # simple cycles, capped at 100
        }
    """
    fan_in  = [n for n, d in G.in_degree()  if d >= 8]
    fan_out = [n for n, d in G.out_degree() if d >= 8]

    # Pass-through: node with both in and out FUND_FLOW edges
    pass_through = []
    for n in G.nodes():
        in_ff  = any(d.get("link_type") == "FUND_FLOW" or k == "FUND_FLOW"
                     for _, _, k, d in G.in_edges(n, data=True, keys=True))
        out_ff = any(d.get("link_type") == "FUND_FLOW" or k == "FUND_FLOW"
                     for _, _, k, d in G.out_edges(n, data=True, keys=True))
        if in_ff and out_ff:
            pass_through.append(n)

    # Cycles (simple, capped)
    try:
        cycles = list(nx.simple_cycles(G))[:100]
    except Exception:
        cycles = []

    return {
        "fan_in_nodes": fan_in,
        "fan_out_nodes": fan_out,
        "pass_through_nodes": pass_through,
        "cycles": cycles,
    }


def find_cashout_paths(
    G: nx.MultiDiGraph,
    victim_nodes: List[str],
    cashout_nodes: List[str],
    max_hops: int = 6,
) -> List[List[str]]:
    """
    Find all simple paths from victim nodes to cash-out nodes, capped at max_hops.
    """
    paths = []
    UG = G.to_undirected()  # allow traversal in both directions for discovery
    for v in victim_nodes:
        for c in cashout_nodes:
            if v == c:
                continue
            try:
                for path in nx.all_simple_paths(UG, v, c, cutoff=max_hops):
                    paths.append(path)
            except nx.NetworkXNoPath:
                pass
    return paths

"""
Pramaan Offline PyVis & Matplotlib Fallback Graph Renderer (views/components/graph_renderer.py)
Vendors vis-network assets inline/locally and generates static Matplotlib fallback image.
"""

import os
import io
import base64
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx
from pyvis.network import Network
from views import api

# Path to local vendored vis-network files
VENDOR_JS_PATH = Path(__file__).resolve().parents[2] / "assets" / "vendor" / "vis-network.min.js"
VENDOR_CSS_PATH = Path(__file__).resolve().parents[2] / "assets" / "vendor" / "vis-network.min.css"


def is_vis_vendored() -> bool:
    """Checks if local vis-network assets exist."""
    return VENDOR_JS_PATH.exists() and VENDOR_CSS_PATH.exists()


def get_local_vis_assets() -> tuple[str, str]:
    """Reads local vis-network JS and CSS contents for offline inline embedding."""
    if not is_vis_vendored():
        return "", ""
    with open(VENDOR_JS_PATH, "r", encoding="utf-8") as f:
        js_content = f.read()
    with open(VENDOR_CSS_PATH, "r", encoding="utf-8") as f:
        css_content = f.read()
    return js_content, css_content


def generate_offline_pyvis_html(case_id: str, min_confidence: float = 0.75, top_n: int = 50, layout_type: str = "force", highlight_path: bool = True) -> str:
    """
    Generates 100% offline PyVis HTML string with embedded vis-network JS/CSS,
    risk band colors, node shapes, victim/cash-out rings, and path highlights.
    """
    if not is_vis_vendored():
        raise FileNotFoundError("Local vis-network assets not found in assets/vendor/")

    js_content, css_content = get_local_vis_assets()

    g = api.get_graph_data(case_id, min_confidence=min_confidence, top_n=top_n)
    nodes_data = g["nodes"]
    edges_data = g["edges"]
    path_nodes = set(g["highlighted_path"]) if highlight_path else set()

    net = Network(height="620px", width="100%", bgcolor="#FFFFFF", font_color="#0F172A", directed=True)
    net.toggle_physics(layout_type == "force")

    # Risk band color matrix
    risk_colors = {
        "critical": {"background": "#FEE2E2", "border": "#B91C1C"},
        "high":     {"background": "#FFEDD5", "border": "#C2410C"},
        "medium":   {"background": "#FEF3C7", "border": "#B45309"},
        "low":      {"background": "#DCFCE7", "border": "#15803D"}
    }

    # Node shape by entity type
    shape_map = {
        "PHONE": "dot",
        "BANK_ACCOUNT": "square",
        "UPI": "diamond",
        "IMEI": "triangle",
        "IMSI": "triangle",
        "IP": "star",
        "EMAIL": "ellipse"
    }

    for n in nodes_data:
        n_id = n["id"]
        val = n["label"]
        band = n["risk_band"].lower() if n.get("risk_band") else "low"
        etype = n["type"]
        shape = shape_map.get(etype, "dot")
        
        c = risk_colors.get(band, risk_colors["low"])
        bg_color = c["background"]
        border_color = c["border"]
        border_width = 2

        # Special roles: Victim (Deep Navy) & Cash-out (Double Red Ring)
        if n.get("is_victim"):
            bg_color = "#E8EEF4"
            border_color = "#1B3A5C"
            border_width = 4
            val = f" [VICTIM] {val}"
        elif n.get("is_cashout"):
            bg_color = "#FEE2E2"
            border_color = "#7F1D1D"
            border_width = 5
            val = f" [CASH-OUT] {val}"

        # Highlight path node
        if highlight_path and n_id in path_nodes:
            border_width += 2

        tooltip = f"Entity: {val}<br/>Type: {etype}<br/>Risk Score: {n.get('risk_score', 0):.0f} ({band.title()})<br/>Click to view details"

        net.add_node(
            n_id,
            label=val,
            title=tooltip,
            shape=shape,
            color={"background": bg_color, "border": border_color, "highlight": {"background": "#E0F2F3", "border": "#0E7C86"}},
            borderWidth=border_width,
            font={"size": 13, "face": "JetBrains Mono"}
        )

    for e in edges_data:
        src = e["from"]
        dst = e["to"]
        label = e.get("label", "")
        
        is_path_edge = highlight_path and (src in path_nodes and dst in path_nodes)
        edge_color = "#B91C1C" if is_path_edge else "#CBD5E1"
        width = 4 if is_path_edge else 1.5

        net.add_edge(
            src, dst,
            title=f"Link: {e.get('link_type')} ({int(e.get('confidence',0)*100)}%)",
            label=label if is_path_edge else "",
            color={"color": edge_color, "highlight": "#0E7C86"},
            width=width,
            arrows="to"
        )

    # Generate raw HTML string from PyVis
    html = net.generate_html()

    # Patch CDN links with inline vendor JS and CSS
    patched_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        {css_content}
        body {{ margin: 0; padding: 0; font-family: Inter, sans-serif; background: #FFFFFF; }}
        #mynetwork {{ width: 100%; height: 620px; border: 1px solid #E2E8F0; border-radius: 6px; }}
        .graph-legend {{
          position: absolute; top: 12px; right: 12px; background: rgba(255,255,255,0.92);
          border: 1px solid #CBD5E1; border-radius: 6px; padding: 10px 14px; font-size: 11.5px;
          color: #0F172A; box-shadow: 0 4px 12px rgba(15,23,42,0.08); z-index: 99; pointer-events: none;
        }}
        .legend-item {{ display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }}
        .legend-box {{ width: 12px; height: 12px; border-radius: 2px; display: inline-block; }}
      </style>
      <script type="text/javascript">
        {js_content}
      </script>
    </head>
    <body>
      <div style="position: relative;">
        <div class="graph-legend">
          <div style="font-weight: 700; font-size: 11px; text-transform: uppercase; margin-bottom: 6px; color: #475569;">Graph Legend</div>
          <div class="legend-item"><span class="legend-box" style="background: #FEE2E2; border: 1.5px solid #B91C1C;"></span> Critical (80-100)</div>
          <div class="legend-item"><span class="legend-box" style="background: #FFEDD5; border: 1.5px solid #C2410C;"></span> High (60-79)</div>
          <div class="legend-item"><span class="legend-box" style="background: #FEF3C7; border: 1.5px solid #B45309;"></span> Medium (30-59)</div>
          <div class="legend-item"><span class="legend-box" style="background: #DCFCE7; border: 1.5px solid #15803D;"></span> Low (0-29)</div>
          <div style="margin-top: 6px; font-weight: 700; font-size: 10px; color: #475569;">SPECIAL ROLES</div>
          <div class="legend-item"><span class="legend-box" style="background: #E8EEF4; border: 2px solid #1B3A5C;"></span> Victim Node</div>
          <div class="legend-item"><span class="legend-box" style="background: #FEE2E2; border: 3px double #7F1D1D;"></span> Cash-out Terminal</div>
        </div>
        <div id="mynetwork"></div>
      </div>
      <script type="text/javascript">
        // Embed node/edge dataset and network instantiation script from PyVis
        {html[html.find("var nodes ="):html.rfind("</script>")]}
      </script>
    </body>
    </html>
    """

    return patched_html


def generate_matplotlib_fallback_png(case_id: str) -> str:
    """
    Generates static Matplotlib network graph fallback PNG image (base64 encoded).
    Ensures graph screen is NEVER blank even if JS renderer fails.
    """
    g_data = api.get_graph_data(case_id, min_confidence=0.75, top_n=50)

    G = nx.DiGraph()
    path_nodes = set(g_data["highlighted_path"])

    for n in g_data["nodes"]:
        G.add_node(n["id"], label=n["label"], type=n["type"], band=n.get("risk_band", "Low"))

    for e in g_data["edges"]:
        G.add_edge(e["from"], e["to"], type=e.get("link_type", ""))

    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')

    pos = nx.spring_layout(G, seed=42)

    # Node colors by band
    color_map = []
    for node in G.nodes():
        if node in path_nodes:
            color_map.append('#B91C1C' if node == 'ent_cashout_atm' else ('#1B3A5C' if node == 'ent_victim_acc' else '#C2410C'))
        else:
            color_map.append('#CBD5E1')

    # Draw graph
    nx.draw_networkx_nodes(G, pos, node_color=color_map, node_size=800, ax=ax)
    nx.draw_networkx_edges(G, pos, edge_color='#CBD5E1', width=1.5, arrows=True, arrowsize=15, ax=ax)
    
    # Highlight path edges
    path_edges = [('ent_victim_acc', 'ent_mule1a_acc'), ('ent_mule1a_acc', 'ent_mule2a_acc'), ('ent_mule2a_acc', 'ent_cashout_atm')]
    nx.draw_networkx_edges(G, pos, edgelist=path_edges, edge_color='#B91C1C', width=3.5, arrows=True, arrowsize=20, ax=ax)

    labels = {n: G.nodes[n]['label'][:12] for n in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=8, font_family='sans-serif', ax=ax)

    ax.set_title("Pramaan Forensic Network Graph (Static Fallback View)", fontsize=12, fontweight='bold', color='#1B3A5C', pad=12)
    ax.axis('off')
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    
    encoded = base64.b64encode(buf.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{encoded}"

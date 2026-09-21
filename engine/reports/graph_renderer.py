import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path

def render_static_graph(graph: nx.Graph, output_path: str) -> None:
    """
    Renders a static network graph using matplotlib at 300 DPI.
    Highlights Victim and Cash-out nodes.
    """
    plt.figure(figsize=(10, 6))
    
    # Custom color logic
    node_colors = []
    for n, d in graph.nodes(data=True):
        role = d.get('role', '')
        if role == 'VICTIM':
            node_colors.append('#1B3A5C')
        elif role == 'CASHOUT':
            node_colors.append('#7F1D1D')
        else:
            node_colors.append('#94A3B8') # default grey
            
    pos = nx.spring_layout(graph, seed=42)
    nx.draw(graph, pos, node_color=node_colors, with_labels=True, 
            node_size=500, font_size=8, font_color='white', edge_color='#CBD5E1')
            
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()

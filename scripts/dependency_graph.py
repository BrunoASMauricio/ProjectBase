#!/usr/bin/env python3

import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

def BuildGraph(repos_data, data_name):
    """Create a directed graph of repository dependencies."""
    graph = nx.DiGraph()
    
    # Add all repositories as nodes
    for repo_id, repo_data in repos_data.items():
        repo_name = repo_data.get("name", repo_id)
        graph.add_node(repo_name, **repo_data)
    
    # Add dependency edges
    for repo_id, repo_data in repos_data.items():
        source = repo_data.get("name", repo_id)
        dependencies = repo_data.get(data_name, {})
        
        for dep_id, dep_info in dependencies.items():
            # If it's a URL as key, use it directly
            if dep_id.startswith("http") or dep_id.startswith("git@"):
                target_id = dep_id
            # If it's a name or other identifier, look for URL in dep_info
            elif "url" in dep_info:
                target_id = dep_info["url"]
            else:
                # Skip if we can't determine the target
                continue
                
            # Find the target node
            target = None
            for rid, rdata in repos_data.items():
                if rid == target_id or rdata.get("url") == target_id:
                    target = rdata.get("name", rid)
                    break
            
            if target and target in graph:
                graph.add_edge(source, target)
    
    return graph

def VisualizeGraph(graph, data_name):
    """Visualize the dependency graph."""
    plt.figure(figsize=(18, 14))
    
    # Use a hierarchical layout
    pos = nx.drawing.nx_agraph.graphviz_layout(graph, prog="dot")  # 'dot' is best for hierarchies

    # Generate a custom colormap
    cmap = LinearSegmentedColormap.from_list("repo_colors", ["#4287f5", "#42f5a7", "#f542d4"])
    
    # Draw the graph
    nx.draw_networkx_nodes(graph, pos, node_size=1000, node_color=range(len(graph)), cmap=cmap, alpha=0.8)

    def wrap_label(text, max_width=12):
        return "\n".join([text[i:i+max_width] for i in range(0, len(text), max_width)])

    labels = {node: wrap_label(str(node)) for node in graph.nodes()}
    font_size = max(6, 12 - len(graph) // 10)
    nx.draw_networkx_labels(graph, pos, labels=labels, font_size=font_size)

    nx.draw_networkx_edges(graph, pos, width=1.5, alpha=0.7, arrows=True, arrowsize=15)
    
    plt.title(f"Repository {data_name} Graph", fontsize=16)
    plt.axis("off")
    plt.tight_layout()

    plt.show(block=False)

"""Graph persistence — Save and load the epistemic graph to/from disk."""

from pathlib import Path

import networkx as nx
from rich.console import Console

from uid_engine import config
from uid_engine.graph.builder import EpistemicGraph

console = Console()


def _sanitize_graph_for_graphml(graph: nx.DiGraph) -> nx.DiGraph:
    """Create a copy of the graph with all attributes converted to GraphML-compatible types."""
    clean_g = nx.DiGraph()
    
    for node, data in graph.nodes(data=True):
        clean_data = {}
        for k, v in data.items():
            if v is None:
                clean_data[k] = ""
            elif isinstance(v, (str, int, float, bool)):
                clean_data[k] = v
            else:
                clean_data[k] = str(v)
        clean_g.add_node(node, **clean_data)

    for u, v, data in graph.edges(data=True):
        clean_data = {}
        for k, val in data.items():
            if val is None:
                clean_data[k] = ""
            elif isinstance(val, (str, int, float, bool)):
                clean_data[k] = val
            else:
                clean_data[k] = str(val)
        clean_g.add_edge(u, v, **clean_data)

    return clean_g


def save_graph(graph: EpistemicGraph, filename: str | None = None) -> Path:
    """Save the epistemic graph to a GraphML file.

    Args:
        graph: The EpistemicGraph to save.
        filename: Optional filename. Defaults to config.DEFAULT_GRAPH_FILE.

    Returns:
        Path to the saved file.
    """
    filename = filename or config.DEFAULT_GRAPH_FILE
    filepath = config.GRAPHS_DIR / filename
    sanitized_graph = _sanitize_graph_for_graphml(graph.graph)
    nx.write_graphml(sanitized_graph, str(filepath))
    console.print(f"[bold green]✓ Graph saved to {filepath}[/bold green]")
    return filepath


def load_graph(filename: str | None = None) -> EpistemicGraph:
    """Load an epistemic graph from a GraphML file.

    Args:
        filename: Optional filename. Defaults to config.DEFAULT_GRAPH_FILE.

    Returns:
        The loaded EpistemicGraph.

    Raises:
        FileNotFoundError: If the graph file does not exist.
    """
    filename = filename or config.DEFAULT_GRAPH_FILE
    filepath = config.GRAPHS_DIR / filename

    if not filepath.exists():
        raise FileNotFoundError(f"Graph file not found: {filepath}")

    eg = EpistemicGraph()
    eg.graph = nx.read_graphml(str(filepath))
    console.print(f"[bold green]✓ Graph loaded from {filepath}[/bold green]")
    return eg

"""Graph persistence — Save and load the epistemic graph to/from disk.

Handles GraphML serialization/deserialization with strict type fidelity.
NetworkX's GraphML writer only supports str/int/float/bool attributes,
so we sanitize on save and rehydrate types on load to prevent silent
type drift (e.g., confidence floats becoming strings after round-trip).
"""

import shutil
from pathlib import Path

import networkx as nx
from rich.console import Console

from uid_engine.graph.builder import EpistemicGraph

console = Console()

# ─── Attributes that must be rehydrated to their original types ──────────────
# GraphML deserializes everything as strings. These maps define the canonical
# types so that downstream code (gap_detector confidence thresholds, etc.)
# never operates on string comparisons by accident.

_FLOAT_ATTRS = {"confidence"}
_BOOL_ATTRS = {"reviewed", "has_abstract", "oral"}


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


def _deserialize_graph_types(graph: nx.DiGraph) -> None:
    """Rehydrate GraphML string attributes back to their canonical Python types.

    GraphML stores everything as strings. This function walks all node and edge
    attributes and casts known fields back to float/bool so downstream code
    (confidence thresholds, boolean filters) operates correctly.

    Operates in-place on the graph.
    """
    for _, data in graph.nodes(data=True):
        _rehydrate_attrs(data)

    for _, _, data in graph.edges(data=True):
        _rehydrate_attrs(data)


def _rehydrate_attrs(data: dict) -> None:
    """Cast known attributes from string back to their canonical types."""
    for attr in _FLOAT_ATTRS:
        if attr in data:
            try:
                data[attr] = float(data[attr])
            except (ValueError, TypeError):
                data[attr] = 0.0

    for attr in _BOOL_ATTRS:
        if attr in data:
            val = data[attr]
            if isinstance(val, str):
                data[attr] = val.lower() in ("true", "1", "yes")


def save_graph(graph: EpistemicGraph, filename: str | None = None) -> Path:
    """Save the epistemic graph to a GraphML file.

    Rotates the previous file to ``{filename}.bak`` before writing,
    so one backup copy is always available.

    Args:
        graph: The EpistemicGraph to save.
        filename: Optional filename. Defaults to config.DEFAULT_GRAPH_FILE.

    Returns:
        Path to the saved file.
    """
    from uid_engine import config  # deferred to avoid circular import at module level

    filename = filename or config.DEFAULT_GRAPH_FILE
    filepath = config.GRAPHS_DIR / filename

    # Rotate previous file to .bak
    if filepath.exists():
        backup_path = filepath.with_suffix(filepath.suffix + ".bak")
        shutil.copy2(str(filepath), str(backup_path))

    sanitized_graph = _sanitize_graph_for_graphml(graph.graph)
    nx.write_graphml(sanitized_graph, str(filepath))
    console.print(f"[bold green]✓ Graph saved to {filepath}[/bold green]")
    return filepath


def load_graph(filename: str | None = None) -> EpistemicGraph:
    """Load an epistemic graph from a GraphML file.

    Rehydrates all typed attributes (float confidence, bool flags) that
    GraphML silently converts to strings during serialization.

    Args:
        filename: Optional filename. Defaults to config.DEFAULT_GRAPH_FILE.

    Returns:
        The loaded EpistemicGraph with correct attribute types and counters.

    Raises:
        FileNotFoundError: If the graph file does not exist.
    """
    from uid_engine import config  # deferred to avoid circular import at module level

    filename = filename or config.DEFAULT_GRAPH_FILE
    filepath = config.GRAPHS_DIR / filename

    if not filepath.exists():
        raise FileNotFoundError(f"Graph file not found: {filepath}")

    eg = EpistemicGraph()
    eg.graph = nx.read_graphml(str(filepath))

    # Rehydrate types that GraphML flattened to strings
    _deserialize_graph_types(eg.graph)

    # Restore internal counters from the loaded graph state
    eg._node_count = eg.graph.number_of_nodes()
    eg._edge_count = eg.graph.number_of_edges()

    console.print(f"[bold green]✓ Graph loaded from {filepath}[/bold green]")
    return eg

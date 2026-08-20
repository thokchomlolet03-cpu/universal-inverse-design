"""CausalChainRegistry — Load, validate, and serve YAML-defined causal chains.

This module is the core architectural unlock of Phase F. It decouples the
biological logic (causal chain definitions) from the Python execution engine.

Any new research domain can be expressed as a YAML file and fed to the engine
without touching a single line of core Python. The engine becomes a compiler:
the YAML files are the source code it compiles into epistemic gap reports.

Usage:
    from uid_engine.chains.registry import CausalChainRegistry

    registry = CausalChainRegistry()
    chain = registry.load("glucosepane")    # Loads glucosepane.yaml
    chain = registry.load("senescent_cells") # Loads senescent_cells.yaml
    chain = registry.load_from_path("/path/to/custom.yaml")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any

from rich.console import Console

from uid_engine.analysis.causal_chains import CausalNode
from uid_engine.graph.schema import GapPriority

console = Console()

# Default directory for bundled chain YAML files
_CHAINS_DIR = Path(__file__).parent


@dataclass
class ChainNodeSpec:
    """Validated specification for a single causal chain node, parsed from YAML."""
    id: str
    description: str
    priority: GapPriority
    required_graph_entity: Optional[str] = None
    required_edge_type: Optional[str] = None
    required_status: str = "PROVEN"
    children: list["ChainNodeSpec"] = field(default_factory=list)


@dataclass
class ChainSpec:
    """Validated top-level chain specification, parsed from a YAML file."""
    name: str
    version: str
    target: str
    goal: str
    description: str
    root_node: ChainNodeSpec


class ChainValidationError(ValueError):
    """Raised when a YAML chain file fails structural validation."""
    pass


class CausalChainRegistry:
    """Loads and serves YAML-defined causal chains.

    The registry searches the bundled chains/ directory for YAML files
    matching a target name. Custom paths can also be loaded directly.

    All loaded chains are cached in memory to avoid repeated disk I/O
    during multi-target pipeline runs.
    """

    def __init__(self, chains_dir: Path | None = None):
        self._chains_dir = chains_dir or _CHAINS_DIR
        self._cache: dict[str, CausalNode] = {}

    # ─── Public API ──────────────────────────────────────────────────────────

    def load(self, target_name: str) -> CausalNode:
        """Load a causal chain by target name.

        Searches for ``{target_name}.yaml`` in the bundled chains directory.

        Args:
            target_name: Target identifier (e.g., "glucosepane", "senescent_cells").

        Returns:
            The root CausalNode of the loaded and validated chain.

        Raises:
            FileNotFoundError: If no YAML file exists for the target.
            ChainValidationError: If the YAML structure is invalid.
        """
        if target_name in self._cache:
            return self._cache[target_name]

        yaml_path = self._chains_dir / f"{target_name}.yaml"
        if not yaml_path.exists():
            available = self.list_available()
            raise FileNotFoundError(
                f"No chain found for target '{target_name}'. "
                f"Available chains: {available}. "
                f"Searched in: {self._chains_dir}"
            )

        chain = self.load_from_path(yaml_path)
        self._cache[target_name] = chain
        return chain

    def load_from_path(self, path: str | Path) -> CausalNode:
        """Load and validate a causal chain from an explicit file path.

        Args:
            path: Absolute or relative path to a chain YAML file.

        Returns:
            The root CausalNode of the loaded and validated chain.

        Raises:
            ChainValidationError: If the YAML structure is invalid.
        """
        import yaml  # deferred — pyyaml may not be installed in test env

        path = Path(path)
        console.print(f"[cyan]Loading chain from {path}[/cyan]")

        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        spec = self._validate_chain_spec(raw, path)
        root = self._build_node_tree(spec.root_node)
        console.print(f"[green]✓ Chain loaded: {spec.name} v{spec.version}[/green]")
        return root

    def list_available(self) -> list[str]:
        """List all available chain names in the chains directory."""
        return [p.stem for p in self._chains_dir.glob("*.yaml")]

    # ─── Validation ──────────────────────────────────────────────────────────

    def _validate_chain_spec(self, raw: Any, path: Path) -> ChainSpec:
        """Validate raw YAML dict against the ChainSpec schema.

        Fail fast with a descriptive message on any structural violation.
        This prevents malformed chains from silently producing wrong results.
        """
        if not isinstance(raw, dict):
            raise ChainValidationError(f"{path}: top-level must be a YAML mapping")

        required_keys = {"name", "version", "target", "goal", "nodes"}
        missing = required_keys - set(raw.keys())
        if missing:
            raise ChainValidationError(
                f"{path}: missing required keys: {sorted(missing)}"
            )

        nodes = raw.get("nodes", [])
        if not isinstance(nodes, list) or len(nodes) != 1:
            raise ChainValidationError(
                f"{path}: 'nodes' must be a list with exactly one root node, "
                f"got {len(nodes) if isinstance(nodes, list) else type(nodes).__name__}"
            )

        root_spec = self._parse_node_spec(nodes[0], path, depth=0)

        return ChainSpec(
            name=str(raw["name"]),
            version=str(raw["version"]),
            target=str(raw["target"]),
            goal=str(raw["goal"]),
            description=str(raw.get("description", "")),
            root_node=root_spec,
        )

    def _parse_node_spec(self, raw: Any, path: Path, depth: int) -> ChainNodeSpec:
        """Recursively parse and validate a node specification."""
        if not isinstance(raw, dict):
            raise ChainValidationError(
                f"{path} (depth {depth}): each node must be a YAML mapping"
            )

        node_id = raw.get("id")
        description = raw.get("description")

        if not node_id or not isinstance(node_id, str):
            raise ChainValidationError(
                f"{path} (depth {depth}): node missing required 'id' string field"
            )
        if not description or not isinstance(description, str):
            raise ChainValidationError(
                f"{path}: node '{node_id}' missing required 'description' field"
            )

        priority_raw = raw.get("priority", "CRITICAL")
        try:
            priority = GapPriority(priority_raw.upper())
        except ValueError:
            valid = [p.value for p in GapPriority]
            raise ChainValidationError(
                f"{path}: node '{node_id}' has invalid priority '{priority_raw}'. "
                f"Must be one of: {valid}"
            )

        children = []
        for child_raw in raw.get("children", []):
            children.append(self._parse_node_spec(child_raw, path, depth + 1))

        return ChainNodeSpec(
            id=str(node_id),
            description=str(description).strip(),
            priority=priority,
            required_graph_entity=raw.get("required_graph_entity"),
            required_edge_type=raw.get("required_edge_type"),
            required_status=str(raw.get("required_status", "PROVEN")),
            children=children,
        )

    # ─── Tree Builder ─────────────────────────────────────────────────────────

    def _build_node_tree(self, spec: ChainNodeSpec) -> CausalNode:
        """Recursively convert a validated ChainNodeSpec tree into a CausalNode tree."""
        node = CausalNode(
            node_id=spec.id,
            description=spec.description,
            required_graph_entity=spec.required_graph_entity,
            required_edge_type=spec.required_edge_type,
            required_status=spec.required_status,
            priority=spec.priority,
        )
        for child_spec in spec.children:
            node.children.append(self._build_node_tree(child_spec))
        return node

"""Tests for CausalChainRegistry — YAML loading and parity with Python chains.

The critical invariant: the YAML-loaded glucosepane chain must produce
EXACTLY the same 9 gaps as the Python-built chain. If this parity test
passes, the engine is truly domain-agnostic — the causal chain is data,
not code.
"""

import pytest
from pathlib import Path

from uid_engine.chains.registry import CausalChainRegistry, ChainValidationError
from uid_engine.analysis.causal_chains import build_glucosepane_repair_chain, flatten_chain
from uid_engine.analysis.gap_detector import NegativeSpaceDetector
from uid_engine.graph.schema import GapPriority


CHAINS_DIR = Path(__file__).parent.parent / "src" / "uid_engine" / "chains"


class TestChainRegistryLoad:
    """Basic registry loading and file resolution."""

    def test_load_glucosepane_by_name(self):
        registry = CausalChainRegistry(CHAINS_DIR)
        chain = registry.load("glucosepane")
        assert chain is not None
        assert chain.node_id == "goal:arterial_compliance"

    def test_load_unknown_target_raises_file_not_found(self):
        registry = CausalChainRegistry(CHAINS_DIR)
        with pytest.raises(FileNotFoundError, match="No chain found for target"):
            registry.load("does_not_exist")

    def test_list_available_includes_glucosepane(self):
        registry = CausalChainRegistry(CHAINS_DIR)
        available = registry.list_available()
        assert "glucosepane" in available

    def test_cache_returns_same_object(self):
        registry = CausalChainRegistry(CHAINS_DIR)
        chain1 = registry.load("glucosepane")
        chain2 = registry.load("glucosepane")
        assert chain1 is chain2  # exact same object from cache

    def test_load_from_path_explicit(self, tmp_path):
        """Test loading from an explicit path outside the registry dir."""
        import yaml
        chain_data = {
            "name": "Test Chain",
            "version": "0.1",
            "target": "test_target",
            "goal": "Test goal",
            "nodes": [{
                "id": "goal:test",
                "description": "A test goal node",
                "priority": "CRITICAL",
            }]
        }
        yaml_file = tmp_path / "test_chain.yaml"
        yaml_file.write_text(yaml.dump(chain_data))

        registry = CausalChainRegistry()
        chain = registry.load_from_path(yaml_file)
        assert chain.node_id == "goal:test"


class TestChainValidation:
    """Registry validation rejects malformed YAML chain files."""

    def _write_yaml(self, tmp_path, data):
        import yaml
        f = tmp_path / "chain.yaml"
        f.write_text(yaml.dump(data))
        return f

    def test_missing_required_key_raises(self, tmp_path):
        registry = CausalChainRegistry()
        f = self._write_yaml(tmp_path, {
            "name": "Bad Chain",
            # missing: version, target, goal, nodes
        })
        with pytest.raises(ChainValidationError, match="missing required keys"):
            registry.load_from_path(f)

    def test_multiple_root_nodes_raises(self, tmp_path):
        registry = CausalChainRegistry()
        f = self._write_yaml(tmp_path, {
            "name": "X", "version": "1", "target": "x", "goal": "x",
            "nodes": [
                {"id": "a", "description": "A", "priority": "HIGH"},
                {"id": "b", "description": "B", "priority": "HIGH"},
            ]
        })
        with pytest.raises(ChainValidationError, match="exactly one root node"):
            registry.load_from_path(f)

    def test_invalid_priority_raises(self, tmp_path):
        registry = CausalChainRegistry()
        f = self._write_yaml(tmp_path, {
            "name": "X", "version": "1", "target": "x", "goal": "x",
            "nodes": [{"id": "a", "description": "A", "priority": "ULTRA_CRITICAL"}]
        })
        with pytest.raises(ChainValidationError, match="invalid priority"):
            registry.load_from_path(f)

    def test_missing_description_raises(self, tmp_path):
        registry = CausalChainRegistry()
        f = self._write_yaml(tmp_path, {
            "name": "X", "version": "1", "target": "x", "goal": "x",
            "nodes": [{"id": "a", "priority": "HIGH"}]  # missing description
        })
        with pytest.raises(ChainValidationError, match="missing required 'description'"):
            registry.load_from_path(f)


class TestYamlChainParity:
    """THE parity test: YAML chain must produce identical gaps to Python chain.

    This is the proof that the engine is domain-agnostic. If this passes,
    the CausalChainRegistry is a correct compiler of biological domain logic.
    """

    def test_yaml_chain_produces_same_node_count(self):
        """YAML and Python chains must have identical node structures."""
        registry = CausalChainRegistry(CHAINS_DIR)
        yaml_chain = registry.load("glucosepane")
        python_chain = build_glucosepane_repair_chain()

        yaml_nodes = flatten_chain(yaml_chain)
        python_nodes = flatten_chain(python_chain)

        assert len(yaml_nodes) == len(python_nodes), (
            f"YAML chain has {len(yaml_nodes)} nodes, "
            f"Python chain has {len(python_nodes)} nodes — they must match."
        )

    def test_yaml_chain_node_ids_match(self):
        """Every node ID in the YAML chain must match the Python chain."""
        registry = CausalChainRegistry(CHAINS_DIR)
        yaml_chain = registry.load("glucosepane")
        python_chain = build_glucosepane_repair_chain()

        yaml_ids = {n.node_id for n in flatten_chain(yaml_chain)}
        python_ids = {n.node_id for n in flatten_chain(python_chain)}

        assert yaml_ids == python_ids, (
            f"Node ID mismatch.\n"
            f"Only in YAML: {yaml_ids - python_ids}\n"
            f"Only in Python: {python_ids - yaml_ids}"
        )

    def test_yaml_chain_priorities_match(self):
        """Every node's priority must match between YAML and Python."""
        registry = CausalChainRegistry(CHAINS_DIR)
        yaml_chain = registry.load("glucosepane")
        python_chain = build_glucosepane_repair_chain()

        yaml_map = {n.node_id: n.priority for n in flatten_chain(yaml_chain)}
        python_map = {n.node_id: n.priority for n in flatten_chain(python_chain)}

        mismatches = {
            nid: (yaml_map[nid], python_map[nid])
            for nid in yaml_map
            if nid in python_map and yaml_map[nid] != python_map[nid]
        }
        assert not mismatches, f"Priority mismatches: {mismatches}"

    def test_yaml_chain_produces_exactly_9_gaps(self, mock_graph):
        """THE proof: YAML chain → gap detector → exactly 9 gaps.

        This is the multi-layer regression guard:
        - Layer 1: Python chain produces 9 gaps (test_gap_detector.py)
        - Layer 2: YAML chain produces the same 9 gaps (this test)

        If both pass, the engine is a correct domain-agnostic compiler.
        """
        registry = CausalChainRegistry(CHAINS_DIR)
        yaml_chain = registry.load("glucosepane")

        detector = NegativeSpaceDetector(mock_graph)
        gaps = detector.detect_gaps(yaml_chain)

        assert len(gaps) == 9, (
            f"YAML-loaded chain produced {len(gaps)} gaps, expected 9. "
            "The CausalChainRegistry is not producing a correct chain."
        )

    def test_yaml_chain_has_same_critical_gap(self, mock_graph):
        """Gap #1 from YAML chain must be CRITICAL priority."""
        registry = CausalChainRegistry(CHAINS_DIR)
        yaml_chain = registry.load("glucosepane")
        detector = NegativeSpaceDetector(mock_graph)
        gaps = detector.detect_gaps(yaml_chain)

        assert gaps[0].priority == GapPriority.CRITICAL


class TestSenescentCellsChain:
    """Tests for the senescent_cells YAML chain (Wave 3 proof)."""

    def test_load_senescent_cells_chain(self):
        registry = CausalChainRegistry(CHAINS_DIR)
        chain = registry.load("senescent_cells")
        assert chain is not None
        assert chain.node_id == "goal:clear_senescent_cells"
        assert chain.priority == GapPriority.CRITICAL

    def test_senescent_cells_chain_structure(self):
        registry = CausalChainRegistry(CHAINS_DIR)
        chain = registry.load("senescent_cells")
        all_nodes = flatten_chain(chain)

        # 1 root + 3 level-1 reqs + 7 sub-reqs = 11 nodes total
        assert len(all_nodes) == 11

        node_ids = [n.node_id for n in all_nodes]
        assert "req:selective_senolysis" in node_ids
        assert "req:scap_inhibition" in node_ids
        assert "req:sasp_neutralization" in node_ids
        assert "req:tissue_regeneration" in node_ids

    def test_senescent_cells_gap_detection_on_empty_graph(self):
        """On an empty graph, all non-container leaf requirements and linked entities flag as gaps."""
        from uid_engine.graph.builder import EpistemicGraph
        empty_graph = EpistemicGraph()
        registry = CausalChainRegistry(CHAINS_DIR)
        chain = registry.load("senescent_cells")

        detector = NegativeSpaceDetector(empty_graph)
        gaps = detector.detect_gaps(chain)

        # 8 gaps: 1 CRITICAL, 3 HIGH, 4 MEDIUM
        assert len(gaps) == 8
        assert gaps[0].priority == GapPriority.CRITICAL
        assert gaps[0].causal_node_id == "req:selective_senolysis"



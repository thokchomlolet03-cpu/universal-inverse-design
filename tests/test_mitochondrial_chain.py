"""Tests for the mitochondrial_mutations YAML chain (MitoSENS)."""

from pathlib import Path
import pytest

from uid_engine.chains.registry import CausalChainRegistry
from uid_engine.analysis.causal_chains import flatten_chain
from uid_engine.analysis.gap_detector import NegativeSpaceDetector
from uid_engine.graph.builder import EpistemicGraph
from uid_engine.graph.schema import GapPriority


CHAINS_DIR = Path(__file__).parent.parent / "src" / "uid_engine" / "chains"


class TestMitochondrialChain:
    """Test loading and evaluating the MitoSENS causal chain."""

    def test_load_mitochondrial_chain(self):
        registry = CausalChainRegistry(CHAINS_DIR)
        chain = registry.load("mitochondrial_mutations")
        assert chain is not None
        assert chain.node_id == "goal:restore_mitochondrial_oxphos"
        assert chain.priority == GapPriority.CRITICAL

    def test_mitochondrial_chain_node_structure(self):
        registry = CausalChainRegistry(CHAINS_DIR)
        chain = registry.load("mitochondrial_mutations")
        all_nodes = flatten_chain(chain)

        # 1 root + 3 level-1 reqs + 7 sub-reqs = 11 nodes
        assert len(all_nodes) == 11

        node_ids = [n.node_id for n in all_nodes]
        assert "req:allotopic_expression" in node_ids
        assert "req:nuclear_codon_optimization" in node_ids
        assert "req:hydrophobic_mts_engineering" in node_ids
        assert "req:tom_tim_translocation" in node_ids
        assert "req:heteroplasmy_shift" in node_ids
        assert "req:mitotargeted_nucleases" in node_ids

    def test_mitochondrial_gap_detection_on_empty_graph(self):
        empty_graph = EpistemicGraph()
        registry = CausalChainRegistry(CHAINS_DIR)
        chain = registry.load("mitochondrial_mutations")

        detector = NegativeSpaceDetector(empty_graph)
        gaps = detector.detect_gaps(chain)

        # 8 gaps detected (1 CRITICAL, 4 HIGH, 3 MEDIUM)
        assert len(gaps) == 8
        assert gaps[0].priority == GapPriority.CRITICAL
        assert gaps[0].causal_node_id == "req:allotopic_expression"

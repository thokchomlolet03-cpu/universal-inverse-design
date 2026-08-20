"""Tests for graph serialization — the CRITICAL save/load type fidelity test.

This test catches the GraphML type-casting bug: NetworkX silently converts
float attributes to strings during serialization. If _deserialize_graph_types()
is broken, confidence thresholds in gap_detector will silently malfunction.
"""

import pytest
from pathlib import Path

import networkx as nx

from uid_engine.graph.store import save_graph, load_graph, _deserialize_graph_types
from uid_engine.graph.builder import EpistemicGraph
from uid_engine.graph.schema import NodeData, NodeType, EdgeData, EdgeType, EvidenceStatus
from uid_engine import config


class TestSaveLoadRoundTrip:
    """The core regression test: types survive a save → load cycle."""

    def test_float_confidence_survives_round_trip(self, minimal_graph, tmp_path):
        """Confidence values must remain float after save/load, not become strings."""
        config.GRAPHS_DIR = tmp_path
        filename = "test_round_trip.graphml"

        save_graph(minimal_graph, filename)
        loaded = load_graph(filename)

        mol_data = loaded.get_node("mol:test_mol")
        assert isinstance(mol_data["confidence"], float), (
            f"Expected float, got {type(mol_data['confidence'])}: {mol_data['confidence']}"
        )
        assert mol_data["confidence"] == pytest.approx(0.75)

    def test_edge_confidence_survives_round_trip(self, minimal_graph, tmp_path):
        """Edge confidence must also survive as float."""
        config.GRAPHS_DIR = tmp_path
        filename = "test_edge_conf.graphml"

        save_graph(minimal_graph, filename)
        loaded = load_graph(filename)

        edge_data = loaded.graph.edges["mol:test_mol", "protein:test_prot"]
        assert isinstance(edge_data["confidence"], float)
        assert edge_data["confidence"] == pytest.approx(0.8)

    def test_bool_reviewed_survives_round_trip(self, minimal_graph, tmp_path):
        """Boolean 'reviewed' attribute must be rehydrated from string."""
        config.GRAPHS_DIR = tmp_path
        filename = "test_bool.graphml"

        save_graph(minimal_graph, filename)
        loaded = load_graph(filename)

        prot_data = loaded.get_node("protein:test_prot")
        assert isinstance(prot_data["reviewed"], bool), (
            f"Expected bool, got {type(prot_data['reviewed'])}: {prot_data['reviewed']}"
        )
        assert prot_data["reviewed"] is True

    def test_node_count_restored_after_load(self, minimal_graph, tmp_path):
        """Internal counters must match graph state after load."""
        config.GRAPHS_DIR = tmp_path
        filename = "test_counters.graphml"

        save_graph(minimal_graph, filename)
        loaded = load_graph(filename)

        assert loaded._node_count == loaded.graph.number_of_nodes()
        assert loaded._edge_count == loaded.graph.number_of_edges()

    def test_all_nodes_preserved(self, mock_graph, tmp_path):
        """The full mock graph must have the same node count after round-trip."""
        config.GRAPHS_DIR = tmp_path
        filename = "test_full_mock.graphml"

        original_count = mock_graph.graph.number_of_nodes()
        save_graph(mock_graph, filename)
        loaded = load_graph(filename)

        assert loaded.graph.number_of_nodes() == original_count

    def test_all_edges_preserved(self, mock_graph, tmp_path):
        """The full mock graph must have the same edge count after round-trip."""
        config.GRAPHS_DIR = tmp_path
        filename = "test_full_edges.graphml"

        original_count = mock_graph.graph.number_of_edges()
        save_graph(mock_graph, filename)
        loaded = load_graph(filename)

        assert loaded.graph.number_of_edges() == original_count


class TestBackupRotation:
    """Verify .bak file is created when overwriting an existing graph."""

    def test_bak_created_on_overwrite(self, minimal_graph, tmp_path):
        config.GRAPHS_DIR = tmp_path
        filename = "test_backup.graphml"

        # First save — no .bak yet
        save_graph(minimal_graph, filename)
        bak_path = (tmp_path / filename).with_suffix(".graphml.bak")
        assert not bak_path.exists()

        # Second save — .bak should now exist
        save_graph(minimal_graph, filename)
        assert bak_path.exists()


class TestDeserializeGraphTypes:
    """Unit tests for the _deserialize_graph_types helper."""

    def test_string_float_rehydrated(self):
        g = nx.DiGraph()
        g.add_node("a", confidence="0.42")
        _deserialize_graph_types(g)
        assert g.nodes["a"]["confidence"] == pytest.approx(0.42)
        assert isinstance(g.nodes["a"]["confidence"], float)

    def test_string_bool_rehydrated(self):
        g = nx.DiGraph()
        g.add_node("a", reviewed="True")
        _deserialize_graph_types(g)
        assert g.nodes["a"]["reviewed"] is True

    def test_string_false_rehydrated(self):
        g = nx.DiGraph()
        g.add_node("a", reviewed="false")
        _deserialize_graph_types(g)
        assert g.nodes["a"]["reviewed"] is False

    def test_invalid_float_defaults_to_zero(self):
        g = nx.DiGraph()
        g.add_node("a", confidence="not_a_number")
        _deserialize_graph_types(g)
        assert g.nodes["a"]["confidence"] == 0.0

    def test_edge_attrs_also_rehydrated(self):
        g = nx.DiGraph()
        g.add_node("a")
        g.add_node("b")
        g.add_edge("a", "b", confidence="0.95")
        _deserialize_graph_types(g)
        assert g.edges["a", "b"]["confidence"] == pytest.approx(0.95)


class TestLoadGraphErrors:
    """Test error handling for missing graph files."""

    def test_load_nonexistent_raises_file_not_found(self, tmp_path):
        config.GRAPHS_DIR = tmp_path
        with pytest.raises(FileNotFoundError):
            load_graph("does_not_exist.graphml")

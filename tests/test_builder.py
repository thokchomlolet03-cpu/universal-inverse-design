"""Tests for graph builder — mock graph construction and counter accuracy."""

import pytest

from uid_engine.graph.builder import EpistemicGraph, build_mock_glucosepane_graph
from uid_engine.graph.schema import NodeData, NodeType, EdgeData, EdgeType, EvidenceStatus


class TestMockGraph:
    """Validate the hand-coded mock glucosepane graph."""

    def test_mock_graph_node_count(self, mock_graph):
        assert mock_graph.graph.number_of_nodes() == 19

    def test_mock_graph_edge_count(self, mock_graph):
        assert mock_graph.graph.number_of_edges() == 18

    def test_mock_graph_has_5_unknowns(self, mock_graph):
        unknowns = mock_graph.get_nodes_by_type(NodeType.UNKNOWN)
        assert len(unknowns) == 5

    def test_mock_graph_has_glucosepane(self, mock_graph):
        assert mock_graph.has_node("mol:glucosepane")
        data = mock_graph.get_node("mol:glucosepane")
        assert data["node_type"] == "MOLECULE"

    def test_mock_graph_has_failed_edge(self, mock_graph):
        """FN3K → glucosepane must have FAILED status."""
        edge = mock_graph.graph.edges["protein:fructosamine_3_kinase", "mol:glucosepane"]
        assert edge["status"] == "FAILED"


class TestEpistemicGraphOperations:
    """Test the EpistemicGraph wrapper methods."""

    def test_add_node_increments_counter(self):
        g = EpistemicGraph()
        g.add_node(NodeData(node_id="a", node_type=NodeType.MOLECULE, name="A"))
        assert g._node_count == 1

    def test_duplicate_add_node_does_not_increment(self):
        """Counter must NOT drift when re-adding the same node."""
        g = EpistemicGraph()
        g.add_node(NodeData(node_id="a", node_type=NodeType.MOLECULE, name="A"))
        g.add_node(NodeData(node_id="a", node_type=NodeType.MOLECULE, name="A v2"))
        assert g._node_count == 1
        assert g.graph.number_of_nodes() == 1

    def test_add_edge_to_missing_node_raises(self):
        g = EpistemicGraph()
        g.add_node(NodeData(node_id="a", node_type=NodeType.MOLECULE, name="A"))
        with pytest.raises(ValueError, match="not in graph"):
            g.add_edge("a", "b", EdgeData(edge_type=EdgeType.ACTIVATES))

    def test_get_nodes_by_type(self):
        g = EpistemicGraph()
        g.add_node(NodeData(node_id="m1", node_type=NodeType.MOLECULE, name="M1"))
        g.add_node(NodeData(node_id="p1", node_type=NodeType.PROTEIN, name="P1"))
        g.add_node(NodeData(node_id="m2", node_type=NodeType.MOLECULE, name="M2"))
        molecules = g.get_nodes_by_type(NodeType.MOLECULE)
        assert set(molecules) == {"m1", "m2"}

    def test_successors_and_predecessors(self):
        g = EpistemicGraph()
        g.add_node(NodeData(node_id="a", node_type=NodeType.MOLECULE, name="A"))
        g.add_node(NodeData(node_id="b", node_type=NodeType.PROTEIN, name="B"))
        g.add_edge("a", "b", EdgeData(edge_type=EdgeType.INHIBITS))

        successors = g.get_successors("a")
        assert len(successors) == 1
        assert successors[0][0] == "b"

        predecessors = g.get_predecessors("b")
        assert len(predecessors) == 1
        assert predecessors[0][0] == "a"

    def test_stats_returns_correct_structure(self, mock_graph):
        s = mock_graph.stats()
        assert "total_nodes" in s
        assert "total_edges" in s
        assert "node_types" in s
        assert "edge_types" in s
        assert "unknowns" in s
        assert s["unknowns"] == 5

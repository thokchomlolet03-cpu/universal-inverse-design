"""Tests for graph schema — enum round-trip and data class validation."""

import pytest

from uid_engine.graph.schema import (
    NodeType, EdgeType, EvidenceStatus, GapPriority,
    NodeData, EdgeData,
)


class TestEnumRoundTrips:
    """Every enum value must survive value → Enum → value conversion."""

    @pytest.mark.parametrize("member", NodeType)
    def test_node_type_round_trip(self, member):
        assert NodeType(member.value) == member

    @pytest.mark.parametrize("member", EdgeType)
    def test_edge_type_round_trip(self, member):
        assert EdgeType(member.value) == member

    @pytest.mark.parametrize("member", EvidenceStatus)
    def test_evidence_status_round_trip(self, member):
        assert EvidenceStatus(member.value) == member

    @pytest.mark.parametrize("member", GapPriority)
    def test_gap_priority_round_trip(self, member):
        assert GapPriority(member.value) == member


class TestNodeData:
    """Validate NodeData serialization."""

    def test_to_dict_includes_type_as_string(self):
        nd = NodeData(
            node_id="mol:test",
            node_type=NodeType.MOLECULE,
            name="Test",
        )
        d = nd.to_dict()
        assert d["node_type"] == "MOLECULE"
        assert d["name"] == "Test"
        assert d["confidence"] == 1.0

    def test_to_dict_flattens_metadata(self):
        nd = NodeData(
            node_id="p:test",
            node_type=NodeType.PROTEIN,
            name="Enzyme",
            metadata={"organism": "E. coli", "ec_number": "3.5.1.1"},
        )
        d = nd.to_dict()
        assert d["organism"] == "E. coli"
        assert d["ec_number"] == "3.5.1.1"


class TestEdgeData:
    """Validate EdgeData serialization."""

    def test_to_dict_includes_status_as_string(self):
        ed = EdgeData(
            edge_type=EdgeType.CATALYZES,
            status=EvidenceStatus.HYPOTHESIZED,
            confidence=0.5,
            source="PMID:12345",
            context="enzyme showed weak activity",
        )
        d = ed.to_dict()
        assert d["edge_type"] == "CATALYZES"
        assert d["status"] == "HYPOTHESIZED"
        assert d["confidence"] == 0.5

    def test_default_status_is_proven(self):
        ed = EdgeData(edge_type=EdgeType.ACTIVATES)
        assert ed.status == EvidenceStatus.PROVEN


class TestEnumCounts:
    """Ensure we don't accidentally add/remove enum members without updating tests."""

    def test_node_type_count(self):
        assert len(NodeType) == 9

    def test_edge_type_count(self):
        assert len(EdgeType) == 11

    def test_evidence_status_count(self):
        assert len(EvidenceStatus) == 4

    def test_gap_priority_count(self):
        assert len(GapPriority) == 4

"""Tests for NegativeSpaceDetector — the core 'Negative Space' regression guard.

The critical invariant: the mock glucosepane graph must always produce exactly
9 epistemic gaps. If this test ever breaks, the core logic has regressed.
"""

import pytest

from uid_engine.graph.builder import build_mock_glucosepane_graph, EpistemicGraph
from uid_engine.graph.schema import (
    NodeData, NodeType, EdgeData, EdgeType, EvidenceStatus, GapPriority
)
from uid_engine.analysis.causal_chains import build_glucosepane_repair_chain
from uid_engine.analysis.gap_detector import NegativeSpaceDetector, EpistemicGap


class TestNegativeSpaceRegression:
    """THE core regression guard — exactly 9 gaps from the mock graph."""

    def test_mock_graph_produces_exactly_9_gaps(self, mock_graph):
        """This is the immutable regression guard.

        If this test ever breaks during a refactor, the core Negative Space
        logic has been damaged — even if all other tests still pass.
        """
        chain = build_glucosepane_repair_chain()
        detector = NegativeSpaceDetector(mock_graph)
        gaps = detector.detect_gaps(chain)
        assert len(gaps) == 9, (
            f"Expected 9 gaps, got {len(gaps)}. "
            "Core Negative Space logic has regressed."
        )

    def test_first_gap_is_critical(self, mock_graph):
        """The CRITICAL selective enzyme gap must always be gap #1."""
        chain = build_glucosepane_repair_chain()
        detector = NegativeSpaceDetector(mock_graph)
        gaps = detector.detect_gaps(chain)
        assert gaps[0].priority == GapPriority.CRITICAL

    def test_gaps_sorted_by_severity(self, mock_graph):
        """Gaps must be returned in descending severity order."""
        chain = build_glucosepane_repair_chain()
        detector = NegativeSpaceDetector(mock_graph)
        gaps = detector.detect_gaps(chain)
        scores = [g.severity_score() for g in gaps]
        assert scores == sorted(scores, reverse=True)

    def test_gap_counts_by_priority(self, mock_graph):
        """Exact counts by priority level (1 CRITICAL, 5 HIGH, 3 MEDIUM)."""
        chain = build_glucosepane_repair_chain()
        detector = NegativeSpaceDetector(mock_graph)
        gaps = detector.detect_gaps(chain)

        priority_counts = {}
        for g in gaps:
            p = g.priority.value
            priority_counts[p] = priority_counts.get(p, 0) + 1

        assert priority_counts.get("CRITICAL", 0) == 1
        assert priority_counts.get("HIGH", 0) == 5
        assert priority_counts.get("MEDIUM", 0) == 3
        assert priority_counts.get("LOW", 0) == 0


class TestEdgeTypeIndex:
    """Verify the O(1) edge-type index is correctly built and used."""

    def test_index_populated_on_init(self, mock_graph):
        detector = NegativeSpaceDetector(mock_graph)
        assert len(detector._edge_type_index) > 0

    def test_index_contains_degrades(self, mock_graph):
        """DEGRADES edges exist in mock graph and must be indexed."""
        detector = NegativeSpaceDetector(mock_graph)
        assert "DEGRADES" in detector._edge_type_index

    def test_index_entry_count_matches_graph(self, mock_graph):
        """Total entries across all index buckets == graph edge count."""
        detector = NegativeSpaceDetector(mock_graph)
        total = sum(len(v) for v in detector._edge_type_index.values())
        assert total == mock_graph.graph.number_of_edges()

    def test_hypothesized_candidates_found_via_index(self, mock_graph):
        """The bacterial enzyme candidate (HYPOTHESIZED DEGRADES) must be
        surfaced as a candidate for the selective enzyme gap."""
        chain = build_glucosepane_repair_chain()
        detector = NegativeSpaceDetector(mock_graph)
        gaps = detector.detect_gaps(chain)

        # Gap #1 is the selective enzyme gap
        gap1 = gaps[0]
        candidate_ids = [c["entity_id"] for c in gap1.closest_candidates]
        # The bacterial candidate has a HYPOTHESIZED DEGRADES edge
        assert "protein:bacterial_class_i_enzyme" in candidate_ids


class TestGapClassification:
    """Verify gap type classification logic."""

    def test_unknown_node_classified_as_missing_mechanism(self, mock_graph):
        chain = build_glucosepane_repair_chain()
        detector = NegativeSpaceDetector(mock_graph)
        gaps = detector.detect_gaps(chain)

        # Gap #1 must be MISSING_MECHANISM (points to UNKNOWN node)
        assert gaps[0].gap_type == "MISSING_MECHANISM"

    def test_severity_score_values(self):
        """Test EpistemicGap severity scoring."""
        gap = EpistemicGap(
            gap_id="test",
            description="test",
            priority=GapPriority.CRITICAL,
            causal_node_id="test",
            gap_type="MISSING_MECHANISM",
            closest_candidates=[],
            downstream_impact=[],
            source_evidence=[],
            suggested_directions=[],
        )
        assert gap.severity_score() == 4

        gap.priority = GapPriority.HIGH
        assert gap.severity_score() == 3

        gap.priority = GapPriority.MEDIUM
        assert gap.severity_score() == 2

        gap.priority = GapPriority.LOW
        assert gap.severity_score() == 1

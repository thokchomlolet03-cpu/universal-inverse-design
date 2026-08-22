"""Unit tests for pathway redundancy and betweenness centrality analysis."""

import pytest
from uid_engine.graph.builder import build_mock_glucosepane_graph
from uid_engine.analysis.gap_detector import NegativeSpaceDetector
from uid_engine.analysis.causal_chains import build_glucosepane_repair_chain
from uid_engine.analysis.pathway_analyzer import (
    compute_pathway_centrality_for_gap,
    PathwayCentralityScore,
)


def test_pathway_centrality_calculation():
    """Epistemic gap should produce non-negative betweenness centrality and redundancy index."""
    graph = build_mock_glucosepane_graph()
    chain = build_glucosepane_repair_chain()
    detector = NegativeSpaceDetector(graph)
    gaps = detector.detect_gaps(chain)
    assert len(gaps) > 0

    gap0 = gaps[0]
    score = compute_pathway_centrality_for_gap(graph, gap0, target_node_id="mol:glucosepane")

    assert isinstance(score, PathwayCentralityScore)
    assert score.gap_id == gap0.gap_id
    assert score.betweenness_centrality >= 0.0
    assert 0.0 <= score.redundancy_index <= 1.0
    assert score.criticality_tier in [
        "BOTTLENECK_VULNERABILITY",
        "MODERATE_BUFFERING",
        "HIGH_REDUNDANCY_RISK",
    ]
    d = score.to_dict()
    assert "betweenness_centrality" in d
    assert "redundancy_index" in d

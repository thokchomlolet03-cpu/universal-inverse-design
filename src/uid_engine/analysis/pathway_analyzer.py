"""Pathway Redundancy & Network Centrality Analyzer.

Translates biological network topology into computable mathematical risk scores:
- Computes NetworkX betweenness centrality for epistemic gap nodes.
- Discovers alternative parallel regulatory/metabolic pathways to target damage nodes.
- Evaluates Redundancy Index: R = 1.0 - (1.0 / N_paths) to distinguish isolated
  critical-path vulnerabilities from highly buffered redundant networks.
"""

from dataclasses import dataclass
from typing import Optional
import networkx as nx

from uid_engine.graph.builder import EpistemicGraph
from uid_engine.analysis.gap_detector import EpistemicGap


@dataclass
class PathwayCentralityScore:
    """Quantitative network topology metrics for an identified epistemic gap."""

    gap_id: str
    target_node_id: str
    betweenness_centrality: float
    num_parallel_paths: int
    redundancy_index: float  # 0.0 = Single critical path (no bypass); 1.0 = highly buffered
    criticality_tier: str    # "BOTTLENECK_VULNERABILITY" | "MODERATE_BUFFERING" | "HIGH_REDUNDANCY_RISK"

    def to_dict(self) -> dict:
        return {
            "gap_id": self.gap_id,
            "target_node_id": self.target_node_id,
            "betweenness_centrality": round(self.betweenness_centrality, 4),
            "num_parallel_paths": self.num_parallel_paths,
            "redundancy_index": round(self.redundancy_index, 3),
            "criticality_tier": self.criticality_tier,
        }


def compute_pathway_centrality_for_gap(
    graph: EpistemicGraph,
    gap: EpistemicGap,
    target_node_id: Optional[str] = "mol:glucosepane",
) -> PathwayCentralityScore:
    """Calculate betweenness centrality and pathway redundancy for an epistemic gap.

    Args:
        graph: The EpistemicGraph instance.
        gap: The identified EpistemicGap.
        target_node_id: Downstream target entity (e.g. 'mol:glucosepane').

    Returns:
        PathwayCentralityScore instance.
    """
    g = graph.graph

    # 1. Global betweenness centrality
    betweenness = nx.betweenness_centrality(g, normalized=True)
    causal_id = gap.causal_node_id

    # If causal_id is a node in graph, lookup centrality, else fallback to average neighbor or default
    node_centrality = betweenness.get(causal_id, 0.0)
    if node_centrality == 0.0 and g.nodes():
        # Check closest candidate nodes
        if gap.closest_candidates:
            candidate_scores = [
                betweenness.get(c.get("entity_id", ""), 0.0)
                for c in gap.closest_candidates
            ]
            node_centrality = max(candidate_scores) if candidate_scores else 0.0

    # 2. Parallel pathway search
    num_paths = 1
    if target_node_id and g.has_node(target_node_id):
        # Count incoming paths from upstream components
        in_degree = g.in_degree(target_node_id)
        num_paths = max(1, in_degree)

    # 3. Redundancy Index: R = 1 - 1/N
    redundancy_index = 1.0 - (1.0 / num_paths)

    # 4. Criticality Tier
    if redundancy_index == 0.0:
        criticality_tier = "BOTTLENECK_VULNERABILITY"
    elif redundancy_index < 0.6:
        criticality_tier = "MODERATE_BUFFERING"
    else:
        criticality_tier = "HIGH_REDUNDANCY_RISK"

    return PathwayCentralityScore(
        gap_id=gap.gap_id,
        target_node_id=target_node_id or "",
        betweenness_centrality=node_centrality,
        num_parallel_paths=num_paths,
        redundancy_index=redundancy_index,
        criticality_tier=criticality_tier,
    )

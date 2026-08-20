"""Negative Space Detector — The core innovation of the Inverse Design Engine.

This module traverses the causal chain and checks each requirement against
the knowledge graph. When a required entity is missing, unproven, or failed,
it is flagged as an Epistemic Gap (Negative Space).

The output is a structured list of gaps, ranked by priority and impact,
representing EXACTLY what humanity still needs to discover to achieve
the target repair goal.
"""

from dataclasses import dataclass
from typing import Optional

from rich.console import Console

from uid_engine.graph.builder import EpistemicGraph
from uid_engine.graph.schema import (
    EdgeType,
    EvidenceStatus,
    GapPriority,
    NodeType,
)
from uid_engine.analysis.causal_chains import CausalNode, flatten_chain

console = Console()


@dataclass
class EpistemicGap:
    """A single identified gap in human scientific knowledge.

    This represents something that MUST be solved for the repair goal
    to be achieved, but for which no validated solution currently exists.
    """

    gap_id: str                             # Unique identifier
    description: str                        # What is missing
    priority: GapPriority                   # How critical is this gap
    causal_node_id: str                     # Which causal chain node flagged this
    gap_type: str                           # "MISSING_MECHANISM", "UNPROVEN_HYPOTHESIS", "CROSS_DOMAIN_BLIND_SPOT"
    closest_candidates: list[dict]          # What IS known that's closest to solving this
    downstream_impact: list[str]            # What other goals are blocked by this gap
    source_evidence: list[str]              # Papers/sources that define the boundary of knowledge
    suggested_directions: list[str]         # Potential research approaches

    def severity_score(self) -> int:
        """Numerical severity: CRITICAL=4, HIGH=3, MEDIUM=2, LOW=1."""
        return {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}[self.priority.value]


class NegativeSpaceDetector:
    """Detects epistemic gaps by checking causal chains against the knowledge graph.

    The detector operates in 3 phases:
    1. Chain Traversal: Walk the causal chain tree depth-first.
    2. Graph Matching: For each causal node, check if the knowledge graph
       contains a matching entity with PROVEN status.
    3. Gap Classification: If no match is found, classify the gap type
       and find the closest existing candidates.
    """

    def __init__(self, graph: EpistemicGraph):
        self.graph = graph
        self.gaps: list[EpistemicGap] = []

        # Pre-compute edge-type index for O(1) candidate lookups.
        # Without this, _find_closest_candidates() does a full N×E scan
        # per gap — acceptable at 327 nodes, catastrophic at 10K+.
        self._edge_type_index: dict[str, list[tuple[str, str, dict]]] = {}
        self._build_edge_index()

    def _build_edge_index(self) -> None:
        """Build a lookup table: edge_type → list of (source, target, edge_data)."""
        self._edge_type_index.clear()
        for u, v, data in self.graph.graph.edges(data=True):
            etype = data.get("edge_type", "")
            if etype not in self._edge_type_index:
                self._edge_type_index[etype] = []
            self._edge_type_index[etype].append((u, v, data))

    def detect_gaps(self, causal_root: CausalNode) -> list[EpistemicGap]:
        """Run the full negative space detection pipeline.

        Args:
            causal_root: Root node of the target causal chain.

        Returns:
            List of EpistemicGap objects, sorted by severity.
        """
        self.gaps = []
        all_nodes = flatten_chain(causal_root)

        console.print(f"\n[bold cyan]Scanning {len(all_nodes)} causal requirements...[/bold cyan]")

        for causal_node in all_nodes:
            gap = self._check_node(causal_node)
            if gap is not None:
                self.gaps.append(gap)

        # Sort by severity (CRITICAL first)
        self.gaps.sort(key=lambda g: g.severity_score(), reverse=True)

        console.print(
            f"[bold {'red' if self.gaps else 'green'}]"
            f"Found {len(self.gaps)} epistemic gaps[/bold {'red' if self.gaps else 'green'}]"
        )

        return self.gaps

    def _check_node(self, causal_node: CausalNode) -> Optional[EpistemicGap]:
        """Check a single causal node against the knowledge graph.

        Returns an EpistemicGap if the requirement is not met, None otherwise.
        """
        # If no specific graph entity is expected, check if ANY entity
        # in the graph could satisfy this requirement
        if causal_node.required_graph_entity:
            return self._check_specific_entity(causal_node)
        else:
            return self._check_general_requirement(causal_node)

    def _check_specific_entity(self, causal_node: CausalNode) -> Optional[EpistemicGap]:
        """Check if a specific expected entity exists and is validated."""
        entity_id = causal_node.required_graph_entity

        # Case 1: Entity doesn't exist in graph at all
        if not self.graph.has_node(entity_id):
            return self._create_gap(
                causal_node,
                gap_type="MISSING_MECHANISM",
                reason=f"Entity '{entity_id}' not found in knowledge graph",
            )

        node_data = self.graph.get_node(entity_id)

        # Case 2: Entity exists but IS an UNKNOWN node (explicit negative space)
        if node_data.get("node_type") == NodeType.UNKNOWN.value:
            return self._create_gap(
                causal_node,
                gap_type="MISSING_MECHANISM",
                reason=f"Entity '{entity_id}' is explicitly marked as UNKNOWN",
            )

        # Case 3: Entity exists — check if it has PROVEN edges of the required type
        if causal_node.required_edge_type:
            has_proven = self._has_proven_edge(
                entity_id,
                causal_node.required_edge_type,
                causal_node.required_status,
            )
            if not has_proven:
                return self._create_gap(
                    causal_node,
                    gap_type="UNPROVEN_HYPOTHESIS",
                    reason=(
                        f"Entity '{entity_id}' exists but has no PROVEN "
                        f"{causal_node.required_edge_type} relationship"
                    ),
                )

        # Case 4: Check if entity's own status is PROVEN
        if causal_node.required_status == "PROVEN":
            confidence = float(node_data.get("confidence", 1.0))
            if confidence < 0.6:
                return self._create_gap(
                    causal_node,
                    gap_type="UNPROVEN_HYPOTHESIS",
                    reason=f"Entity '{entity_id}' has low confidence ({confidence:.1f})",
                )

        return None  # Requirement is met

    def _check_general_requirement(self, causal_node: CausalNode) -> Optional[EpistemicGap]:
        """Check if any entity in the graph could satisfy an unlinked requirement.

        For causal nodes without a specific expected entity, we search the
        graph for any node that could plausibly satisfy the requirement.
        If nothing is found, it's a gap.
        """
        # For the MVP, general requirements without graph links are flagged
        # as gaps if they have no children (leaf nodes) — meaning nothing
        # in the system addresses them
        if not causal_node.children:
            return self._create_gap(
                causal_node,
                gap_type="MISSING_MECHANISM",
                reason="No known mechanism or entity addresses this requirement",
            )
        return None

    def _has_proven_edge(
        self, entity_id: str, edge_type: str, required_status: str
    ) -> bool:
        """Check if an entity has at least one edge of the given type with PROVEN status."""
        for target, edge_data in self.graph.get_successors(entity_id):
            if (
                edge_data.get("edge_type") == edge_type
                and edge_data.get("status") == required_status
            ):
                return True

        for source, edge_data in self.graph.get_predecessors(entity_id):
            if (
                edge_data.get("edge_type") == edge_type
                and edge_data.get("status") == required_status
            ):
                return True

        return False

    def _create_gap(
        self, causal_node: CausalNode, gap_type: str, reason: str
    ) -> EpistemicGap:
        """Create an EpistemicGap from a failed causal node check."""

        # Find closest candidates in the graph
        candidates = self._find_closest_candidates(causal_node)

        # Determine downstream impact
        downstream = self._get_downstream_impact(causal_node)

        return EpistemicGap(
            gap_id=f"gap:{causal_node.node_id}",
            description=causal_node.description,
            priority=causal_node.priority,
            causal_node_id=causal_node.node_id,
            gap_type=gap_type,
            closest_candidates=candidates,
            downstream_impact=downstream,
            source_evidence=[reason],
            suggested_directions=self._suggest_directions(causal_node, gap_type),
        )

    def _find_closest_candidates(self, causal_node: CausalNode) -> list[dict]:
        """Find entities in the graph that are closest to satisfying this requirement.

        Uses the pre-computed edge-type index for O(1) lookup instead of
        scanning all N nodes × all E edges per gap call.
        """
        candidates = []

        if causal_node.required_graph_entity:
            entity_id = causal_node.required_graph_entity
            if self.graph.has_node(entity_id):
                node_data = self.graph.get_node(entity_id)
                candidates.append({
                    "entity_id": entity_id,
                    "name": node_data.get("name", ""),
                    "description": node_data.get("description", ""),
                    "confidence": node_data.get("confidence", 0),
                    "source": node_data.get("source", ""),
                })

        # O(1) lookup via pre-computed index instead of O(N×E) full scan
        if causal_node.required_edge_type:
            hypothesized_edges = self._edge_type_index.get(
                causal_node.required_edge_type, []
            )
            for source_id, target_id, edge_data in hypothesized_edges:
                if edge_data.get("status") == EvidenceStatus.HYPOTHESIZED.value:
                    node_data = self.graph.get_node(source_id)
                    candidates.append({
                        "entity_id": source_id,
                        "name": node_data.get("name", ""),
                        "status": "HYPOTHESIZED (not yet proven)",
                        "confidence": edge_data.get("confidence", 0),
                        "source": edge_data.get("source", ""),
                        "context": edge_data.get("context", ""),
                    })

        return candidates

    def _get_downstream_impact(self, causal_node: CausalNode) -> list[str]:
        """Determine what downstream goals are blocked by this gap."""
        # Walk up the causal chain to find parent goals
        # For MVP, return the node's own children as impacted
        return [child.description for child in causal_node.children]

    def _suggest_directions(self, causal_node: CausalNode, gap_type: str) -> list[str]:
        """Suggest potential research directions to fill this gap."""
        suggestions = []

        if gap_type == "MISSING_MECHANISM":
            suggestions.append(
                "Search for homologous enzymes in extremophile organisms "
                "(soil bacteria, deep-sea archaea) via metagenomic screening"
            )
            suggestions.append(
                "Use computational protein design (RFdiffusion, AlphaFold) "
                "to engineer a de novo enzyme for this specific substrate"
            )
        elif gap_type == "UNPROVEN_HYPOTHESIS":
            suggestions.append(
                "Design targeted in vitro assay to validate the hypothesized mechanism"
            )
            suggestions.append(
                "Search for independent replication studies in PubMed"
            )

        if "delivery" in causal_node.description.lower():
            suggestions.append(
                "Investigate lipid nanoparticle formulations optimized for "
                "extracellular matrix penetration"
            )
            suggestions.append(
                "Explore direct intravascular catheter-based delivery to bypass systemic distribution"
            )

        if "toxicity" in causal_node.description.lower():
            suggestions.append(
                "Conduct in silico toxicity prediction using molecular dynamics simulation"
            )

        if "structure" in causal_node.description.lower():
            suggestions.append(
                "Attempt cryo-EM of glucosepane-crosslinked collagen fibrils"
            )
            suggestions.append(
                "Use AlphaFold to predict glucosepane-collagen binding geometry as interim model"
            )

        return suggestions

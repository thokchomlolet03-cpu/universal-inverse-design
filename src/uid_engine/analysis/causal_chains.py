"""Causal chain construction and inversion for the Inverse Design Engine.

This module defines the Target Causal Chains — the sequence of conditions
that MUST be satisfied to achieve a repair goal. The chain is then checked
against the knowledge graph to identify where it breaks (Negative Space).

The key insight: Instead of asking "What do we know?", we ask
"What MUST exist for the goal to be achieved?" and then check reality.
"""

from dataclasses import dataclass, field
from typing import Optional

from uid_engine.graph.schema import GapPriority


@dataclass
class CausalNode:
    """A single node in a causal chain.

    Each node represents a condition that must be satisfied.
    The node can be linked to an entity in the knowledge graph
    (if the condition is met) or flagged as unresolved (if it's not).
    """

    node_id: str                                    # Unique ID for this causal node
    description: str                                # What must be true
    required_graph_entity: Optional[str] = None     # Expected entity in graph (if known)
    required_edge_type: Optional[str] = None        # Expected relationship type
    required_status: str = "PROVEN"                 # Must be PROVEN, not HYPOTHESIZED or FAILED
    priority: GapPriority = GapPriority.CRITICAL    # Impact if this node is unresolved
    children: list["CausalNode"] = field(default_factory=list)  # Sub-requirements

    def add_child(self, child: "CausalNode") -> "CausalNode":
        """Add a sub-requirement and return the child for chaining."""
        self.children.append(child)
        return child


def build_glucosepane_repair_chain() -> CausalNode:
    """Build the Target Causal Chain for glucosepane crosslink repair.

    This is the inverse design chain: starting from the desired end state
    (restored arterial compliance) and working backward to identify every
    prerequisite condition.

    The chain structure:
        Goal: Restore arterial compliance
        └── Req: Remove glucosepane crosslinks from ECM
            ├── Req: A selective enzyme that cleaves glucosepane
            │   ├── Req: 3D structure of glucosepane-collagen complex
            │   ├── Req: Catalytic pocket matching glucosepane geometry
            │   └── Req: Known protein scaffold with modifiable active site
            ├── Req: In vivo delivery to arterial ECM
            │   ├── Req: Delivery vehicle that penetrates dense collagen
            │   └── Req: Stable enzyme that survives serum proteases
            └── Req: Safety validation
                ├── Req: Cleavage byproduct toxicity profile
                └── Req: ECM remodeling confirmation post-cleavage
    """

    # Root goal
    root = CausalNode(
        node_id="goal:arterial_compliance",
        description="Restore youthful compliance to human arterial extracellular matrix",
        priority=GapPriority.CRITICAL,
    )

    # Level 1: Remove crosslinks
    remove_crosslinks = root.add_child(CausalNode(
        node_id="req:remove_glucosepane",
        description="Remove glucosepane crosslinks from collagen/elastin in arterial ECM",
        priority=GapPriority.CRITICAL,
    ))

    # Level 2A: Selective enzyme
    selective_enzyme = remove_crosslinks.add_child(CausalNode(
        node_id="req:selective_enzyme",
        description=(
            "A stable, non-toxic enzyme or catalyst that selectively hydrolyzes "
            "the glucosepane imidazole ring without destroying native collagen "
            "lysine-arginine bonds"
        ),
        required_graph_entity="unknown:selective_enzyme",
        required_edge_type="DEGRADES",
        required_status="PROVEN",
        priority=GapPriority.CRITICAL,
    ))

    # Level 3: Sub-requirements for enzyme design
    selective_enzyme.add_child(CausalNode(
        node_id="req:crystal_structure",
        description=(
            "Experimentally resolved 3D structure of glucosepane crosslinked "
            "within native collagen fibers (X-ray crystallography or cryo-EM)"
        ),
        required_graph_entity="unknown:glucosepane_crystal_structure",
        priority=GapPriority.HIGH,
    ))

    selective_enzyme.add_child(CausalNode(
        node_id="req:catalytic_pocket",
        description=(
            "Computational design of a catalytic pocket with sub-nanomolar "
            "binding affinity for glucosepane (Kd < 10nM) and zero affinity "
            "for native lysine/arginine residues"
        ),
        priority=GapPriority.HIGH,
    ))

    selective_enzyme.add_child(CausalNode(
        node_id="req:protein_scaffold",
        description=(
            "A known protein scaffold (bacterial, fungal, or de novo designed) "
            "whose active site can be modified to accommodate glucosepane binding"
        ),
        required_graph_entity="protein:bacterial_class_i_enzyme",
        required_status="PROVEN",
        priority=GapPriority.HIGH,
    ))

    # Level 2B: Delivery
    delivery = remove_crosslinks.add_child(CausalNode(
        node_id="req:in_vivo_delivery",
        description="In vivo delivery mechanism to transport AGE-breaker to arterial ECM",
        required_graph_entity="unknown:in_vivo_delivery",
        priority=GapPriority.HIGH,
    ))

    delivery.add_child(CausalNode(
        node_id="req:ecm_penetration",
        description=(
            "Delivery vehicle capable of penetrating dense, crosslinked collagen "
            "matrix in aged arterial walls"
        ),
        priority=GapPriority.HIGH,
    ))

    delivery.add_child(CausalNode(
        node_id="req:serum_stability",
        description=(
            "Enzyme or catalyst must remain stable and active after exposure "
            "to human serum proteases (half-life > 24 hours)"
        ),
        priority=GapPriority.MEDIUM,
    ))

    # Level 2C: Safety
    safety = remove_crosslinks.add_child(CausalNode(
        node_id="req:safety_validation",
        description="Full safety profile for glucosepane cleavage therapy",
        priority=GapPriority.HIGH,
    ))

    safety.add_child(CausalNode(
        node_id="req:byproduct_toxicity",
        description=(
            "Toxicity and immunogenicity profile of molecular fragments "
            "remaining on collagen after glucosepane cleavage"
        ),
        required_graph_entity="unknown:cleavage_byproduct_toxicity",
        priority=GapPriority.MEDIUM,
    ))

    safety.add_child(CausalNode(
        node_id="req:ecm_remodeling",
        description=(
            "Confirmation that arterial tissue regains youthful mechanical properties "
            "after crosslink removal (spontaneous or fibroblast-mediated remodeling)"
        ),
        required_graph_entity="unknown:ecm_remodeling_post_cleavage",
        priority=GapPriority.MEDIUM,
    ))

    return root


def flatten_chain(root: CausalNode) -> list[CausalNode]:
    """Flatten a causal chain tree into a list of all nodes (depth-first)."""
    result = [root]
    for child in root.children:
        result.extend(flatten_chain(child))
    return result

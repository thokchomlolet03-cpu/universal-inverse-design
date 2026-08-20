"""Graph builder — Constructs the epistemic knowledge graph from ingested data.

This module creates a NetworkX directed graph (DiGraph) populated with typed
nodes and edges conforming to the schema defined in schema.py. It includes
a mock data loader for Phase A testing before real API data is available.
"""

import networkx as nx
from rich.console import Console

from uid_engine.graph.schema import (
    EdgeData,
    EdgeType,
    EvidenceStatus,
    GapPriority,
    NodeData,
    NodeType,
    SENS_DAMAGE_CATEGORIES,
)
from uid_engine import config

console = Console()


class EpistemicGraph:
    """The core knowledge graph for the Universal Inverse Design Engine.

    This graph represents biological knowledge as typed nodes (molecules,
    proteins, genes, papers, unknowns) connected by typed causal edges
    (catalyzes, requires, causes_damage, etc.).

    The graph's unique feature is UNKNOWN nodes — explicit representations
    of missing scientific knowledge (Negative Space).
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self._node_count = 0
        self._edge_count = 0

    # ─── Node Operations ────────────────────────────────────────────────────

    def add_node(self, node_data: NodeData) -> str:
        """Add a typed node to the graph. Returns the node_id.

        If a node with the same ID already exists, its attributes are
        updated (NetworkX merge semantics) but the counter is NOT
        incremented — preventing count drift.
        """
        is_new = node_data.node_id not in self.graph
        self.graph.add_node(node_data.node_id, **node_data.to_dict())
        if is_new:
            self._node_count += 1
        return node_data.node_id

    def add_edge(self, source_id: str, target_id: str, edge_data: EdgeData) -> None:
        """Add a typed, directional edge between two nodes."""
        if source_id not in self.graph:
            raise ValueError(f"Source node '{source_id}' not in graph")
        if target_id not in self.graph:
            raise ValueError(f"Target node '{target_id}' not in graph")
        self.graph.add_edge(source_id, target_id, **edge_data.to_dict())
        self._edge_count += 1

    def has_node(self, node_id: str) -> bool:
        return node_id in self.graph

    def get_node(self, node_id: str) -> dict:
        return self.graph.nodes[node_id]

    def get_nodes_by_type(self, node_type: NodeType) -> list[str]:
        """Return all node_ids of a given type."""
        return [
            n for n, d in self.graph.nodes(data=True)
            if d.get("node_type") == node_type.value
        ]

    def get_successors(self, node_id: str) -> list[tuple[str, dict]]:
        """Return all outgoing edges from a node with their data."""
        return [
            (target, self.graph.edges[node_id, target])
            for target in self.graph.successors(node_id)
        ]

    def get_predecessors(self, node_id: str) -> list[tuple[str, dict]]:
        """Return all incoming edges to a node with their data."""
        return [
            (source, self.graph.edges[source, node_id])
            for source in self.graph.predecessors(node_id)
        ]

    # ─── Statistics ──────────────────────────────────────────────────────────

    def stats(self) -> dict:
        """Return summary statistics about the graph."""
        type_counts = {}
        for _, data in self.graph.nodes(data=True):
            t = data.get("node_type", "UNTYPED")
            type_counts[t] = type_counts.get(t, 0) + 1

        edge_type_counts = {}
        for _, _, data in self.graph.edges(data=True):
            t = data.get("edge_type", "UNTYPED")
            edge_type_counts[t] = edge_type_counts.get(t, 0) + 1

        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "node_types": type_counts,
            "edge_types": edge_type_counts,
            "unknowns": len(self.get_nodes_by_type(NodeType.UNKNOWN)),
        }

    def print_stats(self) -> None:
        """Pretty-print graph statistics."""
        s = self.stats()
        console.print("\n[bold cyan]═══ Epistemic Graph Statistics ═══[/bold cyan]")
        console.print(f"  Total nodes: [green]{s['total_nodes']}[/green]")
        console.print(f"  Total edges: [green]{s['total_edges']}[/green]")
        console.print(f"  Unknown gaps: [bold red]{s['unknowns']}[/bold red]")
        console.print("\n  [bold]Node types:[/bold]")
        for t, c in sorted(s["node_types"].items()):
            console.print(f"    {t}: {c}")
        console.print("\n  [bold]Edge types:[/bold]")
        for t, c in sorted(s["edge_types"].items()):
            console.print(f"    {t}: {c}")
        console.print()


def build_mock_glucosepane_graph() -> EpistemicGraph:
    """Build a hand-coded mock graph for glucosepane crosslink research.

    This mock graph contains real scientific facts about glucosepane, coded
    manually from known literature. It serves as the test dataset for
    Phase A/B development before real API ingestion is implemented.

    The mock data deliberately includes:
    - Known facts (to test graph construction)
    - Explicit UNKNOWN nodes (to test gap detection)
    - A FAILED experiment edge (to test status filtering)
    """
    g = EpistemicGraph()

    # ─── SENS Damage Category ───────────────────────────────────────────────

    g.add_node(NodeData(
        node_id="sens:extracellular_crosslinks",
        node_type=NodeType.DAMAGE_CLASS,
        name="Extracellular Crosslinks (GlycoSENS)",
        description=SENS_DAMAGE_CATEGORIES["extracellular_crosslinks"]["description"],
        source="SENS Research Foundation",
    ))

    # ─── Core Molecules ─────────────────────────────────────────────────────

    g.add_node(NodeData(
        node_id="mol:glucosepane",
        node_type=NodeType.MOLECULE,
        name="Glucosepane",
        description=(
            "The most abundant Advanced Glycation End-product (AGE) crosslink in aged "
            "human tissue. A lysine-arginine crosslink with a bicyclic aminal-amidine core. "
            "Accumulates irreversibly in collagen and elastin throughout life."
        ),
        source="PMID:21561553",
        metadata={"molecular_formula": "C12H22N4O4", "crosslink_type": "lysine-arginine"},
    ))

    g.add_node(NodeData(
        node_id="mol:collagen",
        node_type=NodeType.MOLECULE,
        name="Collagen (Type I)",
        description="The most abundant structural protein in the human body. Primary component of the extracellular matrix.",
        source="UniProt",
    ))

    g.add_node(NodeData(
        node_id="mol:glucose",
        node_type=NodeType.MOLECULE,
        name="D-Glucose",
        description="Primary metabolic sugar. Initiates the Maillard reaction leading to AGE formation.",
        source="KEGG",
    ))

    # ─── Tissues ────────────────────────────────────────────────────────────

    g.add_node(NodeData(
        node_id="tissue:arteries",
        node_type=NodeType.TISSUE,
        name="Arterial walls",
        description="Blood vessel walls. Glucosepane crosslinks stiffen arterial collagen, causing hypertension.",
        source="PMID:21561553",
    ))

    g.add_node(NodeData(
        node_id="tissue:skin",
        node_type=NodeType.TISSUE,
        name="Skin (dermis)",
        description="Dermal collagen and elastin lose elasticity due to AGE crosslinking.",
        source="PMID:21561553",
    ))

    # ─── Known Proteins / Enzymes ───────────────────────────────────────────

    g.add_node(NodeData(
        node_id="protein:fructosamine_3_kinase",
        node_type=NodeType.PROTEIN,
        name="Fructosamine-3-kinase (FN3K)",
        description=(
            "Human enzyme that phosphorylates and destabilizes fructosamines (early glycation "
            "products). Cannot break mature glucosepane crosslinks."
        ),
        source="UniProt:Q9H479",
        metadata={"organism": "Homo sapiens", "ec_number": "2.7.1.218"},
    ))

    g.add_node(NodeData(
        node_id="protein:bacterial_class_i_enzyme",
        node_type=NodeType.PROTEIN,
        name="Bacterial Class I-like enzyme (candidate)",
        description=(
            "Candidate glucosepane-degrading enzyme identified via metagenomic screening. "
            "Demonstrated in vitro activity releasing citrulline. Selectivity and in vivo "
            "stability remain untested."
        ),
        source="Patent:WO2020215043A1",
        confidence=0.5,
        metadata={"organism": "soil bacterium (uncharacterized)", "status": "candidate"},
    ))

    # ─── Papers ─────────────────────────────────────────────────────────────

    g.add_node(NodeData(
        node_id="paper:PMID_21561553",
        node_type=NodeType.PAPER,
        name="Sell & Monnier 2012 — Glucosepane: major AGE crosslink",
        description="Landmark paper establishing glucosepane as the dominant AGE crosslink in human tissue.",
        source="PubMed",
        metadata={"year": 2012, "journal": "Chem Res Toxicol"},
    ))

    g.add_node(NodeData(
        node_id="paper:WO2020215043A1",
        node_type=NodeType.PAPER,
        name="Patent: Glucosepane-degrading enzymes from metagenomics",
        description="Patent describing enzymatic candidates for glucosepane degradation identified through metagenomic screening.",
        source="Patent Database",
        metadata={"year": 2020, "type": "patent"},
    ))

    g.add_node(NodeData(
        node_id="paper:canalised_cleavage_2026",
        node_type=NodeType.PAPER,
        name="Canalised Cleavage of Glucosepane (2026)",
        description=(
            "Reports two chemical cleavage strategies: thermal (Lewis acid + alpha-effect "
            "nucleophiles) and photoredox (visible-light-driven). First convergent catalytic "
            "approach to glucosepane breakdown."
        ),
        source="ChemRxiv",
        metadata={"year": 2026, "type": "preprint"},
    ))

    # ─── Mechanisms ─────────────────────────────────────────────────────────

    g.add_node(NodeData(
        node_id="mech:maillard_reaction",
        node_type=NodeType.MECHANISM,
        name="Maillard Reaction / Non-enzymatic Glycation",
        description="Glucose reacts with lysine/arginine residues on collagen to form early glycation products, which rearrange into irreversible AGE crosslinks over years.",
        source="PMID:21561553",
    ))

    g.add_node(NodeData(
        node_id="mech:lewis_acid_cleavage",
        node_type=NodeType.MECHANISM,
        name="Lewis Acid Thermal Cleavage of Glucosepane",
        description="Uses Lewis acid and mild-acid catalysis for ring-opening, then alpha-effect nucleophiles trap the iminium intermediate.",
        source="ChemRxiv:canalised_cleavage_2026",
        metadata={"status": "demonstrated_in_vitro"},
    ))

    g.add_node(NodeData(
        node_id="mech:photoredox_cleavage",
        node_type=NodeType.MECHANISM,
        name="Photoredox Cleavage of Glucosepane",
        description="Visible-light-driven redox chemistry to cleave glucosepane. Alternative to thermal method.",
        source="ChemRxiv:canalised_cleavage_2026",
        metadata={"status": "demonstrated_in_vitro"},
    ))

    # ─── EXPLICIT UNKNOWNS (Negative Space) ─────────────────────────────────

    g.add_node(NodeData(
        node_id="unknown:selective_enzyme",
        node_type=NodeType.UNKNOWN,
        name="MISSING: Selective glucosepane-cleaving enzyme",
        description=(
            "No validated enzyme exists that selectively cleaves the glucosepane "
            "imidazole ring without degrading native collagen lysine-arginine bonds. "
            "Bacterial candidates exist but selectivity is untested."
        ),
        metadata={"priority": GapPriority.CRITICAL.value, "required_for": "arterial_compliance_repair"},
    ))

    g.add_node(NodeData(
        node_id="unknown:glucosepane_crystal_structure",
        node_type=NodeType.UNKNOWN,
        name="MISSING: 3D crystal structure of glucosepane-crosslinked collagen",
        description=(
            "The exact 3D geometry of glucosepane bonded within native collagen fibers "
            "has never been experimentally resolved via X-ray crystallography or cryo-EM. "
            "Without this, rational enzyme design cannot target the exact bond geometry."
        ),
        metadata={"priority": GapPriority.HIGH.value, "required_for": "rational_enzyme_design"},
    ))

    g.add_node(NodeData(
        node_id="unknown:in_vivo_delivery",
        node_type=NodeType.UNKNOWN,
        name="MISSING: In vivo delivery mechanism for AGE-breaker enzymes",
        description=(
            "No validated delivery vehicle exists to transport a glucosepane-cleaving "
            "enzyme into the dense extracellular matrix of aged arterial walls in a living "
            "human. Lipid nanoparticles, AAV vectors, and direct injection are all untested "
            "for this specific target."
        ),
        metadata={"priority": GapPriority.HIGH.value, "required_for": "therapeutic_deployment"},
    ))

    g.add_node(NodeData(
        node_id="unknown:cleavage_byproduct_toxicity",
        node_type=NodeType.UNKNOWN,
        name="MISSING: Toxicity profile of glucosepane cleavage byproducts",
        description=(
            "When glucosepane crosslinks are cleaved, the fragmented molecular residues "
            "remain attached to collagen. Whether these fragments are toxic, immunogenic, "
            "or safely cleared by the body is completely unknown."
        ),
        metadata={"priority": GapPriority.MEDIUM.value, "required_for": "safety_validation"},
    ))

    g.add_node(NodeData(
        node_id="unknown:ecm_remodeling_post_cleavage",
        node_type=NodeType.UNKNOWN,
        name="MISSING: ECM remodeling dynamics after crosslink removal",
        description=(
            "After glucosepane crosslinks are removed from collagen, will the tissue "
            "spontaneously regain youthful elasticity? Or does the ECM require active "
            "remodeling by fibroblasts to restore mechanical properties? Unknown."
        ),
        metadata={"priority": GapPriority.MEDIUM.value, "required_for": "functional_tissue_restoration"},
    ))

    # ─── Edges: Causal Relationships ────────────────────────────────────────

    # Glucose → Maillard Reaction → Glucosepane → Crosslinks Collagen → Damages Arteries
    g.add_edge("mol:glucose", "mech:maillard_reaction", EdgeData(
        edge_type=EdgeType.ACTIVATES,
        status=EvidenceStatus.PROVEN,
        source="PMID:21561553",
        context="glucose reacts non-enzymatically with protein amino groups",
    ))

    g.add_edge("mech:maillard_reaction", "mol:glucosepane", EdgeData(
        edge_type=EdgeType.PRODUCES,
        status=EvidenceStatus.PROVEN,
        source="PMID:21561553",
        context="rearrangement produces the dominant crosslink glucosepane",
    ))

    g.add_edge("mol:glucosepane", "mol:collagen", EdgeData(
        edge_type=EdgeType.CROSSLINKS,
        status=EvidenceStatus.PROVEN,
        source="PMID:21561553",
        context="glucosepane crosslinks collagen fibers via lysine-arginine",
    ))

    g.add_edge("mol:glucosepane", "tissue:arteries", EdgeData(
        edge_type=EdgeType.CAUSES_DAMAGE,
        status=EvidenceStatus.PROVEN,
        source="PMID:21561553",
        context="crosslinked collagen stiffens arterial walls",
    ))

    g.add_edge("mol:glucosepane", "tissue:skin", EdgeData(
        edge_type=EdgeType.CAUSES_DAMAGE,
        status=EvidenceStatus.PROVEN,
        source="PMID:21561553",
        context="dermal collagen loses elasticity due to crosslinking",
    ))

    # Glucosepane → SENS Category
    g.add_edge("mol:glucosepane", "sens:extracellular_crosslinks", EdgeData(
        edge_type=EdgeType.PART_OF,
        status=EvidenceStatus.PROVEN,
        source="SENS Research Foundation",
    ))

    # FN3K — Can deglycate early products but NOT mature glucosepane
    g.add_edge("protein:fructosamine_3_kinase", "mol:glucosepane", EdgeData(
        edge_type=EdgeType.DEGRADES,
        status=EvidenceStatus.FAILED,
        source="UniProt:Q9H479",
        context="FN3K acts on early fructosamines, not mature crosslinks",
    ))

    # Bacterial enzyme — candidate, in vitro only
    g.add_edge("protein:bacterial_class_i_enzyme", "mol:glucosepane", EdgeData(
        edge_type=EdgeType.DEGRADES,
        status=EvidenceStatus.HYPOTHESIZED,
        confidence=0.5,
        source="Patent:WO2020215043A1",
        context="in vitro activity demonstrated, releases citrulline",
    ))

    # Chemical cleavage strategies
    g.add_edge("mech:lewis_acid_cleavage", "mol:glucosepane", EdgeData(
        edge_type=EdgeType.DEGRADES,
        status=EvidenceStatus.PROVEN,
        confidence=0.7,
        source="ChemRxiv:canalised_cleavage_2026",
        context="convergent catalytic approach achieved ring-opening",
    ))

    g.add_edge("mech:photoredox_cleavage", "mol:glucosepane", EdgeData(
        edge_type=EdgeType.DEGRADES,
        status=EvidenceStatus.PROVEN,
        confidence=0.7,
        source="ChemRxiv:canalised_cleavage_2026",
        context="visible-light-driven redox cleavage demonstrated",
    ))

    # Papers → Entities they report on
    g.add_edge("mol:glucosepane", "paper:PMID_21561553", EdgeData(
        edge_type=EdgeType.REPORTED_IN, source="PubMed",
    ))
    g.add_edge("protein:bacterial_class_i_enzyme", "paper:WO2020215043A1", EdgeData(
        edge_type=EdgeType.REPORTED_IN, source="Patent Database",
    ))
    g.add_edge("mech:lewis_acid_cleavage", "paper:canalised_cleavage_2026", EdgeData(
        edge_type=EdgeType.REPORTED_IN, source="ChemRxiv",
    ))

    # Unknown gaps → what they are required for
    g.add_edge("unknown:selective_enzyme", "mol:glucosepane", EdgeData(
        edge_type=EdgeType.REQUIRES,
        context="selective cleavage needed to remove glucosepane safely",
    ))

    g.add_edge("unknown:glucosepane_crystal_structure", "unknown:selective_enzyme", EdgeData(
        edge_type=EdgeType.REQUIRES,
        context="3D structure needed for rational enzyme active site design",
    ))

    g.add_edge("unknown:in_vivo_delivery", "unknown:selective_enzyme", EdgeData(
        edge_type=EdgeType.REQUIRES,
        context="delivery vehicle needed to get enzyme into ECM",
    ))

    g.add_edge("unknown:cleavage_byproduct_toxicity", "unknown:selective_enzyme", EdgeData(
        edge_type=EdgeType.REQUIRES,
        context="byproduct safety must be established before clinical use",
    ))

    g.add_edge("unknown:ecm_remodeling_post_cleavage", "unknown:selective_enzyme", EdgeData(
        edge_type=EdgeType.REQUIRES,
        context="tissue must actually restore function after crosslink removal",
    ))

    console.print("[bold green]✓ Mock glucosepane graph built successfully[/bold green]")
    return g

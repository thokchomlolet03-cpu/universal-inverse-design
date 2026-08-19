"""Graph schema — Node and Edge type definitions for the longevity knowledge graph.

This module defines the strict ontology that governs how biological knowledge is
represented in the epistemic graph. Every node and edge must conform to these types.
No ad-hoc types are allowed — the LLM extraction, data ingestion, and gap detector
all reference this single source of truth.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ─── Node Types ──────────────────────────────────────────────────────────────────

class NodeType(str, Enum):
    """Every node in the knowledge graph must be one of these types."""

    MOLECULE = "MOLECULE"           # Chemical compound (glucosepane, AGEs, drugs)
    PROTEIN = "PROTEIN"             # Enzyme or structural protein
    GENE = "GENE"                   # Gene encoding a protein
    PATHWAY = "PATHWAY"             # Metabolic or signaling pathway
    TISSUE = "TISSUE"               # Human tissue or organ
    PAPER = "PAPER"                 # Scientific publication
    DAMAGE_CLASS = "DAMAGE_CLASS"   # SENS damage category
    MECHANISM = "MECHANISM"         # A biological mechanism (known, hypothesized, or missing)
    UNKNOWN = "UNKNOWN"             # An explicitly missing piece of knowledge (Negative Space)


# ─── Edge Types ──────────────────────────────────────────────────────────────────

class EdgeType(str, Enum):
    """Every edge in the knowledge graph must be one of these types."""

    CATALYZES = "CATALYZES"             # Enzyme catalyzes a reaction
    CROSSLINKS = "CROSSLINKS"           # Molecule creates crosslinks in tissue
    CAUSES_DAMAGE = "CAUSES_DAMAGE"     # Mechanism causes tissue damage
    REPORTED_IN = "REPORTED_IN"         # Finding reported in a paper
    REQUIRES = "REQUIRES"               # Achieving X requires Y
    PART_OF = "PART_OF"                 # Entity belongs to pathway/category
    INHIBITS = "INHIBITS"               # Regulatory inhibition
    ACTIVATES = "ACTIVATES"             # Regulatory activation
    DEGRADES = "DEGRADES"               # Enzyme/compound degrades a substrate
    PRODUCES = "PRODUCES"               # Reaction produces a product
    BLOCKS = "BLOCKS"                   # Entity blocks or prevents a process


# ─── Evidence Status ─────────────────────────────────────────────────────────────

class EvidenceStatus(str, Enum):
    """The experimental validation status of a causal relationship."""

    PROVEN = "PROVEN"               # Experimentally validated (in vitro or in vivo)
    HYPOTHESIZED = "HYPOTHESIZED"   # Proposed but not yet tested
    FAILED = "FAILED"               # Tested and found to NOT work
    UNKNOWN = "UNKNOWN"             # Status cannot be determined


# ─── Gap Priority ────────────────────────────────────────────────────────────────

class GapPriority(str, Enum):
    """Priority level for an identified epistemic gap."""

    CRITICAL = "CRITICAL"   # Blocks ALL downstream repair goals
    HIGH = "HIGH"           # Blocks multiple repair pathways
    MEDIUM = "MEDIUM"       # Blocks a single pathway, alternatives may exist
    LOW = "LOW"             # Nice to have, not on critical path


# ─── Data Classes for Graph Entities ─────────────────────────────────────────────

@dataclass
class NodeData:
    """Attributes attached to every node in the graph."""

    node_id: str                                # Unique identifier (e.g., "glucosepane", "PMID:12345")
    node_type: NodeType                         # Must be a valid NodeType
    name: str                                   # Human-readable name
    description: str = ""                       # Detailed description
    confidence: float = 1.0                     # 0.0 to 1.0 — how reliable is this data?
    source: str = ""                            # Where this data came from (e.g., "UniProt", "PMID:12345")
    metadata: dict = field(default_factory=dict) # Additional type-specific attributes

    def to_dict(self) -> dict:
        """Serialize to dictionary for NetworkX node attributes."""
        return {
            "node_type": self.node_type.value,
            "name": self.name,
            "description": self.description,
            "confidence": self.confidence,
            "source": self.source,
            **self.metadata,
        }


@dataclass
class EdgeData:
    """Attributes attached to every edge in the graph."""

    edge_type: EdgeType                         # Must be a valid EdgeType
    status: EvidenceStatus = EvidenceStatus.PROVEN  # Experimental status
    confidence: float = 1.0                     # 0.0 to 1.0
    source: str = ""                            # Paper or database source
    context: str = ""                           # Brief quote from source proving relationship
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to dictionary for NetworkX edge attributes."""
        return {
            "edge_type": self.edge_type.value,
            "status": self.status.value,
            "confidence": self.confidence,
            "source": self.source,
            "context": self.context,
            **self.metadata,
        }


# ─── The 7 SENS Damage Categories ───────────────────────────────────────────────

SENS_DAMAGE_CATEGORIES = {
    "extracellular_crosslinks": {
        "name": "Extracellular Crosslinks (GlycoSENS)",
        "description": (
            "Advanced Glycation End-products (AGEs) like glucosepane form covalent "
            "crosslinks between collagen and elastin fibers, causing tissue stiffening, "
            "arterial hypertension, and organ failure."
        ),
        "key_molecules": ["glucosepane", "pentosidine", "CML", "CEL"],
        "affected_tissues": ["arteries", "skin", "lungs", "heart", "kidneys"],
    },
    "extracellular_aggregates": {
        "name": "Extracellular Aggregates (AmyloSENS)",
        "description": "Amyloid plaques and other protein aggregates accumulate between cells.",
        "key_molecules": ["amyloid_beta", "transthyretin", "IAPP"],
        "affected_tissues": ["brain", "heart", "pancreas"],
    },
    "intracellular_junk": {
        "name": "Intracellular Junk (LysoSENS)",
        "description": (
            "Oxidized lipids and proteins (lipofuscin, 7-ketocholesterol) accumulate "
            "inside lysosomes, choking cellular waste disposal."
        ),
        "key_molecules": ["lipofuscin", "7-ketocholesterol", "A2E"],
        "affected_tissues": ["retina", "neurons", "heart_muscle"],
    },
    "cell_loss": {
        "name": "Cell Loss & Atrophy (RepleniSENS)",
        "description": "Tissues lose cells over time without adequate replacement from stem cells.",
        "key_molecules": [],
        "affected_tissues": ["heart", "brain", "muscle", "immune_system"],
    },
    "senescent_cells": {
        "name": "Senescent Cells (ApoptoSENS)",
        "description": (
            "Damaged cells enter a 'zombie' state, secreting toxic inflammatory "
            "signals (SASP) that poison surrounding healthy tissue."
        ),
        "key_molecules": ["p16INK4a", "p21", "SASP_cytokines"],
        "affected_tissues": ["all_tissues"],
    },
    "mitochondrial_mutations": {
        "name": "Mitochondrial Mutations (MitoSENS)",
        "description": (
            "Mitochondrial DNA accumulates mutations 10-100x faster than nuclear DNA, "
            "causing energy brownouts and toxic ROS production."
        ),
        "key_molecules": ["mtDNA", "Complex_I", "Complex_III"],
        "affected_tissues": ["all_tissues"],
    },
    "nuclear_mutations": {
        "name": "Nuclear Mutations & Epigenetic Drift (OncoSENS)",
        "description": (
            "Nuclear DNA accumulates mutations and epigenetic noise, increasing cancer "
            "risk and disrupting cell identity."
        ),
        "key_molecules": ["p53", "telomerase", "DNMT"],
        "affected_tissues": ["all_tissues"],
    },
}

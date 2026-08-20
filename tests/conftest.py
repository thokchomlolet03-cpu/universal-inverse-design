"""Shared test fixtures for the Universal Inverse Design Engine."""

import pytest
import tempfile
from pathlib import Path

from uid_engine.graph.builder import EpistemicGraph, build_mock_glucosepane_graph
from uid_engine.graph.schema import NodeData, NodeType, EdgeData, EdgeType, EvidenceStatus
from uid_engine import config


@pytest.fixture
def mock_graph() -> EpistemicGraph:
    """Build the standard mock glucosepane graph."""
    return build_mock_glucosepane_graph()


@pytest.fixture
def tmp_graph_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for graph file I/O tests."""
    return tmp_path


@pytest.fixture
def minimal_graph() -> EpistemicGraph:
    """Build a tiny graph with one node of each core type for unit tests."""
    g = EpistemicGraph()

    g.add_node(NodeData(
        node_id="mol:test_mol",
        node_type=NodeType.MOLECULE,
        name="Test Molecule",
        confidence=0.75,
    ))
    g.add_node(NodeData(
        node_id="protein:test_prot",
        node_type=NodeType.PROTEIN,
        name="Test Protein",
        confidence=0.9,
        metadata={"reviewed": True, "organism": "E. coli"},
    ))
    g.add_edge("mol:test_mol", "protein:test_prot", EdgeData(
        edge_type=EdgeType.INHIBITS,
        status=EvidenceStatus.PROVEN,
        confidence=0.8,
    ))

    return g


@pytest.fixture
def sample_paper() -> dict:
    """A synthetic paper dict matching the PubMed ingestion format."""
    return {
        "pmid": "99999999",
        "title": "Glucosepane crosslinks collagen in arterial walls causing hypertension",
        "abstract": (
            "Glucosepane is the dominant AGE crosslink in aged human collagen. "
            "It crosslinks lysine-arginine residues in arterial collagen, causing "
            "tissue stiffening and hypertension. Aminoguanidine failed to reverse "
            "existing crosslinks but inhibited new formation."
        ),
        "authors": ["Smith J", "Doe A"],
        "journal": "J Gerontology",
        "year": "2025",
        "doi": "10.1234/test",
        "mesh_terms": ["Glycation", "Collagen"],
        "keywords": ["glucosepane", "aging"],
    }

"""Unit tests for Twist Bioscience gene synthesis and BL21 expression handoff."""

import csv
from pathlib import Path
import pytest

from uid_engine.generative.candidate_model import CandidateProtein, BiophysicalProperties, ScreeningResult
from uid_engine.generative.synthesis_handoff import (
    calculate_gc_content,
    reverse_translate_bl21,
    sanitize_synthesis_dna,
    assemble_pet28a_construct,
    export_twist_order_csv,
    export_genbank_record,
    transition_graph_candidate_to_synthesis_ordered,
    TwistConstruct,
)
from uid_engine.graph.builder import EpistemicGraph
from uid_engine.graph.schema import NodeData, NodeType, EdgeData, EdgeType, EvidenceStatus


@pytest.fixture
def mock_candidate():
    props = BiophysicalProperties(
        molecular_weight=28450.0,
        isoelectric_point=6.4,
        net_charge_ph74=-1.2,
        gravy_score=-0.14,
        aromaticity=0.08,
        instability_index=28.6,
    )
    result = ScreeningResult(
        passed=True,
        gate_1_plddt=True,
        gate_2_sc_rmsd=True,
        gate_3_catalytic_retention=True,
        gate_4_biophysical_solubility=True,
        gate_5_docking=True,
        gate_6_selectivity=True,
        mean_plddt=88.4,
        sc_rmsd=1.14,
        gravy_score=-0.14,
    )
    seq = "MKLLVTALLALLAHHASEDYKPNDVDYIEENLYFQGHISDAPSLVTEEQVALVKGKLVEVTKEE"
    return CandidateProtein(
        candidate_id="CAND-TEST-03",
        target_spec_id="SPEC-TEST-03",
        target_domain="Glucosepane",
        causal_gap_id="gap:glucosepane_selective_cleavage",
        sequence=seq,
        length=len(seq),
        predicted_plddt=88.4,
        predicted_ptm=0.86,
        sc_rmsd=1.14,
        catalytic_residues={"H54": "HIS", "D112": "ASP", "S198": "SER"},
        biophysical_properties=props,
        screening_result=result,
    )


def test_reverse_translate_bl21():
    """Verify codon adaptation length, GC content, and CAI score."""
    seq = "MKLLVTALLA"
    dna, gc, cai = reverse_translate_bl21(seq)
    assert len(dna) == len(seq) * 3
    assert 40.0 <= gc <= 60.0
    assert cai >= 0.88


def test_sanitize_synthesis_dna_purges_motifs():
    """Homopolymer runs (>4 identical bases) and internal restriction sites must be sanitized."""
    dirty_dna = "ATGAAAAAATTTGGATCCGAATTCAAAAATTT"
    clean_dna = sanitize_synthesis_dna(dirty_dna)

    assert "AAAAAA" not in clean_dna
    assert "GGATCC" not in clean_dna  # BamHI
    assert "GAATTC" not in clean_dna  # EcoRI


def test_assemble_pet28a_construct(mock_candidate):
    """pET-28a construct must contain NdeI, 6xHis, TEV site, CDS, tandem stops, and XhoI."""
    construct = assemble_pet28a_construct(mock_candidate, vector_name="pET-28a(+)")
    assert isinstance(construct, TwistConstruct)
    assert construct.full_construct_dna.startswith("CATATG")  # NdeI
    assert construct.full_construct_dna.endswith("CTCGAG")    # XhoI
    assert "CATCACCATCACCATCAC" in construct.full_construct_dna  # 6xHis
    assert "GAAAACCTGTATTTTCAGGGC" in construct.full_construct_dna  # TEV site
    assert "TAATGA" in construct.full_construct_dna  # Dual stops
    assert construct.twist_synthesis_score == "ACCEPTED_STANDARD"


def test_export_twist_order_csv(mock_candidate, tmp_path):
    """Twist order CSV must be valid and conform to batch portal format."""
    construct = assemble_pet28a_construct(mock_candidate)
    csv_file = tmp_path / "twist_test_order.csv"
    exported = export_twist_order_csv([construct], output_path=csv_file)

    assert exported.exists()
    with open(exported, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["Item Name"] == construct.item_name
        assert rows[0]["Target Vector"] == "pET-28a(+)"
        assert rows[0]["Purification Tag"] == "N-terminal 6xHis"
        assert rows[0]["Cleavage Site"] == "TEV (ENLYFQ/G)"


def test_export_genbank_record(mock_candidate, tmp_path):
    """GenBank record must contain standard LOCUS, FEATURES, tags, and ORIGIN."""
    construct = assemble_pet28a_construct(mock_candidate)
    gb_file = tmp_path / f"{construct.item_name}.gb"
    exported = export_genbank_record(construct, output_path=gb_file)

    assert exported.exists()
    content = exported.read_text(encoding="utf-8")
    assert "LOCUS" in content
    assert "FEATURES" in content
    assert "6xHis Tag" in content
    assert "TEV Cleavage Site" in content
    assert "ORIGIN" in content
    assert "//" in content


def test_transition_graph_candidate_to_synthesis_ordered():
    """Graph edge status must transition from HYPOTHESIZED_IN_SILICO to SYNTHESIS_ORDERED."""
    graph = EpistemicGraph()
    cand_node = "protein:cand-test-03"
    target_node = "mol:glucosepane"

    graph.add_node(NodeData(node_id=cand_node, node_type=NodeType.PROTEIN, name="Cand 03"))
    graph.add_node(NodeData(node_id=target_node, node_type=NodeType.MOLECULE, name="Glucosepane"))
    graph.add_edge(cand_node, target_node, EdgeData(
        edge_type=EdgeType.DEGRADES,
        status=EvidenceStatus.HYPOTHESIZED_IN_SILICO,
    ))

    count = transition_graph_candidate_to_synthesis_ordered(graph, "CAND-TEST-03")
    assert count == 1
    edge = graph.get_edge(cand_node, target_node)
    assert edge["status"] == EvidenceStatus.SYNTHESIS_ORDERED.value
    assert "TwistBioscience" in edge["source"]

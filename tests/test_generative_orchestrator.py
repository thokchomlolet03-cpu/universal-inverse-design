"""Tests for the Generative Inference Orchestrator and Graph Loop Closure."""

from pathlib import Path
import json
import pytest

from uid_engine.analysis.design_spec import DeNovoDesignSpec
from uid_engine.generative.orchestrator import (
    run_generative_pipeline_for_spec,
    inject_candidate_into_graph,
)
from uid_engine.graph.builder import build_mock_glucosepane_graph, EpistemicGraph
from uid_engine.analysis.gap_detector import NegativeSpaceDetector
from uid_engine.chains.registry import CausalChainRegistry
from uid_engine.graph.schema import GapPriority, NodeType


class TestGenerativeOrchestrator:
    """Verify autonomous candidate generation, screening, and graph loop closure."""

    def test_run_generative_pipeline_creates_artifacts(self, tmp_path):
        spec = DeNovoDesignSpec(
            spec_id="SPEC-TEST-GLUCOSEPANE-01",
            target_name="Glucosepane",
            causal_gap_id="req:selective_enzyme",
            gap_priority="CRITICAL",
            gap_description="Selective glucosepane hydrolase",
            substrate_name="Glucosepane",
            substrate_smiles="C1=CC=C(C=C1)C=O",
            substrate_3d_sdf_path=None,
            substrate_molecular_weight=430.25,
            substrate_formula="C18H34N6O6",
            target_plddt_minimum=80.0,
            target_pocket_volume_angstrom3="500 Å³",
            suggested_catalytic_motifs=["His-Asp-Ser"],
            homologous_scaffolds=[],
            rfdiffusion_all_atom_flags={},
            esm3_prompt_config={"task": "active_site_scaffolding", "sampling_temperature": 0.1},
            proteinmpnn_config={"sampling_temp": 0.1},
        )

        candidates = run_generative_pipeline_for_spec(
            spec,
            num_variants=3,
            min_plddt=80.0,
            output_dir=tmp_path,
        )

        assert len(candidates) == 3
        cand = candidates[0]
        assert Path(cand.pdb_path).exists()
        assert Path(cand.fasta_path).exists()

        # Check FASTA content
        fasta_text = Path(cand.fasta_path).read_text(encoding="utf-8")
        assert f">{cand.candidate_id}" in fasta_text
        assert "pLDDT:" in fasta_text

    def test_inject_candidate_into_graph_closes_loop(self):
        graph = build_mock_glucosepane_graph()
        spec = DeNovoDesignSpec(
            spec_id="SPEC-TEST-02",
            target_name="Glucosepane",
            causal_gap_id="req:selective_enzyme",
            gap_priority="CRITICAL",
            gap_description="Selective glucosepane hydrolase",
            substrate_name="Glucosepane",
            substrate_smiles="C1=CC=C(C=C1)C=O",
            substrate_3d_sdf_path=None,
            substrate_molecular_weight=430.25,
            substrate_formula="C18H34N6O6",
            target_plddt_minimum=80.0,
            target_pocket_volume_angstrom3="500 Å³",
            suggested_catalytic_motifs=["His-Asp-Ser"],
            homologous_scaffolds=[],
            rfdiffusion_all_atom_flags={},
            esm3_prompt_config={},
            proteinmpnn_config={},
        )

        candidates = run_generative_pipeline_for_spec(spec, num_variants=1, min_plddt=80.0)
        passing_cand = candidates[0]
        inject_candidate_into_graph(passing_cand, graph)

        node_id = f"protein:{passing_cand.candidate_id.lower()}"
        assert graph.has_node(node_id)
        assert graph.get_node(node_id)["node_type"] == NodeType.PROTEIN.value
        assert graph.get_node(node_id)["confidence"] == 0.5

        # Check edge
        assert graph.has_edge(node_id, "mol:glucosepane")
        edge_data = graph.get_edge(node_id, "mol:glucosepane")
        assert edge_data["edge_type"] == "DEGRADES"
        assert edge_data["status"] == "HYPOTHESIZED_IN_SILICO"

    def test_gap_detector_state_transition_when_candidate_present(self):
        graph = build_mock_glucosepane_graph()
        chain = CausalChainRegistry().load("glucosepane")

        # Before candidate injection: CRITICAL gap for selective enzyme
        detector = NegativeSpaceDetector(graph)
        gaps_before = detector.detect_gaps(chain)
        enzyme_gap_before = next(g for g in gaps_before if g.causal_node_id == "req:selective_enzyme")
        assert enzyme_gap_before.priority == GapPriority.CRITICAL
        assert enzyme_gap_before.gap_type == "MISSING_MECHANISM"

        # Now inject de novo candidate enzyme
        spec = DeNovoDesignSpec(
            spec_id="SPEC-TEST-03",
            target_name="Glucosepane",
            causal_gap_id="req:selective_enzyme",
            gap_priority="CRITICAL",
            gap_description="Selective glucosepane hydrolase",
            substrate_name="Glucosepane",
            substrate_smiles="C1=CC=C(C=C1)C=O",
            substrate_3d_sdf_path=None,
            substrate_molecular_weight=430.25,
            substrate_formula="C18H34N6O6",
            target_plddt_minimum=80.0,
            target_pocket_volume_angstrom3="500 Å³",
            suggested_catalytic_motifs=["His-Asp-Ser"],
            homologous_scaffolds=[],
            rfdiffusion_all_atom_flags={},
            esm3_prompt_config={},
            proteinmpnn_config={},
        )
        cands = run_generative_pipeline_for_spec(spec, num_variants=1, min_plddt=80.0)
        inject_candidate_into_graph(cands[0], graph)

        # After candidate injection: Re-run detector
        detector_after = NegativeSpaceDetector(graph)
        gaps_after = detector_after.detect_gaps(chain)
        enzyme_gap_after = next(g for g in gaps_after if g.causal_node_id == "req:selective_enzyme")

        # Priority transitions to LOW and gap_type becomes CANDIDATE_PENDING_SYNTHESIS
        assert enzyme_gap_after.priority == GapPriority.LOW
        assert enzyme_gap_after.gap_type == "CANDIDATE_PENDING_SYNTHESIS"

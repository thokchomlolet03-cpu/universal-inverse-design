"""Tests for Layer 3 De Novo Design Spec Compiler and RDKit 3D conformer generation."""

import json
from pathlib import Path
from uid_engine.analysis.design_spec import (
    generate_3d_ligand_conformer,
    calculate_molecular_properties,
    compile_design_spec_for_gap,
    export_spec_json,
    export_spec_markdown,
    compile_all_specs_for_target,
    DeNovoDesignSpec,
)
from uid_engine.graph.builder import build_mock_glucosepane_graph
from uid_engine.analysis.gap_detector import EpistemicGap
from uid_engine.graph.schema import GapPriority


class TestCheminformatics3DConformer:
    """Verify RDKit 3D Euclidean conformer generation and property calculation."""

    def test_generate_3d_sdf_conformer(self, tmp_path):
        smiles = "C1=CC=C(C=C1)C=O"  # Benzaldehyde
        sdf_path = tmp_path / "benzaldehyde_3d.sdf"
        result = generate_3d_ligand_conformer(smiles, sdf_path)

        assert result is not None
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "RDKit" in content
        assert "V2000" in content
        assert "O" in content

    def test_calculate_molecular_properties(self):
        smiles = "CC(=O)O"  # Acetic acid
        mw, formula = calculate_molecular_properties(smiles)
        assert mw == 60.02 or mw == 60.05
        assert formula == "C2H4O2"


class TestDesignSpecCompilation:
    """Verify compilation of EpistemicGaps into Layer 3 De Novo Design Specs."""

    def test_compile_design_spec_structure(self, tmp_path):
        graph = build_mock_glucosepane_graph()
        gap = EpistemicGap(
            gap_id="gap:req:selective_enzyme",
            description="Selective glucosepane hydrolyzing enzyme",
            priority=GapPriority.CRITICAL,
            causal_node_id="req:selective_enzyme",
            gap_type="MISSING_MECHANISM",
            closest_candidates=[],
            downstream_impact=[],
            source_evidence=[],
            suggested_directions=[],
        )

        spec = compile_design_spec_for_gap(gap, graph, target="glucosepane", output_dir=tmp_path)
        assert spec.spec_id == "SPEC-GLUCOSEPANE-REQ-SELECTIVE_ENZYME"
        assert spec.gap_priority == "CRITICAL"
        assert spec.target_plddt_minimum == 85.0
        assert spec.substrate_3d_sdf_path is not None
        assert Path(spec.substrate_3d_sdf_path).exists()

    def test_export_spec_json_and_markdown(self, tmp_path):
        graph = build_mock_glucosepane_graph()
        gap = EpistemicGap(
            gap_id="gap:test",
            description="Test gap",
            priority=GapPriority.HIGH,
            causal_node_id="req:test",
            gap_type="MISSING_MECHANISM",
            closest_candidates=[],
            downstream_impact=[],
            source_evidence=[],
            suggested_directions=[],
        )
        spec = compile_design_spec_for_gap(gap, graph, target="glucosepane", output_dir=tmp_path)

        json_file = tmp_path / "spec.json"
        md_file = tmp_path / "spec.md"

        export_spec_json(spec, json_file)
        export_spec_markdown(spec, md_file)

        assert json_file.exists()
        assert md_file.exists()

        data = json.loads(json_file.read_text(encoding="utf-8"))
        assert data["spec_id"] == spec.spec_id
        assert data["rfdiffusion_all_atom_flags"]["model"] == "RFdiffusion_AllAtom_v1"

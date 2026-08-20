"""Tests for the 4-gate in silico screening and biophysical quality control filters."""

import pytest
from uid_engine.generative.screening import (
    compute_biophysical_properties,
    screen_candidate_sequence,
)


class TestBiophysicalScreening:
    """Test Gate 4 biophysical properties and solubility/aggregation screening."""

    def test_compute_biophysical_properties(self):
        # Soluble hydrophilic test sequence
        seq = "MKTIIALSYIFCLVFA" + "EEDDKK" * 10
        props = compute_biophysical_properties(seq)

        assert props.molecular_weight > 0
        assert 0.0 <= props.isoelectric_point <= 14.0
        assert props.gravy_score < 0.0  # Hydrophilic

    def test_gate_1_plddt_failure(self):
        seq = "M" + "A" * 150
        _, res = screen_candidate_sequence(seq, predicted_plddt=72.5, sc_rmsd=1.1)

        assert res.passed is False
        assert res.gate_1_plddt is False
        assert any("pLDDT" in r for r in res.failure_reasons)

    def test_gate_2_sc_rmsd_failure(self):
        seq = "M" + "A" * 150
        _, res = screen_candidate_sequence(seq, predicted_plddt=91.0, sc_rmsd=2.85)

        assert res.passed is False
        assert res.gate_2_sc_rmsd is False
        assert any("scRMSD" in r for r in res.failure_reasons)

    def test_gate_3_catalytic_mutation_failure(self):
        # Sequence missing His at position 5
        seq = "MAAALAAAAA"
        catalytic_map = {"H5": "H"}
        _, res = screen_candidate_sequence(
            seq,
            predicted_plddt=90.0,
            sc_rmsd=1.0,
            expected_catalytic_residues=catalytic_map,
        )

        assert res.passed is False
        assert res.gate_3_catalytic_retention is False
        assert any("Active site mutation" in r for r in res.failure_reasons)

    def test_gate_4_hydrophobic_aggregation_failure(self):
        # Hyper-hydrophobic poly-leucine sequence (extremely high GRAVY score > 2.0)
        seq = "M" + "L" * 120
        _, res = screen_candidate_sequence(seq, predicted_plddt=92.0, sc_rmsd=1.0)

        assert res.passed is False
        assert res.gate_4_biophysical_solubility is False
        assert any("Hydrophobicity GRAVY" in r for r in res.failure_reasons)

    def test_all_gates_pass(self):
        # Stable, soluble globular sequence (BPTI bovine pancreatic trypsin inhibitor fragment)
        seq = "RPDFCLEPPYTGPCKARIIRYFYNAKAGLCQTFVYGGCRAKRNNFKSAEDCMRTCGGA"
        catalytic_map = {"R1": "R", "D3": "D", "K15": "K"}
        props, res = screen_candidate_sequence(
            seq,
            predicted_plddt=89.5,
            sc_rmsd=1.2,
            expected_catalytic_residues=catalytic_map,
        )

        assert res.passed is True
        assert res.gate_1_plddt is True
        assert res.gate_2_sc_rmsd is True
        assert res.gate_3_catalytic_retention is True
        assert res.gate_4_biophysical_solubility is True
        assert len(res.failure_reasons) == 0

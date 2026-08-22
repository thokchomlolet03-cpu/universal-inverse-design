"""Unit tests for AutoDock Vina molecular docking evaluation (Gate 5)."""

import pytest
from uid_engine.generative.docking_gate import (
    evaluate_molecular_docking,
    generate_flexible_ligand_pdbqt,
    DockingResult,
)


def test_generate_flexible_ligand_pdbqt_glucosepane():
    """Glucosepane SMILES should yield 3D conformer with rotatable bonds."""
    smiles = "C18H34N6O6"  # Glucosepane formula
    # Accurate canonical SMILES for glucosepane core
    glucosepane_smiles = "NC(CO)C(=O)NC(CCCCN1C=C(N=C1)NCCCC(C(=O)O)N)C(=O)O"
    pdb_block, num_rot = generate_flexible_ligand_pdbqt(glucosepane_smiles)
    assert pdb_block is not None
    assert "ATOM" in pdb_block or "HETATM" in pdb_block
    assert num_rot > 0


def test_evaluate_molecular_docking_pass():
    """Standard glucosepane candidate should achieve ΔG <= -8.0 kcal/mol."""
    res = evaluate_molecular_docking(
        substrate_smiles="C18H34N6O6",
        max_binding_energy_threshold=-8.0,
    )
    assert isinstance(res, DockingResult)
    assert res.binding_energy_kcal_mol <= -8.0
    assert res.passed_gate_5 is True
    assert res.num_rotatable_bonds >= 0
    assert "AutoDock Vina ΔG" in res.pose_summary


def test_evaluate_molecular_docking_strict_threshold_failure():
    """Unrealistic threshold (e.g. -20.0 kcal/mol) should fail Gate 5."""
    res = evaluate_molecular_docking(
        substrate_smiles="C18H34N6O6",
        max_binding_energy_threshold=-20.0,
    )
    assert res.passed_gate_5 is False

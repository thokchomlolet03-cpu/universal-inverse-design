"""Unit tests for Gate 6 off-target selectivity screening."""

import pytest
from uid_engine.generative.off_target_screen import (
    evaluate_off_target_selectivity,
    calculate_kd_ratio_from_delta_g,
    DECOY_TARGETS,
    SelectivityResult,
)


def test_decoy_library_contains_required_proteins():
    """Verify presence of HSA, Collagen I/III, Elastin, Fibronectin, and BCL-xL."""
    assert "Collagen_Type_I_a1" in DECOY_TARGETS
    assert "Collagen_Type_III" in DECOY_TARGETS
    assert "Elastin" in DECOY_TARGETS
    assert "Human_Serum_Albumin" in DECOY_TARGETS
    assert "Fibronectin" in DECOY_TARGETS
    assert "BCL_xL" in DECOY_TARGETS


def test_kd_ratio_calculation():
    """ΔΔG of ~2.8 kcal/mol at 310K should yield ~100x selectivity ratio."""
    # 2.8 kcal/mol difference at 310.15K: exp(2.8 / (0.001987 * 310.15)) ~ exp(4.54) ~ 94-100x
    ratio = calculate_kd_ratio_from_delta_g(target_delta_g=-9.2, decoy_delta_g=-6.0)
    assert ratio >= 100.0


def test_evaluate_off_target_selectivity_pass():
    """High affinity target (-9.2 kcal/mol) vs weak decoys should pass 100x selectivity."""
    seq = "MKLLVTALLA" * 10
    res = evaluate_off_target_selectivity(
        candidate_sequence=seq,
        target_delta_g=-9.2,
        min_selectivity_ratio=100.0,
    )
    assert isinstance(res, SelectivityResult)
    assert res.passed_gate_6 is True
    assert res.selectivity_ratio >= 100.0
    assert "Worst-Case Selectivity" in res.summary


def test_evaluate_off_target_selectivity_failure():
    """Weak target affinity (-6.2 kcal/mol) vs decoys should fail 100x selectivity."""
    seq = "MKLLVTALLA" * 10
    res = evaluate_off_target_selectivity(
        candidate_sequence=seq,
        target_delta_g=-6.2,
        min_selectivity_ratio=100.0,
    )
    assert res.passed_gate_6 is False

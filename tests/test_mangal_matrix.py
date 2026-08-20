"""Tests for Project Mangal Matrix & Tensor Engine."""

import pytest
from mangal_engine.matrix.dimensions import (
    ArchetypeLens,
    CoreElement,
    CognitiveOperation,
    ScaleShift,
    ThermodynamicVector,
    InformationState,
    PhilosophicalOperator,
    VectorCoordinate,
    is_heuristic_compatible,
)
from mangal_engine.matrix.tensor import (
    InterrogationTensor,
    MatrixScale,
    SynthesizedInquiry,
)


def test_matrix_dimensions_counts():
    """Verify that every foundational dimension has exactly 10 members."""
    assert len(ArchetypeLens) == 10
    assert len(CoreElement) == 10
    assert len(CognitiveOperation) == 10
    assert len(ScaleShift) == 10
    assert len(ThermodynamicVector) == 10
    assert len(InformationState) == 10
    assert len(PhilosophicalOperator) == 10


def test_tensor_scale_cardinalities():
    """Verify combinatorial sizes across all scale modes."""
    t_1k = InterrogationTensor(MatrixScale.SCALE_1K)
    assert t_1k.total_theoretical_combinations == 1_000

    t_10k = InterrogationTensor(MatrixScale.SCALE_10K)
    assert t_10k.total_theoretical_combinations == 10_000

    t_100k = InterrogationTensor(MatrixScale.SCALE_100K)
    assert t_100k.total_theoretical_combinations == 100_000


def test_coordinate_deterministic_lookup():
    """Verify O(1) index lookup maps back and forth accurately."""
    tensor = InterrogationTensor(MatrixScale.SCALE_10K)

    # First item (index 0)
    c0 = tensor.get_coordinate_by_index(0)
    assert c0.archetype == list(ArchetypeLens)[0]
    assert c0.element == list(CoreElement)[0]
    assert c0.operation == list(CognitiveOperation)[0]
    assert c0.scale == list(ScaleShift)[0]
    assert c0.coordinate_id == "W00-X00-Y00-Z00"

    # Last item (index 9999)
    c_last = tensor.get_coordinate_by_index(9999)
    assert c_last.archetype == list(ArchetypeLens)[9]
    assert c_last.element == list(CoreElement)[9]
    assert c_last.operation == list(CognitiveOperation)[9]
    assert c_last.scale == list(ScaleShift)[9]
    assert c_last.coordinate_id == "W09-X09-Y09-Z09"

    # Out of bounds
    with pytest.raises(IndexError):
        tensor.get_coordinate_by_index(-1)
    with pytest.raises(IndexError):
        tensor.get_coordinate_by_index(10000)


def test_gate1_heuristic_compatibility():
    """Verify pure-Python Gate 1 heuristic ruleset prunes degenerate vectors."""
    # Incompatible: Atomic scale + Sovereign regulator
    incomp = VectorCoordinate(
        archetype=ArchetypeLens.SOVEREIGN,
        element=CoreElement.CORE_ASSET,
        operation=CognitiveOperation.INVERT,
        scale=ScaleShift.ATOMIC,
    )
    assert is_heuristic_compatible(incomp) is False

    # Incompatible: Absolute Zero + Automate
    incomp_zero = VectorCoordinate(
        archetype=ArchetypeLens.THERMODYNAMICIST,
        element=CoreElement.FRICTION_POINT,
        operation=CognitiveOperation.AUTOMATE,
        scale=ScaleShift.ABSOLUTE_ZERO,
    )
    assert is_heuristic_compatible(incomp_zero) is False

    # Compatible: Thermodynamicist + Friction Point + Invert + Infinite Abundance
    comp = VectorCoordinate(
        archetype=ArchetypeLens.THERMODYNAMICIST,
        element=CoreElement.FRICTION_POINT,
        operation=CognitiveOperation.INVERT,
        scale=ScaleShift.INFINITE_ABUNDANCE,
    )
    assert is_heuristic_compatible(comp) is True


def test_inquiry_synthesis():
    """Verify dynamic inquiry prompt generation."""
    tensor = InterrogationTensor(MatrixScale.SCALE_10K)
    coord = VectorCoordinate(
        archetype=ArchetypeLens.ADVERSARY,
        element=CoreElement.FRICTION_POINT,
        operation=CognitiveOperation.INVERT,
        scale=ScaleShift.INFINITE_ABUNDANCE,
    )
    problem = "Arterial collagen glucosepane crosslinking"
    inquiry = tensor.synthesize_inquiry(coord, problem)

    assert isinstance(inquiry, SynthesizedInquiry)
    assert inquiry.coordinate == coord
    assert problem in inquiry.inquiry_text
    assert "Adversary" in inquiry.inquiry_text
    assert inquiry.is_compatible is True


def test_diverse_sampling():
    """Verify stratified diverse sampling returns unique valid coordinates."""
    tensor = InterrogationTensor(MatrixScale.SCALE_10K)
    sample = tensor.sample_diverse_coordinates(count=25, seed=42)

    assert len(sample) == 25
    assert len(set(sample)) == 25  # All unique
    for coord in sample:
        assert is_heuristic_compatible(coord) is True

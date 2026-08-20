"""Tests for Project Mangal Multi-Gate Sieve & Evaluator."""

import pytest
from mangal_engine.interrogator.evaluator import InterrogationEvaluator, MicroSolution
from mangal_engine.interrogator.sieve import InterrogationSieve, ScoredInquiry
from mangal_engine.matrix.dimensions import (
    ArchetypeLens,
    CoreElement,
    CognitiveOperation,
    ScaleShift,
    VectorCoordinate,
)
from mangal_engine.matrix.tensor import InterrogationTensor, MatrixScale


def test_sieve_gate1_rejection():
    """Verify that incompatible coordinates are dropped at Gate 1 with zero score."""
    sieve = InterrogationSieve()
    tensor = InterrogationTensor(MatrixScale.SCALE_10K)

    # Incompatible coordinate
    incomp_coord = VectorCoordinate(
        archetype=ArchetypeLens.SOVEREIGN,
        element=CoreElement.CORE_ASSET,
        operation=CognitiveOperation.INVERT,
        scale=ScaleShift.ATOMIC,
    )
    inquiry = tensor.synthesize_inquiry(incomp_coord, "Test Problem")
    scored = sieve.score_inquiry(inquiry)

    assert scored.gate1_passed is False
    assert scored.total_impact_score == 0.0


def test_sieve_ranking_and_extraction():
    """Verify that Gate 2/3 correctly scores and ranks high-leverage inquiries."""
    sieve = InterrogationSieve()
    tensor = InterrogationTensor(MatrixScale.SCALE_10K)

    coords = tensor.sample_diverse_coordinates(count=30, seed=123)
    inquiries = [tensor.synthesize_inquiry(c, "Cellular senescence SASP suppression") for c in coords]

    top_scored = sieve.sieve_inquiries(inquiries, top_k=10)

    assert len(top_scored) <= 10
    assert all(s.gate1_passed for s in top_scored)
    assert all(s.total_impact_score > 0.0 for s in top_scored)

    # Verify descending sort
    scores = [s.total_impact_score for s in top_scored]
    assert scores == sorted(scores, reverse=True)


def test_evaluator_micro_solutions():
    """Verify that InterrogationEvaluator generates structured micro-solutions."""
    sieve = InterrogationSieve()
    evaluator = InterrogationEvaluator()
    tensor = InterrogationTensor(MatrixScale.SCALE_10K)

    coord = VectorCoordinate(
        archetype=ArchetypeLens.THERMODYNAMICIST,
        element=CoreElement.FRICTION_POINT,
        operation=CognitiveOperation.INVERT,
        scale=ScaleShift.INFINITE_ABUNDANCE,
    )
    inquiry = tensor.synthesize_inquiry(coord, "Glucosepane crosslinking")
    scored = sieve.score_inquiry(inquiry)

    solution = evaluator.evaluate_inquiry(scored)

    assert isinstance(solution, MicroSolution)
    assert solution.inquiry == scored
    assert len(solution.deduction_text) > 20
    assert len(solution.invariant_candidate) > 10
    assert solution.paradigm_tag in ["INVERSION_PARADIGM", "STRUCTURAL_PARADIGM", "THERMODYNAMIC_PARADIGM", "AUTOMATION_PARADIGM", "ELIMINATION_PARADIGM"]

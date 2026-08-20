"""Tests for Project Mangal Axiomatic Challenge Protocol."""

import pytest
from mangal_engine.distiller.axiom_distiller import DistilledAxiom
from mangal_engine.mutation.axiomatic_challenge import (
    AxiomaticChallengeEngine,
    ChallengedHypothesis,
    MutationVector,
)


def test_axiomatic_challenge_4_vectors():
    """Verify that all 4 mutation vectors produce concrete breakthrough hypotheses."""
    engine = AxiomaticChallengeEngine()
    axiom = DistilledAxiom(
        axiom_id="AXIOM-GLUCOSEPANE-01",
        target_problem="Glucosepane crosslink repair",
        core_axiom_statement="Extracellular stiffness is governed by lack of catalytic cleavage for imidazole crosslinks.",
        root_cause_category="STRUCTURAL",
        supporting_cluster_count=5,
        key_invariants=["Heterocyclic imidazole core", "Collagen fibril spacing"],
        confidence_score=0.92,
        summary_rationale="Tested across 10,000 vectors.",
    )

    hypotheses = engine.challenge_axiom(axiom)

    assert len(hypotheses) == 4
    vectors_present = {h.vector for h in hypotheses}
    assert MutationVector.AXIOM_INVALIDATION in vectors_present
    assert MutationVector.DIMENSIONAL_EXPANSION in vectors_present
    assert MutationVector.CONSTRAINT_SUBSTITUTION in vectors_present
    assert MutationVector.SYMBIOTIC_SYNTHESIS in vectors_present

    for h in hypotheses:
        assert isinstance(h, ChallengedHypothesis)
        assert len(h.breakthrough_mechanism) > 20
        assert h.required_prerequisite_id.startswith("req:")
        assert h.confidence >= 0.70

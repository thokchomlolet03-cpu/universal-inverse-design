"""Tests for Project Mangal Semantic Clusterer & Axiom Distiller."""

import pytest
from mangal_engine.distiller.axiom_distiller import AxiomDistiller, DistilledAxiom
from mangal_engine.distiller.clusterer import ConceptualCluster, SemanticClusterer
from mangal_engine.interrogator.evaluator import InterrogationEvaluator
from mangal_engine.interrogator.sieve import InterrogationSieve
from mangal_engine.matrix.tensor import InterrogationTensor, MatrixScale


def test_semantic_clustering():
    """Verify that micro-solutions are clustered into coherent conceptual paradigms."""
    tensor = InterrogationTensor(MatrixScale.SCALE_10K)
    sieve = InterrogationSieve()
    evaluator = InterrogationEvaluator()
    clusterer = SemanticClusterer()

    coords = tensor.sample_diverse_coordinates(count=30, seed=99)
    inquiries = [tensor.synthesize_inquiry(c, "Extracellular matrix collagen crosslinking") for c in coords]
    scored = sieve.sieve_inquiries(inquiries, top_k=20)
    solutions = evaluator.evaluate_batch(scored)

    clusters = clusterer.cluster_solutions(solutions)

    assert len(clusters) > 0
    for cluster in clusters:
        assert isinstance(cluster, ConceptualCluster)
        assert cluster.member_count > 0
        assert len(cluster.centroid_terms) > 0
        assert len(cluster.dominant_invariant) > 0
        assert cluster.cohesion_score >= 0.70


def test_axiom_distillation():
    """Verify that AxiomDistiller extracts an irreducible invariant root cause."""
    tensor = InterrogationTensor(MatrixScale.SCALE_10K)
    sieve = InterrogationSieve()
    evaluator = InterrogationEvaluator()
    clusterer = SemanticClusterer()
    distiller = AxiomDistiller()

    problem = "Arterial collagen glucosepane crosslinking"
    coords = tensor.sample_diverse_coordinates(count=40, seed=77)
    inquiries = [tensor.synthesize_inquiry(c, problem) for c in coords]
    scored = sieve.sieve_inquiries(inquiries, top_k=20)
    solutions = evaluator.evaluate_batch(scored)
    clusters = clusterer.cluster_solutions(solutions)

    axiom = distiller.distill_axiom(problem, clusters)

    assert isinstance(axiom, DistilledAxiom)
    assert axiom.axiom_id.startswith("AXIOM-")
    assert len(axiom.core_axiom_statement) > 30
    assert "crosslink" in axiom.core_axiom_statement.lower() or "glucosepane" in axiom.core_axiom_statement.lower()
    assert axiom.confidence_score >= 0.80
    assert len(axiom.key_invariants) > 0

"""End-to-End Integration Tests: Project Mangal -> Universal Inverse Design Engine."""

import tempfile
from pathlib import Path

import pytest
from mangal_engine.compiler.chain_writer import ChainWriter
from mangal_engine.distiller.axiom_distiller import AxiomDistiller
from mangal_engine.distiller.clusterer import SemanticClusterer
from mangal_engine.interrogator.evaluator import InterrogationEvaluator
from mangal_engine.interrogator.sieve import InterrogationSieve
from mangal_engine.matrix.tensor import InterrogationTensor, MatrixScale
from mangal_engine.mutation.axiomatic_challenge import AxiomaticChallengeEngine

from uid_engine.analysis.gap_detector import NegativeSpaceDetector
from uid_engine.chains.registry import CausalChainRegistry
from uid_engine.graph.builder import EpistemicGraph
from uid_engine.graph.schema import GapPriority


def test_mangal_to_uid_autonomous_loop():
    """Verify that Mangal autonomously generates a causal chain that drives UID Negative Space Detection."""
    target_problem = "Vascular Collagen Crosslinking"

    # Step 1: Mangal Interrogation Matrix
    tensor = InterrogationTensor(MatrixScale.SCALE_10K)
    sieve = InterrogationSieve()
    evaluator = InterrogationEvaluator()
    clusterer = SemanticClusterer()
    distiller = AxiomDistiller()
    challenge_engine = AxiomaticChallengeEngine()
    writer = ChainWriter()

    coords = tensor.sample_diverse_coordinates(count=30, seed=42)
    inquiries = [tensor.synthesize_inquiry(c, target_problem) for c in coords]
    scored = sieve.sieve_inquiries(inquiries, top_k=15)
    solutions = evaluator.evaluate_batch(scored)

    # Step 2: Topological Clustering & Axiom Distillation
    clusters = clusterer.cluster_solutions(solutions)
    axiom = distiller.distill_axiom(target_problem, clusters)
    assert axiom.confidence_score >= 0.80

    # Step 3: 4-Vector Axiomatic Challenge
    hypotheses = challenge_engine.challenge_axiom(axiom)
    assert len(hypotheses) == 4

    # Step 4: Autonomous Causal Chain Compilation
    with tempfile.TemporaryDirectory() as tmpdir:
        result = writer.compile_chain(target_problem, axiom, hypotheses, output_dir=tmpdir)
        assert result.is_valid is True
        assert result.file_path.exists()

        # Step 5: UID Engine Consumption
        registry = CausalChainRegistry()
        causal_tree = registry.load_from_path(result.file_path)

        # Step 6: Negative Space Detection on Empty Graph
        graph = EpistemicGraph()
        detector = NegativeSpaceDetector(graph)
        gaps = detector.detect_gaps(causal_tree)

        # Assertions on gaps discovered
        assert len(gaps) > 0
        critical_gaps = [g for g in gaps if g.priority == GapPriority.CRITICAL]
        assert len(critical_gaps) >= 1
        assert "MISSING_MECHANISM" in critical_gaps[0].gap_type or "UNPROVEN_HYPOTHESIS" in critical_gaps[0].gap_type
        assert "selective_catalyst" in critical_gaps[0].causal_node_id or "selective_catalyst" in str(critical_gaps[0].suggested_directions)

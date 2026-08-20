"""Tests for Project Mangal ChainWriter & YAML Schema Validation."""

import tempfile
from pathlib import Path

import pytest
from mangal_engine.compiler.chain_writer import ChainWriter, CompiledChainResult
from mangal_engine.distiller.axiom_distiller import DistilledAxiom
from mangal_engine.mutation.axiomatic_challenge import AxiomaticChallengeEngine
from uid_engine.chains.registry import CausalChainRegistry


def test_chain_writer_yaml_schema_validity():
    """Verify that ChainWriter produces a 100% valid YAML chain accepted by CausalChainRegistry."""
    distiller_axiom = DistilledAxiom(
        axiom_id="AXIOM-LIPOFUSCIN-01",
        target_problem="Lysosomal lipofuscin accumulation",
        core_axiom_statement="Intracellular junk accumulation is governed by non-degradable oxidized protein aggregates in lysosomes.",
        root_cause_category="STRUCTURAL",
        supporting_cluster_count=4,
        key_invariants=["7-ketocholesterol", "Lipofuscin autofluorescence"],
        confidence_score=0.90,
        summary_rationale="Tested across 10,000 vectors.",
    )

    engine = AxiomaticChallengeEngine()
    hypotheses = engine.challenge_axiom(distiller_axiom)

    with tempfile.TemporaryDirectory() as tmpdir:
        writer = ChainWriter()
        result = writer.compile_chain(
            seed_problem="Lysosomal Lipofuscin Accumulation",
            axiom=distiller_axiom,
            hypotheses=hypotheses,
            output_dir=tmpdir,
        )

        assert isinstance(result, CompiledChainResult)
        assert result.is_valid is True
        assert result.file_path.exists()
        assert result.node_count >= 8

        # Explicitly parse and validate with UID CausalChainRegistry
        registry = CausalChainRegistry()
        causal_root = registry.load_from_path(result.file_path)

        assert causal_root.node_id.startswith("goal:lysosomal_lipofuscin_accumulation")
        assert len(causal_root.children) >= 3

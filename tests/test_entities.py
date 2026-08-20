"""Tests for heuristic entity extraction — correctness and deduplication."""

import pytest

from uid_engine.graph.entities import extract_heuristic_fallback


class TestHeuristicFallback:
    """Validate the deterministic heuristic extractor."""

    def test_extracts_glucosepane_and_collagen(self, sample_paper):
        result = extract_heuristic_fallback(
            sample_paper["abstract"], sample_paper["pmid"], sample_paper["title"]
        )
        entity_ids = [e["entity_id"] for e in result["entities"]]
        assert "mol:glucosepane" in entity_ids
        assert "mol:collagen" in entity_ids

    def test_extracts_tissue_from_abstract(self, sample_paper):
        result = extract_heuristic_fallback(
            sample_paper["abstract"], sample_paper["pmid"], sample_paper["title"]
        )
        entity_ids = [e["entity_id"] for e in result["entities"]]
        assert "tissue:arteries" in entity_ids

    def test_crosslinks_edge_detected(self, sample_paper):
        result = extract_heuristic_fallback(
            sample_paper["abstract"], sample_paper["pmid"], sample_paper["title"]
        )
        crosslink_edges = [
            e for e in result["causal_edges"]
            if e["edge_type"] == "CROSSLINKS"
        ]
        assert len(crosslink_edges) == 1
        assert crosslink_edges[0]["source_id"] == "mol:glucosepane"
        assert crosslink_edges[0]["target_id"] == "mol:collagen"

    def test_causes_damage_edge_detected(self, sample_paper):
        result = extract_heuristic_fallback(
            sample_paper["abstract"], sample_paper["pmid"], sample_paper["title"]
        )
        damage_edges = [
            e for e in result["causal_edges"]
            if e["edge_type"] == "CAUSES_DAMAGE"
        ]
        assert len(damage_edges) >= 1

    def test_aminoguanidine_extracted(self, sample_paper):
        """The sample abstract mentions aminoguanidine."""
        result = extract_heuristic_fallback(
            sample_paper["abstract"], sample_paper["pmid"], sample_paper["title"]
        )
        entity_ids = [e["entity_id"] for e in result["entities"]]
        assert "mol:aminoguanidine" in entity_ids


class TestHeuristicDedup:
    """Verify that duplicate entity IDs are not produced."""

    def test_no_duplicate_tissue_ids(self):
        """An abstract mentioning 'artery' AND 'arterial' must not produce
        two separate tissue:arteries entities."""
        abstract = (
            "Glucosepane accumulates in the artery wall. "
            "Arterial collagen stiffens due to crosslinking."
        )
        result = extract_heuristic_fallback(abstract, "99999", "")
        entity_ids = [e["entity_id"] for e in result["entities"]]

        # Count occurrences of tissue:arteries
        count = entity_ids.count("tissue:arteries")
        assert count == 1, f"tissue:arteries appeared {count} times — dedup failed"

    def test_no_duplicate_tissue_ids_kidney(self):
        """'kidney' and 'renal' both map to tissue:kidneys."""
        abstract = "Glucosepane in kidney tissue. Renal damage is observed."
        result = extract_heuristic_fallback(abstract, "88888", "")
        entity_ids = [e["entity_id"] for e in result["entities"]]
        count = entity_ids.count("tissue:kidneys")
        assert count == 1

    def test_no_duplicate_heart(self):
        """'heart' and 'myocardium' both map to tissue:heart."""
        abstract = "Glucosepane in heart muscle. Myocardium shows stiffness."
        result = extract_heuristic_fallback(abstract, "77777", "")
        entity_ids = [e["entity_id"] for e in result["entities"]]
        count = entity_ids.count("tissue:heart")
        assert count == 1


class TestHeuristicEdgeCases:
    """Edge cases and empty inputs."""

    def test_empty_abstract_returns_empty(self):
        result = extract_heuristic_fallback("", "00000", "")
        assert result["entities"] == []
        assert result["causal_edges"] == []

    def test_irrelevant_abstract_returns_empty(self):
        result = extract_heuristic_fallback(
            "This paper discusses climate change in the Arctic.",
            "11111", "Climate study"
        )
        assert result["entities"] == []
        assert result["causal_edges"] == []

    def test_title_only_extraction(self):
        """Even without abstract, title keywords should trigger extraction."""
        result = extract_heuristic_fallback(
            "", "22222", "Glucosepane crosslinks in collagen"
        )
        entity_ids = [e["entity_id"] for e in result["entities"]]
        assert "mol:glucosepane" in entity_ids
        assert "mol:collagen" in entity_ids

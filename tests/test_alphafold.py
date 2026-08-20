"""Tests for AlphaFold DB REST ingestion client and structural metadata parsing."""

import json
import pytest
from unittest.mock import patch, MagicMock

from uid_engine.ingest.alphafold import (
    parse_alphafold_entry,
    fetch_alphafold_prediction,
    fetch_alphafold_batch,
    save_alphafold_data,
    load_alphafold_data,
    ingest_alphafold,
)
from uid_engine.graph.builder import EpistemicGraph
from uid_engine.graph.schema import NodeData, NodeType
from uid_engine.cli import _add_alphafold_to_graph


SAMPLE_ALPHAFOLD_RAW_ENTRY = {
    "entryId": "AF-P10415-F1",
    "gene": "BCL2",
    "uniprotAccession": "P10415",
    "uniprotId": "BCL2_HUMAN",
    "uniprotDescription": "Apoptosis regulator Bcl-2",
    "taxId": 9606,
    "organismScientificName": "Homo sapiens",
    "uniprotStart": 1,
    "uniprotEnd": 239,
    "uniprotSequence": "MAHAGRTGYDNREIVMKYIHYKLSQRGYEWDAGDVGAAPPGAAPAPGIFSSQPGHTPHPAASRDPVARTSPLQTPAAPGAAAGPALSPVPPVVHLTLRQAGDDFSRRYRRDFAEMSSQLHLTPFTARGRFATVVEELFRDGVNWGRIVAFFEFGGVMCVESVNREMSPLVDNIALWMTEYLNRHLHTWIQDNGGWDAFVELYGPSMRPLFDFSWLSLKTLLSLALVGACITLGAYLGHK",
    "modelCreatedDate": "2022-06-01",
    "latestVersion": 4,
    "allVersions": [1, 2, 3, 4],
    "isReviewed": True,
    "isReferenceProteome": True,
    "cifUrl": "https://alphafold.ebi.ac.uk/files/AF-P10415-F1-model_v4.cif",
    "bcifUrl": "https://alphafold.ebi.ac.uk/files/AF-P10415-F1-model_v4.bcif",
    "pdbUrl": "https://alphafold.ebi.ac.uk/files/AF-P10415-F1-model_v4.pdb",
    "paeDocUrl": "https://alphafold.ebi.ac.uk/files/AF-P10415-F1-predicted_aligned_error_v4.json",
    "paeImageUrl": "https://alphafold.ebi.ac.uk/files/AF-P10415-F1-pae.png",
    "globalMetricValue": 88.45,
}


class TestAlphaFoldParsing:
    """Test parse_alphafold_entry pLDDT tier classification and metadata extraction."""

    def test_parse_entry_confident_tier(self):
        parsed = parse_alphafold_entry(SAMPLE_ALPHAFOLD_RAW_ENTRY)
        assert parsed["entry_id"] == "AF-P10415-F1"
        assert parsed["uniprot_accession"] == "P10415"
        assert parsed["mean_plddt"] == 88.45
        assert parsed["confidence_category"] == "CONFIDENT"
        assert parsed["pdb_url"].endswith(".pdb")
        assert parsed["cif_url"].endswith(".cif")
        assert parsed["sequence_end"] == 239

    def test_plddt_very_high_tier(self):
        raw = dict(SAMPLE_ALPHAFOLD_RAW_ENTRY, globalMetricValue=94.2)
        parsed = parse_alphafold_entry(raw)
        assert parsed["confidence_category"] == "VERY_HIGH"

    def test_plddt_low_tier(self):
        raw = dict(SAMPLE_ALPHAFOLD_RAW_ENTRY, globalMetricValue=58.1)
        parsed = parse_alphafold_entry(raw)
        assert parsed["confidence_category"] == "LOW"

    def test_plddt_very_low_tier(self):
        raw = dict(SAMPLE_ALPHAFOLD_RAW_ENTRY, globalMetricValue=42.0)
        parsed = parse_alphafold_entry(raw)
        assert parsed["confidence_category"] == "VERY_LOW"


class TestAlphaFoldFetch:
    """Test API prediction fetching with mocked HTTP responses."""

    @patch("uid_engine.ingest.alphafold.retry_request")
    def test_fetch_prediction_success(self, mock_retry):
        mock_response = MagicMock()
        mock_response.json.return_value = [SAMPLE_ALPHAFOLD_RAW_ENTRY]
        mock_retry.return_value = mock_response

        res = fetch_alphafold_prediction("P10415")
        assert res is not None
        assert res["uniprot_accession"] == "P10415"
        assert res["entry_id"] == "AF-P10415-F1"

    @patch("uid_engine.ingest.alphafold.retry_request")
    def test_fetch_prediction_empty_returns_none(self, mock_retry):
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_retry.return_value = mock_response

        res = fetch_alphafold_prediction("UNKNOWN_ACC")
        assert res is None

    @patch("uid_engine.ingest.alphafold.fetch_alphafold_prediction")
    def test_fetch_batch(self, mock_fetch):
        mock_fetch.return_value = parse_alphafold_entry(SAMPLE_ALPHAFOLD_RAW_ENTRY)
        results = fetch_alphafold_batch(["P10415", "P10415"], rate_limit_delay=0.0)

        # Deduplicates accessions
        assert len(results) == 1
        assert results[0]["uniprot_accession"] == "P10415"


class TestAlphaFoldPersistence:
    """Test disk saving and loading."""

    def test_save_and_load_round_trip(self, tmp_path):
        from uid_engine import config
        original_raw = config.RAW_DATA_DIR
        try:
            config.RAW_DATA_DIR = tmp_path
            data = [parse_alphafold_entry(SAMPLE_ALPHAFOLD_RAW_ENTRY)]
            saved_path = save_alphafold_data(data, "test_target")
            assert saved_path.exists()

            loaded = load_alphafold_data("test_target")
            assert len(loaded) == 1
            assert loaded[0]["entry_id"] == "AF-P10415-F1"
            assert loaded[0]["mean_plddt"] == 88.45
        finally:
            config.RAW_DATA_DIR = original_raw


class TestAlphaFoldGraphEnrichment:
    """Test enriching epistemic graph protein nodes with AlphaFold data."""

    def test_add_alphafold_to_graph(self, tmp_path):
        from uid_engine import config
        original_raw = config.RAW_DATA_DIR
        try:
            config.RAW_DATA_DIR = tmp_path
            data = [parse_alphafold_entry(SAMPLE_ALPHAFOLD_RAW_ENTRY)]
            save_alphafold_data(data, "senescent_cells")

            # Create graph with matching protein node
            graph = EpistemicGraph()
            graph.add_node(NodeData(
                node_id="protein:P10415",
                node_type=NodeType.PROTEIN,
                name="Bcl-2",
                description="Apoptosis regulator Bcl-2",
                source="UniProt:P10415",
                confidence=1.0,
            ))

            _add_alphafold_to_graph(graph, "senescent_cells")

            node_data = graph.get_node("protein:P10415")
            assert node_data.get("has_3d_structure") is True
            assert node_data.get("alphafold_plddt") == 88.45
            assert node_data.get("alphafold_confidence") == "CONFIDENT"
            assert node_data.get("alphafold_pdb_url").endswith(".pdb")
            assert node_data.get("alphafold_entry_id") == "AF-P10415-F1"
        finally:
            config.RAW_DATA_DIR = original_raw

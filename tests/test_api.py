"""Integration tests for the FastAPI serverless API layer."""

from fastapi.testclient import TestClient
import pytest

from uid_engine.api.main import app

client = TestClient(app)


def test_health_check():
    """Verify health probe returns 200 OK and version info."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.7.0"
    assert "Cloud Run" in data["deployment_tier"]


def test_get_graph_topology():
    """Verify topology endpoint returns nodes and edges in Cytoscape format."""
    response = client.get("/api/v1/graph/topology?target=glucosepane")
    assert response.status_code == 200
    data = response.json()
    assert data["target"] == "glucosepane"
    assert data["total_nodes"] > 0
    assert "elements" in data
    assert "nodes" in data["elements"]


def test_list_candidates():
    """Verify candidates list endpoint returns QC-passing candidates."""
    response = client.get("/api/v1/candidates")
    assert response.status_code == 200
    data = response.json()
    assert data["total_candidates"] >= 1
    cand = data["candidates"][0]
    assert cand["candidate_id"] == "CAND-TEST-03"
    assert cand["plddt"] >= 80.0
    assert cand["vina_delta_g"] <= -8.0


def test_get_candidate_details():
    """Verify candidate detail endpoint returns full biophysical properties."""
    response = client.get("/api/v1/candidates/CAND-TEST-03")
    assert response.status_code == 200
    data = response.json()
    assert data["candidate_id"] == "CAND-TEST-03"
    assert "biophysical_properties" in data
    assert "screening_result" in data


def test_get_candidate_pdb():
    """Verify PDB endpoint returns 3D atomic coordinates."""
    response = client.get("/api/v1/candidates/CAND-TEST-03/pdb")
    assert response.status_code == 200
    text = response.text
    assert "HEADER" in text
    assert "ATOM" in text
    assert "END" in text


def test_interrogate_tensor():
    """Verify 4D tensor real-time interrogation returns inquiry and anomaly/leverage scores."""
    payload = {
        "archetype_w": 0,
        "element_x": 0,
        "operation_y": 0,
        "scale_z": 0,
        "problem": "Extracellular collagen crosslinking",
    }
    response = client.post("/api/v1/tensor/interrogate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["coordinates"] == "[0, 0, 0, 0]"
    assert data["anomaly_score"] > 0
    assert data["leverage_score"] > 0
    assert "synthesized_inquiry" in data


def test_get_twist_order():
    """Verify Twist order endpoint returns E. coli BL21 construct and cleavage details."""
    response = client.get("/api/v1/synthesis/CAND-TEST-03/twist-order")
    assert response.status_code == 200
    data = response.json()
    assert data["host_expression_system"] == "E. coli BL21(DE3)"
    assert data["vector"] == "pET-28a(+)"
    assert "CATCACCATCACCATCAC" in data["purification_tag"]
    assert "ENLYFQG" in data["cleavage_scar"]

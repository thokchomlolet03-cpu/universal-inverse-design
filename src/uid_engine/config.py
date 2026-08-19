"""Central configuration for the Universal Inverse Design Engine."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

# ─── Project Paths ──────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / os.getenv("DATA_DIR", "data")
RAW_DATA_DIR = DATA_DIR / "raw"
GRAPHS_DIR = DATA_DIR / "graphs"
REPORTS_DIR = PROJECT_ROOT / os.getenv("REPORTS_DIR", "reports")

# Ensure directories exist
for d in [RAW_DATA_DIR, GRAPHS_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─── API Configuration ──────────────────────────────────────────────────────────

# NCBI / PubMed — Use a dedicated project email, NOT personal
NCBI_EMAIL = os.getenv("NCBI_EMAIL", "uid-engine-ingest@gmail.com")
NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")
NCBI_RATE_LIMIT = 3  # requests per second (10 with API key)

# UniProt
UNIPROT_BASE_URL = "https://rest.uniprot.org"

# KEGG
KEGG_BASE_URL = "https://rest.kegg.jp"

# ChEMBL
CHEMBL_BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"

# ─── LLM Configuration ──────────────────────────────────────────────────────────

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# ─── Ingestion Limits ───────────────────────────────────────────────────────────

# Maximum number of papers to ingest per target (keep small for MVP)
MAX_PAPERS = int(os.getenv("MAX_PAPERS", "500"))

# ─── Graph Configuration ────────────────────────────────────────────────────────

# Default graph file name
DEFAULT_GRAPH_FILE = "glucosepane_epistemic_graph.graphml"

# Confidence score thresholds
CONFIDENCE_CURATED_DB = 1.0       # Data from curated databases (UniProt, KEGG)
CONFIDENCE_STRUCTURED_DB = 0.8    # Data from structured sources (ChEMBL bioactivity)
CONFIDENCE_LLM_EXTRACTION = 0.5   # Data extracted by LLM from abstracts
CONFIDENCE_SINGLE_PAPER = 0.3     # Single unreplicated paper finding

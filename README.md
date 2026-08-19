# Universal Inverse Design Engine

**Mission:** Build an epistemic engine that identifies what humanity does *not* know — the precise missing scientific unknowns (Negative Space) — preventing us from solving biological aging.

**Benchmark #1:** Glucosepane crosslink repair — the most neglected of the 7 SENS aging damage categories.

## How It Works

```
Ingest Scientific Data → Build Causal Knowledge Graph → Detect Epistemic Gaps → Generate Gap Report
```

The engine does NOT summarize what is known. It finds what is **missing**.

## Quick Start

```bash
# Install dependencies
pip install -e .

# Copy and configure environment
cp .env.example .env

# Run the full pipeline
uid ingest --target glucosepane
uid build-graph
uid detect-gaps
uid report
```

## Architecture

- **Data Ingestion** — PubMed, UniProt, KEGG, ChEMBL
- **Knowledge Graph** — NetworkX-based causal graph with confidence-scored edges
- **Negative Space Detector** — Causal chain inversion & topological gap finding
- **Gap Reporter** — Structured Markdown reports of missing scientific unknowns

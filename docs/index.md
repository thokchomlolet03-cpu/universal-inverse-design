# Universal Inverse Design Engine

<div class="grid cards" markdown>

-   :material-dna: **Mission**

    ---

    Build an epistemic engine that identifies what humanity does **not** know —
    the precise missing scientific unknowns (*Negative Space*) — preventing us
    from solving biological aging.

-   :material-chart-timeline-variant: **Benchmark #1**

    ---

    **Glucosepane crosslink repair** — the most neglected of the 7 SENS aging
    damage categories and the hardest molecular engineering problem in longevity.

-   :material-robot: **What it does**

    ---

    The engine does **NOT** summarize what is known. It finds what is
    **missing** — and then generates *de novo* molecular candidates to fill
    those gaps.

-   :material-github: **Open Source**

    ---

    [:octicons-arrow-right-24: View on GitHub](https://github.com/thokchomlolet03-cpu/universal-inverse-design)

</div>

---

## The Inverse Design Pipeline

```
Ingest Scientific Data
        │
        ▼
Build Causal Knowledge Graph (NetworkX)
        │
        ▼
Detect Epistemic Gaps (Topological Inversion)
        │
        ▼
Generate Gap Report  ──►  Layer 3: De Novo Spec Compiler
        │
        ▼
RFdiffusion / ESM-3 / ProteinMPNN Generative Inference
        │
        ▼
4-Gate In Silico QC Screening (pLDDT ≥ 80, scRMSD ≤ 2.0 Å)
        │
        ▼
Graph Loop Closure → HYPOTHESIZED candidate node injected
```

!!! abstract "Core Thesis"
    Contemporary drug discovery operates on a **forward-search heuristic**: screen millions of candidates hoping to stumble upon a functional interaction. The Universal Inverse Design Engine replaces this with **Inverse Causal Mapping** — starting from the desired physiological outcome and working backward to find the precise molecular lever that is missing.

---

## Quick Start

```bash
# Install the engine
pip install -e .

# Copy and configure environment
cp .env.example .env

# Run the full pipeline
uid ingest --target glucosepane
uid build-graph
uid detect-gaps
uid report

# Generate de novo candidates (Phase H)
uid generate-candidates --target glucosepane
uid screen-candidates --target glucosepane --min-plddt 80.0
uid visualize --target glucosepane
```

---

## System Architecture Overview

| Layer | Component | Description |
|-------|-----------|-------------|
| **Layer 0** | Data Ingesters | PubMed, UniProt, KEGG, ChEMBL API pipelines |
| **Layer 1** | Epistemic Graph | NetworkX causal graph, confidence-scored edges |
| **Layer 2** | Gap Detector | Causal chain inversion & topological gap finding |
| **Layer 3** | Spec Compiler | RDKit `ETKDGv3` + `MMFF94` 3D conformer generation |
| **Layer 4** | Generative Engine | ESM-3 / RFdiffusion / ProteinMPNN orchestrator |
| **Layer 5** | QC Screening | 4-gate filter: pLDDT, scRMSD, catalytic geometry, solubility |
| **Layer 6** | Loop Closure | Injects `HYPOTHESIZED` candidates back into the graph |

---

## Engine Status

| Metric | Value |
|--------|-------|
| Test Suite | 125/125 passing |
| Knowledge Graph Nodes | Dynamic (PubMed + UniProt) |
| Target Benchmark | Glucosepane (GlycoSENS) |
| Generative Models | ESM-3, ProteinMPNN |
| QC Thresholds | pLDDT ≥ 80.0, scRMSD ≤ 2.0 Å |
| Engine Version | v0.6.0 |

---

## Documents

<div class="grid cards" markdown>

-   :material-microscope: **Deep Technical Analysis**

    ---

    *Universal Inverse Design Engine: A Deep Technical Analysis of the Autonomous Biomedical Discovery System*

    [:octicons-arrow-right-24: Read Full Analysis](blog/03_deep_technical_analysis.md)

-   :material-file-document: **Engineering Manifesto**

    ---

    *Inverse Biology: Why Aging Is an Information Failure and How We Mapped
    the Negative Space of Glucosepane*

    [:octicons-arrow-right-24: Read the Manifesto](blog/02_engineering_manifesto.md)

-   :material-sitemap: **System Architecture**

    ---

    *The Epistemic Conductor: System Architecture and Mathematical Foundations
    of the Universal Inverse Design Engine*

    [:octicons-arrow-right-24: Read the Architecture Spec](blog/01_system_architecture.md)

</div>

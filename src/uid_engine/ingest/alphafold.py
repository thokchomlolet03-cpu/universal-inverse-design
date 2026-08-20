"""AlphaFold DB REST API client — Fetches 3D structural predictions and pLDDT scores.

Integrates structural biology data into the Epistemic Knowledge Graph by querying
the AlphaFold Protein Structure Database (EMBL-EBI / DeepMind).

For every protein/enzyme identified in the epistemic graph, this client:
1. Retrieves predicted 3D coordinate URLs (PDB, mmCIF).
2. Extracts per-residue and global confidence metrics (mean pLDDT: 0-100).
3. Classifies structural confidence (VERY_HIGH >= 90, CONFIDENT >= 70, LOW >= 50, VERY_LOW < 50).
4. Links structural data to UniProt accession IDs.

API Documentation: https://alphafold.ebi.ac.uk/api-docs
"""

import json
import time
from pathlib import Path
from typing import Optional

import requests
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from uid_engine import config
from uid_engine.utils.retry import retry_request

console = Console()

BASE_URL = getattr(config, "ALPHAFOLD_BASE_URL", "https://alphafold.ebi.ac.uk/api")


# ─── Core API Functions ──────────────────────────────────────────────────────────

def fetch_alphafold_prediction(uniprot_accession: str) -> Optional[dict]:
    """Fetch AlphaFold structural prediction for a single UniProt accession.

    Args:
        uniprot_accession: UniProt primary accession (e.g., "P10415" for BCL2).

    Returns:
        Structured dictionary with model metadata and pLDDT scores, or None if not found.
    """
    url = f"{BASE_URL}/prediction/{uniprot_accession.strip()}"

    try:
        response = retry_request("GET", url, timeout=30)
        data = response.json()
        if not data or not isinstance(data, list):
            return None

        # Take primary/first prediction model
        raw_model = data[0]
        return parse_alphafold_entry(raw_model)

    except requests.exceptions.RequestException as e:
        console.print(f"[dim]⚠ AlphaFold prediction lookup failed for {uniprot_accession}: {e}[/dim]")
        return None
    except (ValueError, KeyError, IndexError) as e:
        console.print(f"[dim]⚠ Failed to parse AlphaFold response for {uniprot_accession}: {e}[/dim]")
        return None


def parse_alphafold_entry(model: dict) -> dict:
    """Parse raw AlphaFold API model JSON into clean structured metadata.

    Calculates canonical pLDDT confidence tier:
      - VERY_HIGH (pLDDT >= 90): High accuracy for side-chains & catalytic geometry
      - CONFIDENT (70 <= pLDDT < 90): Reliable backbone conformation
      - LOW (50 <= pLDDT < 70): Low confidence / flexible loops
      - VERY_LOW (pLDDT < 50): Unstructured / intrinsically disordered region
    """
    global_plddt = float(model.get("globalMetricValue", 0.0))

    if global_plddt >= 90.0:
        confidence_category = "VERY_HIGH"
    elif global_plddt >= 70.0:
        confidence_category = "CONFIDENT"
    elif global_plddt >= 50.0:
        confidence_category = "LOW"
    else:
        confidence_category = "VERY_LOW"

    return {
        "entry_id": model.get("entryId", ""),
        "uniprot_accession": model.get("uniprotAccession", ""),
        "uniprot_id": model.get("uniprotId", ""),
        "uniprot_description": model.get("uniprotDescription", ""),
        "organism_scientific_name": model.get("organismScientificName", ""),
        "tax_id": model.get("taxId"),
        "mean_plddt": global_plddt,
        "confidence_category": confidence_category,
        "pdb_url": model.get("pdbUrl", ""),
        "cif_url": model.get("cifUrl", ""),
        "bcif_url": model.get("bcifUrl", ""),
        "pae_image_url": model.get("paeImageUrl", ""),
        "sequence_start": model.get("uniprotStart", 1),
        "sequence_end": model.get("uniprotEnd", 0),
        "sequence_length": model.get("uniprotSequence", ""),
        "latest_version": model.get("latestVersion", 4),
    }


def fetch_alphafold_batch(
    accessions: list[str],
    rate_limit_delay: float = 0.2,
) -> list[dict]:
    """Fetch AlphaFold models for a list of UniProt accessions with progress tracking."""
    if not accessions:
        return []

    unique_accessions = sorted(list(set(a.strip() for a in accessions if a.strip())))
    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            "Fetching AlphaFold structures", total=len(unique_accessions)
        )

        for acc in unique_accessions:
            progress.update(task, description=f"AlphaFold: {acc}")
            model = fetch_alphafold_prediction(acc)
            if model:
                results.append(model)
            progress.advance(task)
            time.sleep(rate_limit_delay)

    console.print(f"[green]✓ Retrieved {len(results)} AlphaFold structures[/green]")
    return results


# ─── Disk Persistence ────────────────────────────────────────────────────────────

def save_alphafold_data(models: list[dict], target: str) -> Path:
    """Save fetched AlphaFold structures to disk."""
    config.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    filepath = config.RAW_DATA_DIR / f"alphafold_{target}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(models, f, indent=2, ensure_ascii=False)
    console.print(f"[bold green]✓ Saved {len(models)} AlphaFold records to {filepath}[/bold green]")
    return filepath


def load_alphafold_data(target: str) -> list[dict]:
    """Load previously fetched AlphaFold structures from disk."""
    filepath = config.RAW_DATA_DIR / f"alphafold_{target}.json"
    if not filepath.exists():
        raise FileNotFoundError(f"No cached AlphaFold models for target '{target}' at {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        models = json.load(f)
    console.print(f"[green]✓ Loaded {len(models)} cached AlphaFold records from {filepath}[/green]")
    return models


# ─── Ingestion Pipeline ──────────────────────────────────────────────────────────

def ingest_alphafold(
    target: str,
    accessions: Optional[list[str]] = None,
) -> list[dict]:
    """Ingest AlphaFold structural data for a target.

    If accessions are not explicitly provided, attempts to load UniProt
    proteins for this target and query their accessions.

    Args:
        target: Target identifier (e.g. "glucosepane", "senescent_cells").
        accessions: Optional list of UniProt accessions to query.

    Returns:
        List of parsed AlphaFold structure records.
    """
    console.print(f"\n[bold cyan]═══ AlphaFold Ingestion: {target} ═══[/bold cyan]\n")

    if accessions is None:
        from uid_engine.ingest.uniprot import load_proteins

        try:
            proteins = load_proteins(target)
            accessions = [p["accession"] for p in proteins if p.get("accession")]
            console.print(
                f"[cyan]Loaded {len(accessions)} UniProt accessions for AlphaFold structure query[/cyan]"
            )
        except FileNotFoundError:
            console.print(
                f"[yellow]No cached UniProt proteins found for '{target}'. Skipping AlphaFold lookup.[/yellow]"
            )
            return []

    if not accessions:
        console.print("[yellow]No accessions available for AlphaFold ingestion.[/yellow]")
        return []

    models = fetch_alphafold_batch(accessions)
    if models:
        save_alphafold_data(models, target)

    return models

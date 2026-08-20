"""ChEMBL API client — Fetches compound bioactivity data for aging targets.

Searches for compounds tested against AGE-related targets and retrieves
bioactivity data (IC50, Ki, potency) to identify candidate AGE-breakers.

API Documentation: https://www.ebi.ac.uk/chembl/api/data/docs
"""

import json
import time
from pathlib import Path
from typing import Optional

import requests
from rich.console import Console

from uid_engine import config
from uid_engine.utils.retry import retry_request

console = Console()

BASE_URL = config.CHEMBL_BASE_URL


# ─── Target Search Terms ─────────────────────────────────────────────────────────

TARGET_SEARCHES = {
    "glucosepane": [
        {
            "search_type": "target",
            "query": "advanced glycation",
            "label": "AGE-related targets",
        },
        {
            "search_type": "target",
            "query": "RAGE receptor",
            "label": "RAGE receptor targets",
        },
        {
            "search_type": "compound",
            "query": "AGE breaker",
            "label": "AGE-breaker compounds",
        },
        {
            "search_type": "compound",
            "query": "alagebrium",
            "label": "Alagebrium (ALT-711) — historic AGE-breaker",
        },
        {
            "search_type": "compound",
            "query": "aminoguanidine",
            "label": "Aminoguanidine — AGE formation inhibitor",
        },
    ],
}


def search_chembl_targets(query: str, limit: int = 25) -> list[dict]:
    """Search ChEMBL for biological targets matching a query.

    Args:
        query: Free-text search query.
        limit: Maximum number of results.

    Returns:
        List of target dictionaries.
    """
    url = f"{BASE_URL}/target/search.json"
    params = {"q": query, "limit": limit}

    try:
        response = retry_request("GET", url, params=params, timeout=30)
        data = response.json()
        targets = data.get("targets", [])
        return [_parse_target(t) for t in targets]
    except requests.exceptions.RequestException as e:
        console.print(f"[yellow]⚠ ChEMBL target search failed: {e}[/yellow]")
        return []


def search_chembl_compounds(query: str, limit: int = 25) -> list[dict]:
    """Search ChEMBL for compounds (molecules) matching a query.

    Args:
        query: Free-text search query.
        limit: Maximum number of results.

    Returns:
        List of compound dictionaries.
    """
    url = f"{BASE_URL}/molecule/search.json"
    params = {"q": query, "limit": limit}

    try:
        response = retry_request("GET", url, params=params, timeout=30)
        data = response.json()
        molecules = data.get("molecules", [])
        return [_parse_compound(m) for m in molecules]
    except requests.exceptions.RequestException as e:
        console.print(f"[yellow]⚠ ChEMBL compound search failed: {e}[/yellow]")
        return []


def fetch_bioactivity(target_chembl_id: str, limit: int = 100) -> list[dict]:
    """Fetch bioactivity data (IC50, Ki, etc.) for a ChEMBL target.

    Args:
        target_chembl_id: ChEMBL target identifier.
        limit: Maximum number of activity records.

    Returns:
        List of bioactivity dictionaries.
    """
    url = f"{BASE_URL}/activity.json"
    params = {
        "target_chembl_id": target_chembl_id,
        "limit": limit,
        "pchembl_value__isnull": "false",  # Only entries with pChEMBL values
    }

    try:
        response = retry_request("GET", url, params=params, timeout=30)
        data = response.json()
        activities = data.get("activities", [])
        return [_parse_activity(a) for a in activities]
    except requests.exceptions.RequestException as e:
        console.print(f"[yellow]⚠ ChEMBL bioactivity fetch failed: {e}[/yellow]")
        return []


def _parse_target(target: dict) -> dict:
    """Parse a raw ChEMBL target into a clean dictionary."""
    return {
        "chembl_id": target.get("target_chembl_id", ""),
        "name": target.get("pref_name", ""),
        "target_type": target.get("target_type", ""),
        "organism": target.get("organism", ""),
        "description": target.get("description", ""),
        "target_components": [
            {
                "accession": comp.get("accession", ""),
                "component_type": comp.get("component_type", ""),
            }
            for comp in target.get("target_components", [])
        ],
    }


def _parse_compound(molecule: dict) -> dict:
    """Parse a raw ChEMBL molecule into a clean dictionary."""
    props = molecule.get("molecule_properties", {}) or {}
    structs = molecule.get("molecule_structures", {}) or {}

    return {
        "chembl_id": molecule.get("molecule_chembl_id", ""),
        "name": molecule.get("pref_name", "") or "",
        "molecule_type": molecule.get("molecule_type", ""),
        "max_phase": molecule.get("max_phase", 0),
        "oral": molecule.get("oral", False),
        "molecular_weight": props.get("full_mwt", ""),
        "alogp": props.get("alogp", ""),
        "hba": props.get("hba", ""),
        "hbd": props.get("hbd", ""),
        "psa": props.get("psa", ""),
        "smiles": structs.get("canonical_smiles", ""),
        "inchi_key": structs.get("standard_inchi_key", ""),
    }


def _parse_activity(activity: dict) -> dict:
    """Parse a raw ChEMBL activity record."""
    return {
        "activity_id": activity.get("activity_id", ""),
        "molecule_chembl_id": activity.get("molecule_chembl_id", ""),
        "molecule_name": activity.get("molecule_pref_name", ""),
        "target_chembl_id": activity.get("target_chembl_id", ""),
        "target_name": activity.get("target_pref_name", ""),
        "assay_type": activity.get("assay_type", ""),
        "standard_type": activity.get("standard_type", ""),
        "standard_value": activity.get("standard_value", ""),
        "standard_units": activity.get("standard_units", ""),
        "pchembl_value": activity.get("pchembl_value", ""),
    }


def save_chembl_data(data: dict, target: str) -> Path:
    """Save fetched ChEMBL data to a JSON file."""
    filepath = config.RAW_DATA_DIR / f"chembl_{target}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    console.print(f"[green]✓ Saved ChEMBL data to {filepath}[/green]")
    return filepath


def load_chembl_data(target: str) -> dict:
    """Load previously fetched ChEMBL data from disk."""
    filepath = config.RAW_DATA_DIR / f"chembl_{target}.json"
    if not filepath.exists():
        raise FileNotFoundError(f"No cached ChEMBL data for target '{target}'.")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    console.print(f"[green]✓ Loaded cached ChEMBL data from {filepath}[/green]")
    return data


def ingest_chembl(target: str) -> dict:
    """Full ChEMBL ingestion pipeline: search targets & compounds → fetch bioactivity → save.

    Args:
        target: The aging target (e.g., "glucosepane").

    Returns:
        Dictionary with targets, compounds, and bioactivity data.
    """
    console.print(f"\n[bold cyan]═══ ChEMBL Ingestion: {target} ═══[/bold cyan]\n")

    searches = TARGET_SEARCHES.get(target, [])
    if not searches:
        console.print(f"[red]No ChEMBL searches defined for target: {target}[/red]")
        return {}

    all_targets = []
    all_compounds = []
    all_activities = []

    for search in searches:
        console.print(f"  Searching: {search['label']}...")

        if search["search_type"] == "target":
            results = search_chembl_targets(search["query"])
            all_targets.extend(results)

            # Fetch bioactivity for each target
            for t in results:
                if t["chembl_id"]:
                    activities = fetch_bioactivity(t["chembl_id"], limit=50)
                    all_activities.extend(activities)
                    time.sleep(0.3)

        elif search["search_type"] == "compound":
            results = search_chembl_compounds(search["query"])
            all_compounds.extend(results)

        time.sleep(0.3)

    # Deduplicate
    seen_targets = set()
    unique_targets = []
    for t in all_targets:
        if t["chembl_id"] not in seen_targets:
            seen_targets.add(t["chembl_id"])
            unique_targets.append(t)

    seen_compounds = set()
    unique_compounds = []
    for c in all_compounds:
        if c["chembl_id"] not in seen_compounds:
            seen_compounds.add(c["chembl_id"])
            unique_compounds.append(c)

    result = {
        "targets": unique_targets,
        "compounds": unique_compounds,
        "activities": all_activities,
    }

    console.print(f"\n[bold]ChEMBL Ingestion Summary:[/bold]")
    console.print(f"  Unique targets: {len(unique_targets)}")
    console.print(f"  Unique compounds: {len(unique_compounds)}")
    console.print(f"  Bioactivity records: {len(all_activities)}")

    save_chembl_data(result, target)
    return result

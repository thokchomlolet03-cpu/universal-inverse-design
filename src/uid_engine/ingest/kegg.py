"""KEGG Pathway API client — Fetches metabolic pathway data for aging targets.

Maps the biochemical pathways involved in AGE formation and degradation,
identifying which enzymatic steps have known catalysts and which are gaps.

API Documentation: https://www.kegg.jp/kegg/rest/keggapi.html
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

BASE_URL = config.KEGG_BASE_URL

# ─── Target Pathways ─────────────────────────────────────────────────────────────
# KEGG pathway IDs relevant to each aging target.

TARGET_PATHWAYS = {
    "glucosepane": [
        {
            "pathway_id": "hsa00010",
            "name": "Glycolysis / Gluconeogenesis",
            "relevance": "Glucose metabolism — source of glycation substrates",
        },
        {
            "pathway_id": "hsa04933",
            "name": "AGE-RAGE signaling pathway in diabetic complications",
            "relevance": "Primary pathway for AGE-mediated damage signaling",
        },
        {
            "pathway_id": "hsa00220",
            "name": "Arginine biosynthesis",
            "relevance": "Arginine is one of the two amino acids crosslinked by glucosepane",
        },
        {
            "pathway_id": "hsa00310",
            "name": "Lysine degradation",
            "relevance": "Lysine is the other amino acid crosslinked by glucosepane",
        },
        {
            "pathway_id": "hsa04510",
            "name": "Focal adhesion",
            "relevance": "ECM-cell interactions disrupted by crosslinking",
        },
    ],
}


def fetch_pathway_info(pathway_id: str) -> Optional[dict]:
    """Fetch detailed information for a single KEGG pathway.

    Args:
        pathway_id: KEGG pathway identifier (e.g., "hsa04933").

    Returns:
        Dictionary with pathway metadata, or None on failure.
    """
    try:
        url = f"{BASE_URL}/get/{pathway_id}"
        response = retry_request("GET", url, timeout=30)
        raw_text = response.text
        pathway_data = _parse_kegg_flat(raw_text, pathway_id)
        return pathway_data
    except requests.exceptions.RequestException as e:
        console.print(f"[yellow]⚠ Failed to fetch pathway {pathway_id}: {e}[/yellow]")
        return None


def fetch_pathway_genes(pathway_id: str) -> list[dict]:
    """Fetch all genes/enzymes associated with a KEGG pathway.

    Args:
        pathway_id: KEGG pathway identifier.

    Returns:
        List of gene dictionaries with KEGG gene ID, name, and EC numbers.
    """
    try:
        url = f"{BASE_URL}/link/genes/{pathway_id}"
        response = retry_request("GET", url, timeout=30)
        genes = []
        for line in response.text.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                gene_id = parts[1].strip()
                genes.append({"kegg_gene_id": gene_id})
        return genes
    except requests.exceptions.RequestException as e:
        console.print(f"[yellow]⚠ Failed to fetch genes for {pathway_id}: {e}[/yellow]")
        return []


def fetch_pathway_compounds(pathway_id: str) -> list[dict]:
    """Fetch all compounds associated with a KEGG pathway.

    Args:
        pathway_id: KEGG pathway identifier.

    Returns:
        List of compound dictionaries.
    """
    try:
        url = f"{BASE_URL}/link/compound/{pathway_id}"
        response = retry_request("GET", url, timeout=30)
        compounds = []
        for line in response.text.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                compound_id = parts[1].strip()
                compounds.append({"kegg_compound_id": compound_id})
        return compounds
    except requests.exceptions.RequestException as e:
        console.print(f"[yellow]⚠ Failed to fetch compounds for {pathway_id}: {e}[/yellow]")
        return []


def _parse_kegg_flat(text: str, pathway_id: str) -> dict:
    """Parse KEGG flat-file format into a structured dictionary."""
    result = {
        "pathway_id": pathway_id,
        "name": "",
        "description": "",
        "organism": "",
        "genes": [],
        "compounds": [],
        "enzymes": [],
    }

    current_section = ""
    for line in text.split("\n"):
        if not line.strip():
            continue

        # Section headers start at column 0 (no leading space)
        if line[0] != " " and not line.startswith("///"):
            current_section = line.split()[0] if line.split() else ""

        if current_section == "NAME":
            name_part = line.replace("NAME", "").strip()
            if name_part:
                result["name"] = name_part.rstrip(" -")

        elif current_section == "DESCRIPTION":
            desc_part = line.replace("DESCRIPTION", "").strip()
            if desc_part:
                result["description"] += desc_part + " "

        elif current_section == "ORGANISM":
            org_part = line.replace("ORGANISM", "").strip()
            if org_part:
                result["organism"] = org_part

        elif current_section == "GENE":
            gene_part = line.strip()
            if gene_part and not gene_part.startswith("GENE"):
                gene_part = gene_part.lstrip()
                # Format: "geneID  geneName; description [EC:x.x.x.x]"
                parts = gene_part.split(None, 1)
                if len(parts) >= 2:
                    gene_id = parts[0]
                    rest = parts[1]
                    # Extract EC number if present
                    ec = ""
                    if "[EC:" in rest:
                        ec_start = rest.index("[EC:") + 4
                        ec_end = rest.index("]", ec_start)
                        ec = rest[ec_start:ec_end]
                    result["genes"].append({
                        "gene_id": gene_id,
                        "description": rest.split("[")[0].strip(),
                        "ec_number": ec,
                    })

        elif current_section == "COMPOUND":
            comp_part = line.strip()
            if comp_part and not comp_part.startswith("COMPOUND"):
                comp_part = comp_part.lstrip()
                parts = comp_part.split(None, 1)
                if len(parts) >= 2:
                    result["compounds"].append({
                        "compound_id": parts[0],
                        "name": parts[1].strip(),
                    })

    result["description"] = result["description"].strip()
    return result


def save_pathways(pathways: list[dict], target: str) -> Path:
    """Save fetched pathway data to a JSON file."""
    filepath = config.RAW_DATA_DIR / f"kegg_{target}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(pathways, f, indent=2, ensure_ascii=False)
    console.print(f"[green]✓ Saved {len(pathways)} pathways to {filepath}[/green]")
    return filepath


def load_pathways(target: str) -> list[dict]:
    """Load previously fetched pathways from disk."""
    filepath = config.RAW_DATA_DIR / f"kegg_{target}.json"
    if not filepath.exists():
        raise FileNotFoundError(f"No cached pathways for target '{target}'.")
    with open(filepath, "r", encoding="utf-8") as f:
        pathways = json.load(f)
    console.print(f"[green]✓ Loaded {len(pathways)} cached pathways from {filepath}[/green]")
    return pathways


def ingest_kegg(target: str) -> list[dict]:
    """Full KEGG ingestion pipeline: fetch pathways → parse → save.

    Args:
        target: The aging target (e.g., "glucosepane").

    Returns:
        List of pathway dictionaries with genes and compounds.
    """
    console.print(f"\n[bold cyan]═══ KEGG Ingestion: {target} ═══[/bold cyan]\n")

    pathway_configs = TARGET_PATHWAYS.get(target, [])
    if not pathway_configs:
        console.print(f"[red]No KEGG pathways defined for target: {target}[/red]")
        return []

    pathways = []
    for pw_config in pathway_configs:
        pw_id = pw_config["pathway_id"]
        console.print(f"  Fetching: {pw_config['name']} ({pw_id})...")

        pw_data = fetch_pathway_info(pw_id)
        if pw_data:
            pw_data["relevance"] = pw_config["relevance"]
            pathways.append(pw_data)

        time.sleep(0.5)  # Rate limiting

    console.print(f"\n[bold]KEGG Ingestion Summary:[/bold]")
    console.print(f"  Pathways fetched: {len(pathways)}")
    total_genes = sum(len(pw.get("genes", [])) for pw in pathways)
    total_compounds = sum(len(pw.get("compounds", [])) for pw in pathways)
    console.print(f"  Total genes: {total_genes}")
    console.print(f"  Total compounds: {total_compounds}")

    save_pathways(pathways, target)
    return pathways

"""UniProt REST API client — Fetches protein/enzyme data relevant to aging targets.

Searches UniProtKB for enzymes capable of AGE degradation, amidine hydrolysis,
crosslink cleavage, and related catalytic activities. Focuses on bacterial and
fungal enzymes as potential xenobiotic therapeutic candidates.

API Documentation: https://www.uniprot.org/help/api
"""

import json
import time
from pathlib import Path
from typing import Optional

import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from uid_engine import config
from uid_engine.utils.retry import retry_request

console = Console()

BASE_URL = config.UNIPROT_BASE_URL

# ─── Search Strategies ───────────────────────────────────────────────────────────
# Domain-specific queries targeting enzymes relevant to each aging bottleneck.

SEARCH_QUERIES = {
    "glucosepane": [
        # Direct AGE-related enzymes
        {
            "query": 'fructosamine AND (kinase OR deglycation) AND reviewed:true',
            "label": "Fructosamine kinases (deglycation enzymes)",
        },
        {
            "query": 'amadoriase AND reviewed:true',
            "label": "Amadoriases (fructosyl amino acid oxidases)",
        },
        {
            "query": '"advanced glycation" AND (degradation OR hydrolysis OR cleavage) AND reviewed:true',
            "label": "AGE degradation enzymes",
        },
        # Enzymes that could hydrolyze the imidazole/amidine core
        {
            "query": '"amidine" AND hydrolase AND reviewed:true',
            "label": "Amidine hydrolases",
        },
        {
            "query": '"imidazole" AND (hydrolase OR hydrolysis) AND reviewed:true',
            "label": "Imidazole-ring hydrolases",
        },
        # Collagen-associated enzymes
        {
            "query": 'collagenase AND (bacterial OR fungal) AND reviewed:true',
            "label": "Bacterial/fungal collagenases",
        },
        # RAGE (receptor for AGEs) — the immune receptor side
        {
            "query": '"receptor for advanced glycation" AND reviewed:true',
            "label": "RAGE receptors",
        },
    ],
    "senescent_cells": [
        # Anti-apoptotic proteins (SCAP targets)
        {
            "query": 'gene:BCL2 OR gene:BCL2L1 OR gene:BCL2L2 AND organism_id:9606 AND reviewed:true',
            "label": "BCL-2 family anti-apoptotic proteins (BCL-2, BCL-xL, BCL-W)",
        },
        # Cell cycle inhibitors (senescence markers)
        {
            "query": 'gene:CDKN2A OR gene:CDKN1A AND organism_id:9606 AND reviewed:true',
            "label": "Cell cycle arrest drivers (p16INK4a, p21CIP1)",
        },
        # FOXO4 regulator
        {
            "query": 'gene:FOXO4 AND organism_id:9606 AND reviewed:true',
            "label": "Forkhead box protein O4 (FOXO4)",
        },
        # Surface markers
        {
            "query": 'gene:DPP4 OR gene:PLAUR AND organism_id:9606 AND reviewed:true',
            "label": "Senescence surface markers (DPP4/CD26, uPAR)",
        },
        # Key SASP factors
        {
            "query": 'gene:IL6 OR gene:CXCL8 OR gene:MMP3 AND organism_id:9606 AND reviewed:true',
            "label": "Major SASP effector cytokines & proteases",
        },
    ],
    "mitochondrial_mutations": [
        # Translocases & import machinery
        {
            "query": 'gene:TOMM20 OR gene:TOMM40 OR gene:TIMM23 AND organism_id:9606 AND reviewed:true',
            "label": "Mitochondrial outer and inner membrane translocases (TOM/TIM)",
        },
        # Hydrophobic core subunits (targets for allotopic expression)
        {
            "query": 'gene:MT-ND4 OR gene:MT-ND6 OR gene:MT-ATP6 OR gene:MT-CYB AND organism_id:9606 AND reviewed:true',
            "label": "Hydrophobic mtDNA-encoded OXPHOS core subunits",
        },
        # Mitochondrial transcription and copy number regulators
        {
            "query": 'gene:TFAM OR gene:PPARGC1A AND organism_id:9606 AND reviewed:true',
            "label": "Mitochondrial biogenesis & copy number factors (TFAM, PGC-1alpha)",
        },
        # Base editor & nuclease enzymes
        {
            "query": 'DddA OR "cytosine deaminase" AND reviewed:true',
            "label": "DddA bacterial interbacterial toxin (mitochondrial base editor domain)",
        },
    ],
}


def search_uniprot(query: str, max_results: int = 50) -> list[dict]:
    """Search UniProtKB and return structured protein entries.

    Args:
        query: UniProt search query string.
        max_results: Maximum number of results per query.

    Returns:
        List of protein dictionaries with structured metadata.
    """
    url = f"{BASE_URL}/uniprotkb/search"
    params = {
        "query": query,
        "format": "json",
        "size": min(max_results, 500),
        "fields": (
            "accession,id,protein_name,gene_names,organism_name,organism_id,"
            "ec,cc_catalytic_activity,cc_function,go,length,reviewed,"
            "cc_subcellular_location,xref_pdb"
        ),
    }

    try:
        response = retry_request("GET", url, params=params, timeout=30)
        data = response.json()
        return data.get("results", [])
    except requests.exceptions.RequestException as e:
        console.print(f"[red]UniProt search failed: {e}[/red]")
        return []


def parse_uniprot_entry(entry: dict) -> dict:
    """Parse a raw UniProt JSON entry into a clean, structured dictionary."""

    accession = entry.get("primaryAccession", "")
    entry_id = entry.get("uniProtkbId", "")

    # Protein name (recommended name or first submitted name)
    protein_name = ""
    protein_desc = entry.get("proteinDescription", {})
    rec_name = protein_desc.get("recommendedName")
    if rec_name:
        protein_name = rec_name.get("fullName", {}).get("value", "")
    elif protein_desc.get("submittedNames"):
        protein_name = protein_desc["submittedNames"][0].get("fullName", {}).get("value", "")

    # Gene names
    gene_names = []
    for gene in entry.get("genes", []):
        if gene.get("geneName"):
            gene_names.append(gene["geneName"].get("value", ""))

    # Organism
    organism = entry.get("organism", {}).get("scientificName", "")
    taxon_id = entry.get("organism", {}).get("taxonId", "")

    # EC numbers
    ec_numbers = []
    if rec_name and rec_name.get("ecNumbers"):
        for ec in rec_name["ecNumbers"]:
            ec_numbers.append(ec.get("value", ""))

    # Catalytic activity
    catalytic_activities = []
    for comment in entry.get("comments", []):
        if comment.get("commentType") == "CATALYTIC ACTIVITY":
            reaction = comment.get("reaction", {})
            catalytic_activities.append({
                "reaction": reaction.get("name", ""),
                "ec": reaction.get("ecNumber", ""),
            })

    # Function description
    function_desc = ""
    for comment in entry.get("comments", []):
        if comment.get("commentType") == "FUNCTION":
            texts = comment.get("texts", [])
            if texts:
                function_desc = texts[0].get("value", "")

    # GO terms
    go_terms = []
    for xref in entry.get("uniProtKBCrossReferences", []):
        if xref.get("database") == "GO":
            go_id = xref.get("id", "")
            go_props = xref.get("properties", [])
            go_name = ""
            for prop in go_props:
                if prop.get("key") == "GoTerm":
                    go_name = prop.get("value", "")
            go_terms.append({"id": go_id, "name": go_name})

    # PDB structures
    pdb_ids = []
    for xref in entry.get("uniProtKBCrossReferences", []):
        if xref.get("database") == "PDB":
            pdb_ids.append(xref.get("id", ""))

    # Subcellular location
    locations = []
    for comment in entry.get("comments", []):
        if comment.get("commentType") == "SUBCELLULAR LOCATION":
            for loc in comment.get("subcellularLocations", []):
                location = loc.get("location", {}).get("value", "")
                if location:
                    locations.append(location)

    # Sequence length
    length = entry.get("sequence", {}).get("length", 0)

    # Reviewed status
    reviewed = entry.get("entryType", "") == "UniProtKB reviewed (Swiss-Prot)"

    return {
        "accession": accession,
        "entry_id": entry_id,
        "protein_name": protein_name,
        "gene_names": gene_names,
        "organism": organism,
        "taxon_id": taxon_id,
        "ec_numbers": ec_numbers,
        "catalytic_activities": catalytic_activities,
        "function": function_desc,
        "go_terms": go_terms,
        "pdb_ids": pdb_ids,
        "subcellular_locations": locations,
        "length": length,
        "reviewed": reviewed,
    }


def save_proteins(proteins: list[dict], target: str) -> Path:
    """Save fetched proteins to a JSON file."""
    filepath = config.RAW_DATA_DIR / f"uniprot_{target}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(proteins, f, indent=2, ensure_ascii=False)
    console.print(f"[green]✓ Saved {len(proteins)} proteins to {filepath}[/green]")
    return filepath


def load_proteins(target: str) -> list[dict]:
    """Load previously fetched proteins from disk."""
    filepath = config.RAW_DATA_DIR / f"uniprot_{target}.json"
    if not filepath.exists():
        raise FileNotFoundError(f"No cached proteins for target '{target}'.")
    with open(filepath, "r", encoding="utf-8") as f:
        proteins = json.load(f)
    console.print(f"[green]✓ Loaded {len(proteins)} cached proteins from {filepath}[/green]")
    return proteins


def ingest_uniprot(target: str) -> list[dict]:
    """Full UniProt ingestion pipeline: search all queries → parse → deduplicate → save.

    Args:
        target: The aging target (e.g., "glucosepane").

    Returns:
        List of parsed, deduplicated protein dictionaries.
    """
    console.print(f"\n[bold cyan]═══ UniProt Ingestion: {target} ═══[/bold cyan]\n")

    queries = SEARCH_QUERIES.get(target, [])
    if not queries:
        console.print(f"[red]No UniProt search queries defined for target: {target}[/red]")
        return []

    all_proteins = {}  # Deduplicate by accession

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Querying UniProt", total=len(queries))

        for query_info in queries:
            query = query_info["query"]
            label = query_info["label"]
            progress.update(task, description=f"Searching: {label}")

            raw_results = search_uniprot(query)

            for entry in raw_results:
                parsed = parse_uniprot_entry(entry)
                accession = parsed["accession"]
                if accession and accession not in all_proteins:
                    all_proteins[accession] = parsed

            time.sleep(0.5)  # Be polite to the API
            progress.advance(task)

    proteins = list(all_proteins.values())
    console.print(f"\n[bold]UniProt Ingestion Summary:[/bold]")
    console.print(f"  Total unique proteins: {len(proteins)}")
    console.print(f"  Reviewed (Swiss-Prot): {sum(1 for p in proteins if p['reviewed'])}")
    console.print(f"  With PDB structures: {sum(1 for p in proteins if p['pdb_ids'])}")
    console.print(f"  With EC numbers: {sum(1 for p in proteins if p['ec_numbers'])}")

    # Show organisms breakdown
    organisms = {}
    for p in proteins:
        org = p.get("organism", "Unknown")
        organisms[org] = organisms.get(org, 0) + 1
    if organisms:
        top_orgs = sorted(organisms.items(), key=lambda x: x[1], reverse=True)[:10]
        console.print(f"\n  [bold]Top organisms:[/bold]")
        for org, count in top_orgs:
            console.print(f"    {org}: {count}")

    # Save
    save_proteins(proteins, target)

    return proteins

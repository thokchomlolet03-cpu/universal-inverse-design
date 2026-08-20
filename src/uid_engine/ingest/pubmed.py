"""PubMed E-utilities client — Fetches scientific papers from NCBI PubMed.

This module uses BioPython's Entrez interface to search and retrieve
papers related to a specific aging target (e.g., glucosepane). It handles
rate limiting, pagination, and structured storage of results.

API Documentation: https://www.ncbi.nlm.nih.gov/books/NBK25497/
Rate Limits: 3 req/sec without API key, 10 req/sec with API key.
"""

import json
import time
from pathlib import Path
from typing import Optional

from Bio import Entrez
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from uid_engine import config
from uid_engine.utils.entrez_retry import entrez_fetch, entrez_search

console = Console()

# Configure Entrez with project credentials
Entrez.email = config.NCBI_EMAIL
Entrez.tool = "UniversalInverseDesignEngine"
if config.NCBI_API_KEY:
    Entrez.api_key = config.NCBI_API_KEY


# ─── Search Queries ──────────────────────────────────────────────────────────────
# Pre-defined search strategies for each aging target.
# These are carefully constructed PubMed queries, not naive keyword searches.

SEARCH_QUERIES = {
    "glucosepane": (
        '("glucosepane"[Title/Abstract] OR "glucosepane crosslink"[Title/Abstract]) '
        'OR ("advanced glycation endproduct" AND "crosslink" AND '
        '("collagen" OR "elastin" OR "extracellular matrix")) '
        'OR ("AGE breaker" AND ("enzyme" OR "cleavage" OR "hydrolysis")) '
        'OR ("GlycoSENS"[Title/Abstract])'
    ),
    "senescent_cells": (
        '("senolytic"[Title/Abstract] OR "senescent cells"[Title/Abstract] '
        'AND "clearance"[Title/Abstract])'
    ),
    "mitochondrial_mutations": (
        '("allotopic expression"[Title/Abstract] OR "mitochondrial DNA mutation" '
        'AND "aging"[Title/Abstract])'
    ),
}


def search_pubmed(target: str, max_results: Optional[int] = None) -> list[str]:
    """Search PubMed and return a list of PMIDs for a given target.

    Args:
        target: The aging target to search for (e.g., "glucosepane").
        max_results: Maximum number of results. Defaults to config.MAX_PAPERS.

    Returns:
        List of PubMed IDs (PMIDs) as strings.
    """
    max_results = max_results or config.MAX_PAPERS
    query = SEARCH_QUERIES.get(target)

    if not query:
        console.print(f"[red]No search query defined for target: {target}[/red]")
        console.print(f"[dim]Available targets: {', '.join(SEARCH_QUERIES.keys())}[/dim]")
        return []

    console.print(f"[cyan]Searching PubMed for '{target}' (max {max_results} results)...[/cyan]")

    record = entrez_search(
        db="pubmed",
        term=query,
        retmax=max_results,
        sort="relevance",
        usehistory="y",
    )
    if record is None:
        console.print("[red]PubMed search failed after retries — returning empty list[/red]")
        return []

    pmids = record.get("IdList", [])
    total_count = int(record.get("Count", 0))
    console.print(
        f"[green]Found {total_count} total papers, retrieving {len(pmids)}[/green]"
    )
    return pmids


def fetch_paper_details(pmids: list[str], batch_size: int = 50) -> list[dict]:
    """Fetch detailed metadata for a list of PMIDs.

    Retrieves: title, abstract, authors, journal, year, MeSH terms, DOI.
    Handles batching and rate limiting per NCBI policy.

    Args:
        pmids: List of PubMed IDs.
        batch_size: Number of PMIDs to fetch per request (max 200).

    Returns:
        List of paper dictionaries with structured metadata.
    """
    if not pmids:
        return []

    papers = []
    total_batches = (len(pmids) + batch_size - 1) // batch_size
    rate_limit_delay = 0.34 if config.NCBI_API_KEY else 0.5  # ~3 req/sec without key

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching paper details", total=len(pmids))

        for batch_idx in range(total_batches):
            start = batch_idx * batch_size
            end = min(start + batch_size, len(pmids))
            batch_pmids = pmids[start:end]

            records = entrez_fetch(
                db="pubmed",
                id=",".join(batch_pmids),
                rettype="xml",
                retmode="xml",
            )
            if records is None:
                console.print(f"[yellow]⚠ Batch {batch_idx + 1} skipped after retries[/yellow]")
                progress.update(task, advance=len(batch_pmids))
                continue

            # Parse each article in the batch
            for article in records.get("PubmedArticle", []):
                paper = _parse_pubmed_article(article)
                if paper:
                    papers.append(paper)

            progress.update(task, advance=len(batch_pmids))
            # entrez_retry handles per-request delay; keep a small buffer for batch pacing
            time.sleep(rate_limit_delay)

    console.print(f"[green]✓ Retrieved {len(papers)} papers with full metadata[/green]")
    return papers


def _parse_pubmed_article(article: dict) -> Optional[dict]:
    """Parse a single PubMed article XML record into a structured dictionary."""
    try:
        medline = article.get("MedlineCitation", {})
        article_data = medline.get("Article", {})
        pmid = str(medline.get("PMID", ""))

        # Title
        title = str(article_data.get("ArticleTitle", ""))

        # Abstract
        abstract_parts = article_data.get("Abstract", {}).get("AbstractText", [])
        abstract = " ".join(str(part) for part in abstract_parts) if abstract_parts else ""

        # Authors
        author_list = article_data.get("AuthorList", [])
        authors = []
        for author in author_list:
            last = author.get("LastName", "")
            first = author.get("ForeName", "")
            if last:
                authors.append(f"{last} {first}".strip())

        # Journal
        journal_info = article_data.get("Journal", {})
        journal = str(journal_info.get("Title", ""))

        # Year
        pub_date = article_data.get("Journal", {}).get("JournalIssue", {}).get("PubDate", {})
        year = pub_date.get("Year", "")
        if not year:
            medline_date = pub_date.get("MedlineDate", "")
            year = medline_date[:4] if medline_date else ""

        # MeSH terms
        mesh_list = medline.get("MeshHeadingList", [])
        mesh_terms = []
        for mesh in mesh_list:
            descriptor = mesh.get("DescriptorName", "")
            if descriptor:
                mesh_terms.append(str(descriptor))

        # DOI
        doi = ""
        article_ids = article.get("PubmedData", {}).get("ArticleIdList", [])
        for aid in article_ids:
            if hasattr(aid, "attributes") and aid.attributes.get("IdType") == "doi":
                doi = str(aid)
                break

        # Keywords
        keyword_list = medline.get("KeywordList", [])
        keywords = []
        for kw_group in keyword_list:
            for kw in kw_group:
                keywords.append(str(kw))

        return {
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "journal": journal,
            "year": year,
            "doi": doi,
            "mesh_terms": mesh_terms,
            "keywords": keywords,
        }

    except Exception as e:
        console.print(f"[yellow]⚠ Failed to parse article: {e}[/yellow]")
        return None


def save_papers(papers: list[dict], target: str) -> Path:
    """Save fetched papers to a JSON file in the raw data directory.

    Args:
        papers: List of paper dictionaries.
        target: The aging target name (used for filename).

    Returns:
        Path to the saved file.
    """
    filepath = config.RAW_DATA_DIR / f"pubmed_{target}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)
    console.print(f"[green]✓ Saved {len(papers)} papers to {filepath}[/green]")
    return filepath


def load_papers(target: str) -> list[dict]:
    """Load previously fetched papers from disk.

    Args:
        target: The aging target name.

    Returns:
        List of paper dictionaries.

    Raises:
        FileNotFoundError: If no cached papers exist for this target.
    """
    filepath = config.RAW_DATA_DIR / f"pubmed_{target}.json"
    if not filepath.exists():
        raise FileNotFoundError(f"No cached papers for target '{target}'. Run ingestion first.")

    with open(filepath, "r", encoding="utf-8") as f:
        papers = json.load(f)

    console.print(f"[green]✓ Loaded {len(papers)} cached papers from {filepath}[/green]")
    return papers


def ingest_pubmed(target: str, max_results: Optional[int] = None) -> list[dict]:
    """Full PubMed ingestion pipeline: search → fetch → save.

    Args:
        target: The aging target (e.g., "glucosepane").
        max_results: Maximum papers to retrieve.

    Returns:
        List of paper dictionaries with full metadata.
    """
    console.print(f"\n[bold cyan]═══ PubMed Ingestion: {target} ═══[/bold cyan]\n")

    # Step 1: Search
    pmids = search_pubmed(target, max_results)
    if not pmids:
        console.print("[yellow]No papers found. Check search query.[/yellow]")
        return []

    # Step 2: Fetch details
    papers = fetch_paper_details(pmids)

    # Step 3: Save to disk
    save_papers(papers, target)

    # Step 4: Summary
    papers_with_abstract = sum(1 for p in papers if p.get("abstract"))
    console.print(f"\n[bold]Ingestion Summary:[/bold]")
    console.print(f"  Papers retrieved: {len(papers)}")
    console.print(f"  Papers with abstracts: {papers_with_abstract}")
    console.print(f"  Papers without abstracts: {len(papers) - papers_with_abstract}")

    if papers:
        years = [p.get("year", "") for p in papers if p.get("year")]
        if years:
            console.print(f"  Year range: {min(years)} — {max(years)}")

    return papers

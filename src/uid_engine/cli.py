"""Command-line interface for the Universal Inverse Design Engine.

Usage:
    uid mock-test     Run the full pipeline with mock data (Phase A/B test)
    uid ingest        Ingest data from all APIs for a target
    uid build-graph   Build/update the knowledge graph from ingested data
    uid detect-gaps   Run the negative space detector
    uid report        Generate the epistemic gap report
    uid pipeline      Run the full pipeline: ingest → build → detect → report
"""

import sys

from rich.console import Console
from rich.panel import Panel

from uid_engine.graph.builder import build_mock_glucosepane_graph, EpistemicGraph
from uid_engine.graph.schema import NodeData, NodeType, EdgeData, EdgeType, EvidenceStatus
from uid_engine.graph.store import save_graph, load_graph
from uid_engine.analysis.causal_chains import build_glucosepane_repair_chain
from uid_engine.analysis.gap_detector import NegativeSpaceDetector
from uid_engine.analysis.reporter import GapReporter
from uid_engine.ingest.pubmed import ingest_pubmed, load_papers
from uid_engine.ingest.uniprot import ingest_uniprot, load_proteins
from uid_engine.ingest.kegg import ingest_kegg, load_pathways
from uid_engine.ingest.chembl import ingest_chembl, load_chembl_data
from uid_engine.graph.entities import run_batch_extraction
from uid_engine import config

console = Console()


def print_banner():
    """Print the engine banner."""
    console.print(Panel.fit(
        "[bold cyan]Universal Inverse Design Engine[/bold cyan]\n"
        "[dim]Finding what humanity doesn't know[/dim]\n"
        "[dim]v0.1.0 — Milestone 1: Glucosepane Epistemic Map[/dim]",
        border_style="cyan",
    ))


# ─── Phase A/B: Mock Test ────────────────────────────────────────────────────────

def cmd_mock_test():
    """Run the complete pipeline with mock data."""
    print_banner()
    console.print("\n[bold]Phase A/B Integration Test: Mock Data Pipeline[/bold]\n")

    graph = build_mock_glucosepane_graph()
    graph.print_stats()
    save_graph(graph)

    causal_chain = build_glucosepane_repair_chain()
    console.print("[green]✓ Causal chain built[/green]")

    detector = NegativeSpaceDetector(graph)
    gaps = detector.detect_gaps(causal_chain)

    _print_gaps(gaps)

    reporter = GapReporter(graph, gaps)
    report_path = reporter.save_report()

    _print_complete(len(gaps), report_path)


# ─── Phase C: Real Data Ingestion ────────────────────────────────────────────────

def cmd_ingest(target: str = "glucosepane"):
    """Ingest data from all 4 APIs for a given target."""
    print_banner()
    console.print(f"\n[bold]Phase C: Data Ingestion — {target}[/bold]\n")

    # 1. PubMed
    papers = ingest_pubmed(target)

    # 2. UniProt
    proteins = ingest_uniprot(target)

    # 3. KEGG
    pathways = ingest_kegg(target)

    # 4. ChEMBL
    chembl = ingest_chembl(target)

    # Summary
    console.print(Panel.fit(
        f"[bold green]Ingestion complete![/bold green]\n\n"
        f"PubMed papers: [bold]{len(papers)}[/bold]\n"
        f"UniProt proteins: [bold]{len(proteins)}[/bold]\n"
        f"KEGG pathways: [bold]{len(pathways)}[/bold]\n"
        f"ChEMBL targets: [bold]{len(chembl.get('targets', []))}[/bold]\n"
        f"ChEMBL compounds: [bold]{len(chembl.get('compounds', []))}[/bold]\n"
        f"Bioactivity records: [bold]{len(chembl.get('activities', []))}[/bold]",
        border_style="green",
    ))


# ─── Phase C: Build Graph from Real Data ─────────────────────────────────────────

def cmd_build_graph(target: str = "glucosepane"):
    """Build the knowledge graph from ingested real data."""
    print_banner()
    console.print(f"\n[bold]Building Knowledge Graph from Real Data — {target}[/bold]\n")

    # Start with the mock graph as foundation (it contains the SENS categories
    # and core glucosepane facts that are manually curated)
    graph = build_mock_glucosepane_graph()

    # Layer on real data
    _add_papers_to_graph(graph, target)
    _add_proteins_to_graph(graph, target)
    _add_pathways_to_graph(graph, target)
    _add_chembl_to_graph(graph, target)

    graph.print_stats()
    save_graph(graph)
    console.print("[bold green]✓ Knowledge graph built and saved[/bold green]")


def _add_papers_to_graph(graph: EpistemicGraph, target: str):
    """Add PubMed papers, extracted entities, and causal relationships to the knowledge graph."""
    try:
        papers = load_papers(target)
    except FileNotFoundError:
        console.print("[yellow]⚠ No PubMed data found. Run 'uid ingest' first.[/yellow]")
        return

    # Run entity extraction across papers
    extractions = run_batch_extraction(papers, target)

    added_papers = 0
    added_entities = 0
    added_edges = 0

    for paper in papers:
        pmid = str(paper.get("pmid", ""))
        if not pmid:
            continue

        paper_node_id = f"paper:PMID_{pmid}"
        if not graph.has_node(paper_node_id):
            title = paper.get("title", "")
            abstract = paper.get("abstract", "")
            year = paper.get("year", "")
            journal = paper.get("journal", "")
            authors = paper.get("authors", [])

            graph.add_node(NodeData(
                node_id=paper_node_id,
                node_type=NodeType.PAPER,
                name=f"{authors[0] if authors else 'Unknown'} {year} — {title[:60]}",
                description=abstract[:200] + "..." if len(abstract) > 200 else abstract,
                source="PubMed",
                confidence=config.CONFIDENCE_SINGLE_PAPER,
                metadata={
                    "pmid": pmid,
                    "year": year,
                    "journal": journal,
                    "authors": ", ".join(authors[:3]),
                    "mesh_terms": ", ".join(paper.get("mesh_terms", [])[:5]),
                    "has_abstract": bool(abstract),
                },
            ))
            added_papers += 1

        # Process extracted entities & causal edges for this paper
        paper_ext = extractions.get(pmid, {})
        for ent in paper_ext.get("entities", []):
            ent_id = ent.get("entity_id", "")
            if not ent_id:
                continue

            if not graph.has_node(ent_id):
                try:
                    ntype = NodeType(ent.get("type", "MOLECULE"))
                except ValueError:
                    ntype = NodeType.MOLECULE

                graph.add_node(NodeData(
                    node_id=ent_id,
                    node_type=ntype,
                    name=ent.get("name", ent_id),
                    description=f"Extracted from PMID:{pmid}",
                    source=f"PubMed:PMID_{pmid}",
                    confidence=config.CONFIDENCE_LLM_EXTRACTION,
                    metadata={"organism": ent.get("organism_source", "")},
                ))
                added_entities += 1

            # Connect entity to paper
            if not graph.graph.has_edge(ent_id, paper_node_id):
                graph.add_edge(ent_id, paper_node_id, EdgeData(
                    edge_type=EdgeType.REPORTED_IN,
                    source="PubMed",
                    context=f"Reported in PMID:{pmid}",
                ))

        for edge in paper_ext.get("causal_edges", []):
            s_id = edge.get("source_id", "")
            t_id = edge.get("target_id", "")
            etype_str = edge.get("edge_type", "ACTIVATES")
            status_str = edge.get("status", "PROVEN")

            if graph.has_node(s_id) and graph.has_node(t_id):
                try:
                    etype = EdgeType(etype_str)
                except ValueError:
                    etype = EdgeType.ACTIVATES

                try:
                    estatus = EvidenceStatus(status_str)
                except ValueError:
                    estatus = EvidenceStatus.PROVEN

                if not graph.graph.has_edge(s_id, t_id):
                    graph.add_edge(s_id, t_id, EdgeData(
                        edge_type=etype,
                        status=estatus,
                        source=f"PubMed:PMID_{pmid}",
                        context=edge.get("context", ""),
                        confidence=config.CONFIDENCE_LLM_EXTRACTION,
                    ))
                    added_edges += 1

    console.print(f"[green]  ✓ Added {added_papers} papers, {added_entities} extracted entities, {added_edges} causal edges[/green]")


def _add_proteins_to_graph(graph: EpistemicGraph, target: str):
    """Add UniProt proteins to the knowledge graph."""
    try:
        proteins = load_proteins(target)
    except FileNotFoundError:
        console.print("[yellow]⚠ No UniProt data found. Run 'uid ingest' first.[/yellow]")
        return

    added = 0
    for protein in proteins:
        accession = protein.get("accession", "")
        if not accession:
            continue

        node_id = f"protein:{accession}"
        if graph.has_node(node_id):
            continue

        graph.add_node(NodeData(
            node_id=node_id,
            node_type=NodeType.PROTEIN,
            name=protein.get("protein_name", accession),
            description=protein.get("function", ""),
            source=f"UniProt:{accession}",
            confidence=config.CONFIDENCE_CURATED_DB if protein.get("reviewed") else config.CONFIDENCE_STRUCTURED_DB,
            metadata={
                "organism": protein.get("organism", ""),
                "ec_numbers": ", ".join(protein.get("ec_numbers", [])),
                "gene_names": ", ".join(protein.get("gene_names", [])),
                "pdb_ids": ", ".join(protein.get("pdb_ids", [])[:5]),
                "length": protein.get("length", 0),
                "reviewed": protein.get("reviewed", False),
            },
        ))
        added += 1

    console.print(f"[green]  ✓ Added {added} proteins to graph[/green]")


def _add_pathways_to_graph(graph: EpistemicGraph, target: str):
    """Add KEGG pathways to the knowledge graph."""
    try:
        pathways = load_pathways(target)
    except FileNotFoundError:
        console.print("[yellow]⚠ No KEGG data found. Run 'uid ingest' first.[/yellow]")
        return

    added = 0
    for pathway in pathways:
        pw_id = pathway.get("pathway_id", "")
        if not pw_id:
            continue

        node_id = f"pathway:{pw_id}"
        if graph.has_node(node_id):
            continue

        graph.add_node(NodeData(
            node_id=node_id,
            node_type=NodeType.PATHWAY,
            name=pathway.get("name", pw_id),
            description=pathway.get("relevance", pathway.get("description", "")),
            source=f"KEGG:{pw_id}",
            confidence=config.CONFIDENCE_CURATED_DB,
            metadata={
                "gene_count": len(pathway.get("genes", [])),
                "compound_count": len(pathway.get("compounds", [])),
                "organism": pathway.get("organism", ""),
            },
        ))

        # Connect to glucosepane if relevant
        if graph.has_node("mol:glucosepane"):
            graph.add_edge(node_id, "mol:glucosepane", EdgeData(
                edge_type=EdgeType.PART_OF,
                source=f"KEGG:{pw_id}",
                context=pathway.get("relevance", ""),
            ))

        added += 1

    console.print(f"[green]  ✓ Added {added} pathways to graph[/green]")


def _add_chembl_to_graph(graph: EpistemicGraph, target: str):
    """Add ChEMBL compounds and targets to the knowledge graph."""
    try:
        chembl_data = load_chembl_data(target)
    except FileNotFoundError:
        console.print("[yellow]⚠ No ChEMBL data found. Run 'uid ingest' first.[/yellow]")
        return

    added_compounds = 0
    for compound in chembl_data.get("compounds", []):
        chembl_id = compound.get("chembl_id", "")
        if not chembl_id:
            continue

        node_id = f"mol:{chembl_id}"
        if graph.has_node(node_id):
            continue

        name = compound.get("name", "") or chembl_id
        graph.add_node(NodeData(
            node_id=node_id,
            node_type=NodeType.MOLECULE,
            name=name,
            description=f"ChEMBL compound. Type: {compound.get('molecule_type', 'unknown')}",
            source=f"ChEMBL:{chembl_id}",
            confidence=config.CONFIDENCE_STRUCTURED_DB,
            metadata={
                "smiles": compound.get("smiles", ""),
                "molecular_weight": compound.get("molecular_weight", ""),
                "max_phase": compound.get("max_phase", 0),
                "oral": compound.get("oral", False),
            },
        ))
        added_compounds += 1

    console.print(f"[green]  ✓ Added {added_compounds} compounds to graph[/green]")


# ─── Gap Detection & Reporting ───────────────────────────────────────────────────

def cmd_detect_gaps():
    """Run the Negative Space Detector on the current graph."""
    print_banner()
    graph = load_graph()
    causal_chain = build_glucosepane_repair_chain()
    detector = NegativeSpaceDetector(graph)
    gaps = detector.detect_gaps(causal_chain)
    _print_gaps(gaps)
    return graph, gaps


def cmd_report():
    """Generate the epistemic gap report."""
    print_banner()
    graph = load_graph()
    causal_chain = build_glucosepane_repair_chain()
    detector = NegativeSpaceDetector(graph)
    gaps = detector.detect_gaps(causal_chain)
    reporter = GapReporter(graph, gaps)
    report_path = reporter.save_report()
    _print_complete(len(gaps), report_path)


def cmd_pipeline(target: str = "glucosepane"):
    """Run the full pipeline: ingest → build → detect → report."""
    print_banner()
    console.print(f"\n[bold]Full Pipeline: {target}[/bold]\n")

    # Step 1: Ingest
    cmd_ingest(target)

    # Step 2: Build graph
    cmd_build_graph(target)

    # Step 3: Detect gaps
    graph = load_graph()
    causal_chain = build_glucosepane_repair_chain()
    detector = NegativeSpaceDetector(graph)
    gaps = detector.detect_gaps(causal_chain)
    _print_gaps(gaps)

    # Step 4: Generate report
    reporter = GapReporter(graph, gaps)
    report_path = reporter.save_report()
    _print_complete(len(gaps), report_path)


# ─── Helpers ─────────────────────────────────────────────────────────────────────

def _print_gaps(gaps):
    console.print("\n[bold cyan]═══ Detected Epistemic Gaps ═══[/bold cyan]")
    for i, gap in enumerate(gaps, 1):
        color = {"CRITICAL": "red", "HIGH": "yellow", "MEDIUM": "blue", "LOW": "green"}.get(
            gap.priority.value, "white"
        )
        console.print(
            f"  [{color}]{gap.priority.value}[/{color}] "
            f"Gap #{i}: {gap.description[:80]}..."
        )


def _print_complete(gap_count, report_path):
    console.print(Panel.fit(
        f"[bold green]Pipeline complete![/bold green]\n\n"
        f"Gaps found: [bold]{gap_count}[/bold]\n"
        f"Report: {report_path}",
        border_style="green",
    ))


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print_banner()
        console.print("\nUsage: uid <command> [target]\n")
        console.print("Commands:")
        console.print("  [cyan]mock-test[/cyan]      Run full pipeline with mock data")
        console.print("  [cyan]ingest[/cyan]         Ingest data from PubMed, UniProt, KEGG, ChEMBL")
        console.print("  [cyan]build-graph[/cyan]    Build knowledge graph from ingested data")
        console.print("  [cyan]detect-gaps[/cyan]    Run the Negative Space Detector")
        console.print("  [cyan]report[/cyan]         Generate epistemic gap report")
        console.print("  [cyan]pipeline[/cyan]       Run full pipeline (ingest → build → detect → report)")
        console.print("\n  Default target: glucosepane")
        return

    command = sys.argv[1]
    target = sys.argv[2] if len(sys.argv) > 2 else "glucosepane"

    if command == "mock-test":
        cmd_mock_test()
    elif command == "ingest":
        cmd_ingest(target)
    elif command == "build-graph":
        cmd_build_graph(target)
    elif command == "detect-gaps":
        cmd_detect_gaps()
    elif command == "report":
        cmd_report()
    elif command == "pipeline":
        cmd_pipeline(target)
    else:
        console.print(f"[red]Unknown command: {command}[/red]")


if __name__ == "__main__":
    main()

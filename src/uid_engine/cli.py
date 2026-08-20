"""Command-line interface for the Universal Inverse Design Engine.

Usage:
    uid mock-test
    uid ingest        --target glucosepane [--max-papers 500]
    uid build-graph   --target glucosepane
    uid detect-gaps   --target glucosepane [--chain chains/glucosepane.yaml]
    uid report        --target glucosepane [--chain chains/glucosepane.yaml] [--output reports/]
    uid pipeline      --target glucosepane [--chain chains/glucosepane.yaml] [--dry-run]
"""

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from uid_engine.graph.builder import build_mock_glucosepane_graph, EpistemicGraph
from uid_engine.graph.schema import (
    NodeData, NodeType, EdgeData, EdgeType, EvidenceStatus, SENS_DAMAGE_CATEGORIES
)
from uid_engine.graph.store import save_graph, load_graph
from uid_engine.analysis.causal_chains import build_glucosepane_repair_chain
from uid_engine.analysis.gap_detector import NegativeSpaceDetector
from uid_engine.analysis.reporter import GapReporter
from uid_engine.analysis.visualizer import export_interactive_html
from uid_engine.analysis.design_spec import compile_all_specs_for_target
from uid_engine.generative.orchestrator import orchestrate_discovery_for_target
from uid_engine.chains.registry import CausalChainRegistry, ChainValidationError
from uid_engine.ingest.pubmed import ingest_pubmed, load_papers
from uid_engine.ingest.uniprot import ingest_uniprot, load_proteins
from uid_engine.ingest.kegg import ingest_kegg, load_pathways
from uid_engine.ingest.chembl import ingest_chembl, load_chembl_data
from uid_engine.ingest.alphafold import ingest_alphafold, load_alphafold_data
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

def cmd_ingest(target: str = "glucosepane", max_papers: int | None = None):
    """Ingest data from all 4 APIs for a given target."""
    print_banner()
    console.print(f"\n[bold]Phase C: Data Ingestion — {target}[/bold]\n")

    # 1. PubMed
    papers = ingest_pubmed(target, max_results=max_papers)

    # 2. UniProt
    proteins = ingest_uniprot(target)

    # 3. KEGG
    pathways = ingest_kegg(target)

    # 4. ChEMBL
    chembl = ingest_chembl(target)

    # 5. AlphaFold (3D structures & pLDDT confidence for ingested proteins)
    alphafold_models = ingest_alphafold(target)

    # Summary
    console.print(Panel.fit(
        f"[bold green]Ingestion complete![/bold green]\n\n"
        f"PubMed papers: [bold]{len(papers)}[/bold]\n"
        f"UniProt proteins: [bold]{len(proteins)}[/bold]\n"
        f"AlphaFold structures: [bold]{len(alphafold_models)}[/bold]\n"
        f"KEGG pathways: [bold]{len(pathways)}[/bold]\n"
        f"ChEMBL targets: [bold]{len(chembl.get('targets', []))}[/bold]\n"
        f"ChEMBL compounds: [bold]{len(chembl.get('compounds', []))}[/bold]\n"
        f"Bioactivity records: [bold]{len(chembl.get('activities', []))}[/bold]",
        border_style="green",
    ))


# ─── Phase C: Build Graph from Real Data ─────────────────────────────────────────

def cmd_build_graph(target: str = "glucosepane"):
    """Build the knowledge graph from ingested real data.

    Loads the existing graph if one is already saved (incremental merge),
    otherwise seeds from the mock graph which contains manually curated
    SENS categories and core glucosepane facts.
    """
    print_banner()
    console.print(f"\n[bold]Building Knowledge Graph from Real Data — {target}[/bold]\n")

    # Incremental merge: load existing graph if it exists, otherwise seed from mock
    try:
        graph = load_graph()
        console.print("[cyan]  ↺ Loaded existing graph for incremental merge[/cyan]")
    except FileNotFoundError:
        graph = build_mock_glucosepane_graph()
        console.print("[cyan]  ⊕ Seeded from mock graph (first build)[/cyan]")

    # Layer on new real data
    _add_papers_to_graph(graph, target)
    _add_proteins_to_graph(graph, target)
    _add_alphafold_to_graph(graph, target)
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


def _add_alphafold_to_graph(graph: EpistemicGraph, target: str):
    """Enrich protein nodes with AlphaFold 3D structure predictions and pLDDT scores."""
    try:
        models = load_alphafold_data(target)
    except FileNotFoundError:
        console.print("[yellow]⚠ No AlphaFold data found. Run 'uid ingest' first.[/yellow]")
        return

    enriched = 0
    for model in models:
        acc = model.get("uniprot_accession", "")
        if not acc:
            continue

        node_id = f"protein:{acc}"
        if graph.has_node(node_id):
            node_data = graph.get_node(node_id)
            node_data["has_3d_structure"] = True
            node_data["alphafold_plddt"] = float(model.get("mean_plddt", 0.0))
            node_data["alphafold_confidence"] = model.get("confidence_category", "")
            node_data["alphafold_pdb_url"] = model.get("pdb_url", "")
            node_data["alphafold_entry_id"] = model.get("entry_id", "")
            enriched += 1

    console.print(f"[green]  ✓ Enriched {enriched} proteins with AlphaFold 3D structures[/green]")


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

def cmd_detect_gaps(chain=None):
    """Run the Negative Space Detector on the current graph."""
    print_banner()
    graph = load_graph()
    causal_chain = chain or build_glucosepane_repair_chain()
    detector = NegativeSpaceDetector(graph)
    gaps = detector.detect_gaps(causal_chain)
    _print_gaps(gaps)
    return graph, gaps


_TARGET_TO_SENS = {
    "glucosepane": "extracellular_crosslinks",
    "extracellular_crosslinks": "extracellular_crosslinks",
    "senescent_cells": "senescent_cells",
    "mitochondrial_mutations": "mitochondrial_mutations",
}


def cmd_report(target: str = "glucosepane", chain=None, output_dir=None):
    """Generate the epistemic gap report."""
    print_banner()
    graph = load_graph()
    causal_chain = chain or build_glucosepane_repair_chain()
    detector = NegativeSpaceDetector(graph)
    gaps = detector.detect_gaps(causal_chain)

    sens_key = _TARGET_TO_SENS.get(target, target)
    target_config = SENS_DAMAGE_CATEGORIES.get(sens_key)
    target_name = target_config.get("name", target) if target_config else target

    reporter = GapReporter(graph, gaps, target_config=target_config)
    report_path = reporter.save_report(target_name=target_name, output_dir=output_dir)
    _print_complete(len(gaps), report_path)


def cmd_visualize(target: str = "glucosepane", output_path: str | Path | None = None):
    """Generate an interactive HTML visualization of the knowledge graph."""
    print_banner()
    graph = load_graph()
    sens_key = _TARGET_TO_SENS.get(target, target)
    target_config = SENS_DAMAGE_CATEGORIES.get(sens_key)
    target_name = target_config.get("name", target) if target_config else target

    html_path = export_interactive_html(graph, output_path=output_path, target_name=target_name)
    console.print(Panel.fit(
        f"[bold green]Interactive Map Ready![/bold green]\n\n"
        f"Target: [bold]{target_name}[/bold]\n"
        f"File: [cyan]{html_path}[/cyan]\n"
        f"[dim]Open this file in any web browser to explore the epistemic graph.[/dim]",
        border_style="cyan",
    ))


def cmd_generate_specs(target: str = "glucosepane", output_dir: str | Path | None = None):
    """Compile Layer 3 De Novo Design Specifications for critical epistemic gaps."""
    print_banner()
    specs = compile_all_specs_for_target(target, output_dir=output_dir)
    console.print(Panel.fit(
        f"[bold green]Layer 3 Compilation Complete![/bold green]\n\n"
        f"Target: [bold]{target}[/bold]\n"
        f"Compiled Specs: [bold]{len(specs)}[/bold]\n"
        f"[dim]Specs include 3D .sdf conformers and RFdiffusion/ESM-3/ProteinMPNN configs.[/dim]",
        border_style="green",
    ))


def cmd_generate_candidates(
    target: str = "glucosepane",
    num_variants: int = 8,
    min_plddt: float = 80.0,
    output_dir: str | Path | None = None,
):
    """Execute autonomous de novo generative discovery and close the epistemic graph loop."""
    print_banner()
    candidates = orchestrate_discovery_for_target(
        target=target,
        num_variants_per_spec=num_variants,
        min_plddt=min_plddt,
        output_dir=output_dir,
    )
    console.print(Panel.fit(
        f"[bold green]Generative Discovery Complete![/bold green]\n\n"
        f"Target: [bold]{target}[/bold]\n"
        f"Passing Candidates Injected into Graph: [bold]{len(candidates)}[/bold]\n"
        f"[dim]Run 'uid visualize' to view updated graph with HYPOTHESIZED candidate nodes.[/dim]",
        border_style="magenta",
    ))


def cmd_pipeline(target: str = "glucosepane", chain=None, max_papers=None, output_dir=None):
    """Run the full pipeline: ingest → build → detect → report."""
    print_banner()
    console.print(f"\n[bold]Full Pipeline: {target}[/bold]\n")

    # Step 1: Ingest
    cmd_ingest(target, max_papers=max_papers)

    # Step 2: Build graph
    cmd_build_graph(target)

    # Step 3: Detect gaps
    graph = load_graph()
    causal_chain = chain or build_glucosepane_repair_chain()
    detector = NegativeSpaceDetector(graph)
    gaps = detector.detect_gaps(causal_chain)
    _print_gaps(gaps)

    # Step 4: Generate report
    sens_key = _TARGET_TO_SENS.get(target, target)
    target_config = SENS_DAMAGE_CATEGORIES.get(sens_key)
    target_name = target_config.get("name", target) if target_config else target

    reporter = GapReporter(graph, gaps, target_config=target_config)
    report_path = reporter.save_report(target_name=target_name, output_dir=output_dir)
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


def _resolve_chain(chain_arg: str | None, target: str):
    """Resolve a causal chain from a --chain flag or the bundled registry.

    If --chain is an explicit file path, load it directly.
    Otherwise, look up the target name in the bundled chains/ directory.
    Falls back to the hardcoded Python chain for 'glucosepane' if no YAML found.
    """
    registry = CausalChainRegistry()

    if chain_arg:
        path = Path(chain_arg)
        if not path.exists():
            console.print(f"[red]Chain file not found: {chain_arg}[/red]")
            sys.exit(1)
        try:
            return registry.load_from_path(path)
        except ChainValidationError as e:
            console.print(f"[red]Invalid chain file: {e}[/red]")
            sys.exit(1)

    # Try the bundled registry first
    try:
        return registry.load(target)
    except FileNotFoundError:
        # Graceful fallback: Python-built glucosepane chain (legacy)
        if target == "glucosepane":
            console.print(
                "[yellow]No YAML chain found for 'glucosepane' in registry — "
                "using built-in Python chain[/yellow]"
            )
            return build_glucosepane_repair_chain()
        console.print(
            f"[red]No chain found for target '{target}'. "
            f"Create chains/{target}.yaml or use --chain to specify a custom chain.[/red]"
        )
        sys.exit(1)


def main():
    """Main CLI entry point."""
    config.ensure_dirs()

    parser = argparse.ArgumentParser(
        prog="uid",
        description="Universal Inverse Design Engine — Finding what humanity doesn't know",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  uid mock-test
  uid ingest --target glucosepane --max-papers 500
  uid build-graph --target glucosepane
  uid detect-gaps --target glucosepane
  uid detect-gaps --target senescent_cells --chain chains/senescent_cells.yaml
  uid report --target glucosepane --output reports/
  uid pipeline --target glucosepane --dry-run
""",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    subparsers.required = True

    # ── Shared arguments ──────────────────────────────────────────────────
    def add_target(p):
        p.add_argument(
            "--target", "-t",
            default="glucosepane",
            metavar="NAME",
            help="Research target (default: glucosepane)",
        )

    def add_chain(p):
        p.add_argument(
            "--chain", "-c",
            default=None,
            metavar="PATH",
            help="Path to a YAML causal chain file (default: auto-detect from target)",
        )

    def add_output(p):
        p.add_argument(
            "--output", "-o",
            default=None,
            metavar="DIR",
            help="Output directory for reports (default: reports/)",
        )

    # ── Subcommands ───────────────────────────────────────────────────────
    # mock-test
    p_mock = subparsers.add_parser(
        "mock-test",
        help="Run full pipeline with mock data (Phase A/B integration test)",
    )

    # ingest
    p_ingest = subparsers.add_parser(
        "ingest",
        help="Ingest data from PubMed, UniProt, KEGG, and ChEMBL",
    )
    add_target(p_ingest)
    p_ingest.add_argument(
        "--max-papers", "-n",
        type=int,
        default=None,
        metavar="N",
        help="Maximum PubMed papers to retrieve (default: config.MAX_PAPERS)",
    )
    p_ingest.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be ingested without making API calls",
    )

    # build-graph
    p_build = subparsers.add_parser(
        "build-graph",
        help="Build / incrementally update the knowledge graph from ingested data",
    )
    add_target(p_build)

    # detect-gaps
    p_detect = subparsers.add_parser(
        "detect-gaps",
        help="Run the Negative Space Detector and print detected epistemic gaps",
    )
    add_target(p_detect)
    add_chain(p_detect)

    # report
    p_report = subparsers.add_parser(
        "report",
        help="Generate a Markdown epistemic gap report",
    )
    add_target(p_report)
    add_chain(p_report)
    add_output(p_report)

    # visualize
    p_vis = subparsers.add_parser(
        "visualize",
        help="Export an interactive HTML Cytoscape map of the knowledge graph",
    )
    add_target(p_vis)
    add_output(p_vis)

    # generate-specs
    p_specs = subparsers.add_parser(
        "generate-specs",
        help="Compile Layer 3 De Novo Design Specs (3D conformers & generative ML configs) for gaps",
    )
    add_target(p_specs)
    add_output(p_specs)

    # generate-candidates
    p_cands = subparsers.add_parser(
        "generate-candidates",
        help="Run generative inverse folding loop (ESM-3 + ProteinMPNN) and inject into graph",
    )
    add_target(p_cands)
    add_output(p_cands)
    p_cands.add_argument(
        "--num-variants", "-v",
        type=int,
        default=8,
        help="Number of sequence variants per design spec (default: 8)",
    )
    p_cands.add_argument(
        "--min-plddt",
        type=float,
        default=80.0,
        help="Minimum pLDDT threshold for passing candidates (default: 80.0)",
    )

    # pipeline
    p_pipeline = subparsers.add_parser(
        "pipeline",
        help="Run the full pipeline: ingest → build-graph → detect-gaps → report",
    )
    add_target(p_pipeline)
    add_chain(p_pipeline)
    add_output(p_pipeline)
    p_pipeline.add_argument(
        "--max-papers", "-n",
        type=int,
        default=None,
        metavar="N",
        help="Maximum PubMed papers to retrieve",
    )
    p_pipeline.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the pipeline without making API calls or writing files",
    )

    args = parser.parse_args()

    # ── Dispatch ──────────────────────────────────────────────────────────
    if args.command == "mock-test":
        cmd_mock_test()

    elif args.command == "ingest":
        if getattr(args, "dry_run", False):
            console.print(f"[dim]Dry run: would ingest '{args.target}' "
                          f"(max_papers={args.max_papers or config.MAX_PAPERS})[/dim]")
        else:
            cmd_ingest(args.target, max_papers=getattr(args, "max_papers", None))

    elif args.command == "build-graph":
        cmd_build_graph(args.target)

    elif args.command == "detect-gaps":
        chain = _resolve_chain(getattr(args, "chain", None), args.target)
        cmd_detect_gaps(chain=chain)

    elif args.command == "report":
        chain = _resolve_chain(getattr(args, "chain", None), args.target)
        cmd_report(target=args.target, chain=chain, output_dir=getattr(args, "output", None))

    elif args.command == "visualize":
        cmd_visualize(target=args.target, output_path=getattr(args, "output", None))

    elif args.command == "generate-specs":
        cmd_generate_specs(target=args.target, output_dir=getattr(args, "output", None))

    elif args.command == "generate-candidates":
        cmd_generate_candidates(
            target=args.target,
            num_variants=getattr(args, "num_variants", 8),
            min_plddt=getattr(args, "min_plddt", 80.0),
            output_dir=getattr(args, "output", None),
        )

    elif args.command == "pipeline":
        if getattr(args, "dry_run", False):
            chain = _resolve_chain(getattr(args, "chain", None), args.target)
            nodes = len([])
            console.print(
                f"[dim]Dry run: would run full pipeline for '{args.target}' "
                f"using chain '{chain.node_id}'[/dim]"
            )
        else:
            chain = _resolve_chain(getattr(args, "chain", None), args.target)
            cmd_pipeline(
                args.target,
                chain=chain,
                max_papers=getattr(args, "max_papers", None),
                output_dir=getattr(args, "output", None),
            )


if __name__ == "__main__":
    main()

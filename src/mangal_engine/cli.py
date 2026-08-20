"""Project Mangal — Unified Command-Line Interface.

Commands:
    mangal matrix          Inspect tensor dimensions and sample coordinates
    mangal interrogate     Interrogate a problem through the multi-gate sieve
    mangal distill         Distill the irreducible Axiom & Root Cause
    mangal challenge       Run the 4-vector Axiomatic Challenge Protocol
    mangal compile-chain   Autonomously compile problem -> YAML causal chain
    mangal run             Master closed-loop execution (Mangal -> UID Engine)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mangal_engine.compiler.chain_writer import ChainWriter
from mangal_engine.distiller.axiom_distiller import AxiomDistiller
from mangal_engine.distiller.clusterer import SemanticClusterer
from mangal_engine.interrogator.evaluator import InterrogationEvaluator
from mangal_engine.interrogator.sieve import InterrogationSieve
from mangal_engine.matrix.dimensions import ArchetypeLens, CoreElement, CognitiveOperation, ScaleShift
from mangal_engine.matrix.tensor import InterrogationTensor, MatrixScale
from mangal_engine.mutation.axiomatic_challenge import AxiomaticChallengeEngine

console = Console()


def cmd_matrix(args: argparse.Namespace) -> None:
    """Inspect matrix dimensions and sample coordinates."""
    scale_map = {
        "1k": MatrixScale.SCALE_1K,
        "10k": MatrixScale.SCALE_10K,
        "100k": MatrixScale.SCALE_100K,
    }
    scale = scale_map.get(args.scale, MatrixScale.SCALE_10K)
    tensor = InterrogationTensor(scale)

    console.print(Panel(
        f"[bold cyan]Project Mangal — Tensor Matrix Inspector[/bold cyan]\n"
        f"Selected Scale: [bold green]{scale.value}[/bold green]\n"
        f"Total Search Space: [bold yellow]{tensor.total_theoretical_combinations:,} Vectors[/bold yellow]",
        title="[bold yellow]Matrix Dimensions[/bold yellow]",
        border_style="cyan",
    ))

    table = Table(title="Sampled Multi-Dimensional Vectors", border_style="cyan")
    table.add_column("Coord ID", style="bold cyan")
    table.add_column("Archetype (W)", style="magenta")
    table.add_column("Element (X)", style="blue")
    table.add_column("Operation (Y)", style="yellow")
    table.add_column("Scale (Z)", style="green")

    samples = tensor.sample_diverse_coordinates(count=args.count, seed=args.seed)
    for s in samples:
        w_val = s.archetype.name if s.archetype else "N/A"
        table.add_row(s.coordinate_id, w_val, s.element.name, s.operation.name, s.scale.name)

    console.print(table)


def cmd_interrogate(args: argparse.Namespace) -> None:
    """Run multi-gate interrogation on a target problem."""
    scale_map = {
        "1k": MatrixScale.SCALE_1K,
        "10k": MatrixScale.SCALE_10K,
        "100k": MatrixScale.SCALE_100K,
    }
    scale = scale_map.get(args.scale, MatrixScale.SCALE_10K)
    tensor = InterrogationTensor(scale)
    sieve = InterrogationSieve()

    console.print(f"[bold cyan]Interrogating target:[/bold cyan] [bold white]'{args.target}'[/bold white]")
    console.print(f"[dim]Generating {args.sample_size} coordinate inquiries across {scale.value}...[/dim]")

    coords = tensor.sample_diverse_coordinates(count=args.sample_size, seed=42)
    inquiries = [tensor.synthesize_inquiry(c, args.target) for c in coords]
    scored = sieve.sieve_inquiries(inquiries, top_k=args.top_k)

    console.print(f"[bold green]✓ Sieve complete:[/bold green] Extracted {len(scored)} high-leverage inquiries.\n")

    table = Table(title=f"Top {len(scored)} High-Leverage Inquiries for '{args.target}'", border_style="cyan")
    table.add_column("#", style="dim")
    table.add_column("Vector ID", style="bold cyan")
    table.add_column("Impact", style="bold yellow")
    table.add_column("Diagnostic Inquiry", style="white")

    for idx, s in enumerate(scored, 1):
        table.add_row(
            str(idx),
            s.inquiry.coordinate.coordinate_id,
            f"{s.total_impact_score:.3f}",
            s.inquiry.inquiry_text,
        )

    console.print(table)


def cmd_distill(args: argparse.Namespace) -> None:
    """Distill the irreducible Axiom & Root Cause from matrix evaluations."""
    tensor = InterrogationTensor(MatrixScale.SCALE_10K)
    sieve = InterrogationSieve()
    evaluator = InterrogationEvaluator()
    clusterer = SemanticClusterer()
    distiller = AxiomDistiller()

    console.print(f"[bold cyan]Distilling Axiom for:[/bold cyan] [bold white]'{args.target}'[/bold white]")

    coords = tensor.sample_diverse_coordinates(count=50, seed=42)
    inquiries = [tensor.synthesize_inquiry(c, args.target) for c in coords]
    scored = sieve.sieve_inquiries(inquiries, top_k=20)
    solutions = evaluator.evaluate_batch(scored)
    clusters = clusterer.cluster_solutions(solutions)
    axiom = distiller.distill_axiom(args.target, clusters)

    console.print(Panel(
        f"[bold white]{axiom.core_axiom_statement}[/bold white]\n\n"
        f"Category: [bold yellow]{axiom.root_cause_category}[/bold yellow] | "
        f"Confidence: [bold green]{axiom.confidence_score*100:.1f}%[/bold green] | "
        f"Clusters: [bold cyan]{axiom.supporting_cluster_count}[/bold cyan]\n\n"
        f"[dim]{axiom.summary_rationale}[/dim]",
        title=f"[bold green]The Distilled Axiom ({axiom.axiom_id})[/bold green]",
        border_style="green",
    ))


def cmd_challenge(args: argparse.Namespace) -> None:
    """Run the 4-vector Axiomatic Challenge Protocol."""
    distiller = AxiomDistiller()
    clusterer = SemanticClusterer()
    engine = AxiomaticChallengeEngine()

    dummy_clusters = clusterer.cluster_solutions([])
    axiom = distiller.distill_axiom(args.axiom, dummy_clusters)
    hypotheses = engine.challenge_axiom(axiom)

    console.print(Panel(
        f"Original Axiom: [bold white]{axiom.core_axiom_statement}[/bold white]",
        title="[bold yellow]Axiomatic Challenge Protocol[/bold yellow]",
        border_style="yellow",
    ))

    table = Table(title="4-Vector Breakthrough Hypotheses", border_style="cyan")
    table.add_column("Vector", style="bold cyan")
    table.add_column("Breakthrough Mechanism", style="white")
    table.add_column("Prerequisite Key", style="bold green")

    for h in hypotheses:
        table.add_row(h.vector.value.split("(")[0].strip(), h.breakthrough_mechanism, h.required_prerequisite_id)

    console.print(table)


def cmd_compile_chain(args: argparse.Namespace) -> None:
    """Autonomously compile a seed problem into a production YAML causal chain."""
    tensor = InterrogationTensor(MatrixScale.SCALE_10K)
    sieve = InterrogationSieve()
    evaluator = InterrogationEvaluator()
    clusterer = SemanticClusterer()
    distiller = AxiomDistiller()
    challenge_engine = AxiomaticChallengeEngine()
    writer = ChainWriter()

    console.print(f"[bold cyan]Autonomously compiling causal chain for:[/bold cyan] [bold white]'{args.target}'[/bold white]")

    # Pipeline execution
    coords = tensor.sample_diverse_coordinates(count=40, seed=42)
    inquiries = [tensor.synthesize_inquiry(c, args.target) for c in coords]
    scored = sieve.sieve_inquiries(inquiries, top_k=20)
    solutions = evaluator.evaluate_batch(scored)
    clusters = clusterer.cluster_solutions(solutions)
    axiom = distiller.distill_axiom(args.target, clusters)
    hypotheses = challenge_engine.challenge_axiom(axiom)

    out_dir = args.output or "src/uid_engine/chains"
    result = writer.compile_chain(args.target, axiom, hypotheses, output_dir=out_dir)

    status_str = "[bold green]VALIDATED ✓[/bold green]" if result.is_valid else "[bold red]VALIDATION FAILED ✗[/bold red]"

    console.print(Panel(
        f"Target Slug: [bold cyan]{result.target_slug}[/bold cyan]\n"
        f"Output Path: [bold yellow]{result.file_path}[/bold yellow]\n"
        f"Tree Nodes: [bold white]{result.node_count}[/bold white]\n"
        f"Schema Status: {status_str}",
        title="[bold green]Chain Compilation Complete[/bold green]",
        border_style="green",
    ))


def cmd_run(args: argparse.Namespace) -> None:
    """Master loop: Run Project Mangal -> UID Engine end-to-end."""
    cmd_compile_chain(args)
    console.print("\n[bold cyan]Project Mangal cognitive pass complete.[/bold cyan]")
    console.print("[dim]You can now run: [bold white]uid detect-gaps --target " + args.target.lower().replace(" ", "_") + "[/bold white][/dim]")


def main() -> None:
    """Entry point for the mangal CLI."""
    parser = argparse.ArgumentParser(
        prog="mangal",
        description="Project Mangal — Cognitive Interrogation Matrix & Autonomous Causal Compiler",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # mangal matrix
    p_matrix = subparsers.add_parser("matrix", help="Inspect matrix dimensions and sample coordinates")
    p_matrix.add_argument("--scale", choices=["1k", "10k", "100k"], default="10k")
    p_matrix.add_argument("--count", type=int, default=10)
    p_matrix.add_argument("--seed", type=int, default=None)
    p_matrix.set_defaults(func=cmd_matrix)

    # mangal interrogate
    p_interrogate = subparsers.add_parser("interrogate", help="Interrogate a target problem through the matrix")
    p_interrogate.add_argument("--target", type=str, required=True, help="Seed problem or status quo")
    p_interrogate.add_argument("--scale", choices=["1k", "10k", "100k"], default="10k")
    p_interrogate.add_argument("--sample-size", type=int, default=50)
    p_interrogate.add_argument("--top-k", type=int, default=10)
    p_interrogate.set_defaults(func=cmd_interrogate)

    # mangal distill
    p_distill = subparsers.add_parser("distill", help="Distill the irreducible Axiom & Root Cause")
    p_distill.add_argument("--target", type=str, required=True, help="Seed problem or status quo")
    p_distill.set_defaults(func=cmd_distill)

    # mangal challenge
    p_challenge = subparsers.add_parser("challenge", help="Run the 4-vector Axiomatic Challenge Protocol")
    p_challenge.add_argument("--axiom", type=str, required=True, help="Axiom statement to challenge")
    p_challenge.set_defaults(func=cmd_challenge)

    # mangal compile-chain
    p_compile = subparsers.add_parser("compile-chain", help="Compile problem into YAML causal chain")
    p_compile.add_argument("--target", type=str, required=True, help="Seed problem or status quo")
    p_compile.add_argument("--output", type=str, default="src/uid_engine/chains", help="Output directory")
    p_compile.set_defaults(func=cmd_compile_chain)

    # mangal run
    p_run = subparsers.add_parser("run", help="Master autonomous discovery loop (Mangal -> UID)")
    p_run.add_argument("--target", type=str, required=True, help="Seed problem or status quo")
    p_run.add_argument("--output", type=str, default="src/uid_engine/chains", help="Output directory")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

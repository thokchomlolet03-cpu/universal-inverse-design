"""Generative Inference Orchestrator — Executes the discovery loop and closes the epistemic cycle.

Orchestrates:
1. De Novo Spec Loading (Substrate 3D coordinates + Active site constraints)
2. ESM-3 / ProteinMPNN inverse folding sequence generation
3. 4-Gate In Silico Quality Control Screening (pLDDT, scRMSD, GRAVY solubility)
4. FASTA and 3D PDB structure export
5. Graph Loop Closure (Injecting HYPOTHESIZED candidates into the Epistemic Knowledge Graph)
"""

import json
from pathlib import Path
from typing import Optional, Any
from rich.console import Console

from uid_engine import config
from uid_engine.analysis.design_spec import DeNovoDesignSpec, compile_all_specs_for_target
from uid_engine.generative.candidate_model import CandidateProtein
from uid_engine.generative.protein_mpnn import (
    design_sequences_with_fixed_motifs,
    generate_candidate_pdb_structure,
)
from uid_engine.generative.esm_adapter import ESMGenerativeAdapter
from uid_engine.generative.screening import screen_candidate_sequence
from uid_engine.graph.builder import EpistemicGraph
from uid_engine.graph.schema import NodeData, NodeType, EdgeData, EdgeType, EvidenceStatus
from uid_engine.graph.store import load_graph, save_graph

console = Console()


def run_generative_pipeline_for_spec(
    spec: DeNovoDesignSpec,
    num_variants: int = 8,
    min_plddt: float = 80.0,
    max_sc_rmsd: float = 2.0,
    output_dir: Optional[Path | str] = None,
    seed: int = 42,
) -> list[CandidateProtein]:
    """Execute sequence generation and in silico screening for a single Design Spec.

    Args:
        spec: Layer 3 De Novo Design Specification.
        num_variants: Number of sequence variants to design.
        min_plddt: Minimum pLDDT score for passing screening (Gate 1).
        max_sc_rmsd: Maximum acceptable scRMSD in Å (Gate 2).
        output_dir: Directory for candidate output files.
        seed: Random seed for reproducibility.

    Returns:
        List of generated CandidateProtein objects (both passed and failed).
    """
    out_dir = Path(output_dir) if output_dir else config.PROJECT_ROOT / "data" / "candidates" / spec.target_name.lower().replace(" ", "_")
    out_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold cyan]═══ Generative Inference: {spec.spec_id} ═══[/bold cyan]")
    console.print(f"[dim]Substrate: {spec.substrate_name} | Target pLDDT: ≥{min_plddt}[/dim]\n")

    adapter = ESMGenerativeAdapter(seed=seed)

    # 1. Map target catalytic residues
    catalytic_map = {"H54": "H", "D112": "D", "S198": "S"}  # Default canonical catalytic triad
    target_length = 240  # Standard globular catalytic domain length

    # 2. Design sequences via ProteinMPNN inverse folding
    sequences = design_sequences_with_fixed_motifs(
        target_length=target_length,
        catalytic_residues=catalytic_map,
        num_variants=num_variants,
        sampling_temp=spec.proteinmpnn_config.get("sampling_temp", 0.1),
        seed=seed,
    )

    candidates = []

    for idx, seq in enumerate(sequences, 1):
        cand_id = f"CAND-{spec.spec_id.replace('SPEC-', '')}-v{idx:02d}"

        # 3. Evaluate self-consistency foldability (ESMFold simulation)
        plddt, ptm, sc_rmsd = adapter.evaluate_self_consistency_fold(seq, spec)

        # 4. Multi-gate in silico screening (including Gate 4 GRAVY solubility)
        props, screening = screen_candidate_sequence(
            sequence=seq,
            predicted_plddt=plddt,
            sc_rmsd=sc_rmsd,
            expected_catalytic_residues=catalytic_map,
            min_plddt=min_plddt,
            max_sc_rmsd=max_sc_rmsd,
        )

        pdb_file = out_dir / f"{cand_id}.pdb"
        fasta_file = out_dir / f"{cand_id}.fasta"
        json_file = out_dir / f"{cand_id}.json"

        # Generate PDB coordinates
        generate_candidate_pdb_structure(seq, pdb_file, plddt_score=plddt)

        candidate = CandidateProtein(
            candidate_id=cand_id,
            target_spec_id=spec.spec_id,
            target_domain=spec.target_name,
            causal_gap_id=spec.causal_gap_id,
            sequence=seq,
            length=len(seq),
            predicted_plddt=plddt,
            predicted_ptm=ptm,
            sc_rmsd=sc_rmsd,
            catalytic_residues=catalytic_map,
            biophysical_properties=props,
            screening_result=screening,
            pdb_path=str(pdb_file),
            fasta_path=str(fasta_file),
        )

        # Write FASTA and JSON
        fasta_file.write_text(candidate.to_fasta(), encoding="utf-8")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(candidate.to_dict(), f, indent=2, ensure_ascii=False)

        status_tag = "[bold green]PASSED[/bold green]" if screening.passed else "[bold red]FAILED[/bold red]"
        console.print(
            f"  • {cand_id}: {status_tag} | pLDDT: {plddt:.1f} | scRMSD: {sc_rmsd:.2f}Å | GRAVY: {props.gravy_score:.2f}"
        )
        candidates.append(candidate)

    return candidates


def inject_candidate_into_graph(
    candidate: CandidateProtein,
    graph: EpistemicGraph,
) -> None:
    """Close the epistemic loop: inject a validated candidate protein into the graph.

    Converts an empty Negative Space gap into a testable HYPOTHESIZED solution node.
    """
    node_id = f"protein:{candidate.candidate_id.lower()}"

    # Add candidate node
    graph.add_node(NodeData(
        node_id=node_id,
        node_type=NodeType.PROTEIN,
        name=candidate.candidate_id,
        description=(
            f"De novo designed candidate enzyme resolving gap {candidate.causal_gap_id}. "
            f"Predicted pLDDT: {candidate.predicted_plddt:.1f}, scRMSD: {candidate.sc_rmsd:.2f}Å, "
            f"GRAVY: {candidate.biophysical_properties.gravy_score:.2f}."
        ),
        source=f"DeNovoDesign:{candidate.generation_model}",
        confidence=0.5,  # Hypothesized candidate confidence
        metadata={
            "target_spec_id": candidate.target_spec_id,
            "plddt": candidate.predicted_plddt,
            "ptm": candidate.predicted_ptm,
            "sc_rmsd": candidate.sc_rmsd,
            "gravy_score": candidate.biophysical_properties.gravy_score,
            "pdb_path": candidate.pdb_path or "",
            "fasta_path": candidate.fasta_path or "",
            "sequence_length": candidate.length,
            "is_de_novo_candidate": True,
        },
    ))

    # Connect candidate with a functional degradation/inhibition edge
    target_node = None
    if "glucosepane" in candidate.target_domain.lower():
        if graph.has_node("mol:glucosepane"):
            target_node = "mol:glucosepane"
        elif graph.has_node("glucosepane"):
            target_node = "glucosepane"
    elif "senescent" in candidate.target_domain.lower():
        if graph.has_node("sens:cellular_senescence"):
            target_node = "sens:cellular_senescence"
        elif graph.has_node("senescent_cells"):
            target_node = "senescent_cells"

    edge_type = EdgeType.DEGRADES if ("glucosepane" in candidate.target_domain.lower()) else EdgeType.INHIBITS

    if target_node and graph.has_node(target_node):
        graph.add_edge(
            node_id,
            target_node,
            EdgeData(
                edge_type=edge_type,
                status=EvidenceStatus.HYPOTHESIZED_IN_SILICO,
                confidence=0.5,
                source=f"DeNovoDesign:{candidate.generation_model}",
                context=f"In silico designed candidate addressing {candidate.causal_gap_id}",
            ),
        )


def orchestrate_discovery_for_target(
    target: str,
    num_variants_per_spec: int = 8,
    min_plddt: float = 80.0,
    output_dir: Optional[Path | str] = None,
) -> list[CandidateProtein]:
    """Top-level autonomous discovery orchestrator:
    Compile specs -> generate candidate molecules -> screen quality -> inject into graph.
    """
    console.print(f"\n[bold magenta]═════════════════════════════════════════════════════════════════[/bold magenta]")
    console.print(f"[bold magenta]  Autonomous De Novo Discovery Orchestrator: {target.upper()}[/bold magenta]")
    console.print(f"[bold magenta]═════════════════════════════════════════════════════════════════[/bold magenta]\n")

    # Step 1: Compile all Layer 3 specs for priority gaps
    specs = compile_all_specs_for_target(target)
    if not specs:
        console.print("[yellow]No critical specs found requiring de novo candidate generation.[/yellow]")
        return []

    # Step 2: Load current knowledge graph
    graph = load_graph()

    all_passed_candidates = []

    # Step 3: Run generative loop for each specification
    for spec in specs:
        candidates = run_generative_pipeline_for_spec(
            spec,
            num_variants=num_variants_per_spec,
            min_plddt=min_plddt,
            output_dir=output_dir,
        )

        passed = [c for c in candidates if c.screening_result.passed]
        all_passed_candidates.extend(passed)

        # Step 4: Inject passing candidates into knowledge graph
        for p in passed:
            inject_candidate_into_graph(p, graph)

    # Step 5: Save updated knowledge graph with closed loop
    save_graph(graph)
    console.print(
        f"\n[bold green]✓ Closed Epistemic Loop: Injected {len(all_passed_candidates)} passing candidates into graph![/bold green]"
    )
    return all_passed_candidates

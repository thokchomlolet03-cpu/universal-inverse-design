"""Layer 3 De Novo Design Spec Compiler — Bridges epistemic gaps to generative models.

Translates identified Negative Space gaps (e.g., missing glucosepane hydrolase,
PROTAC senolytics, or mitochondrial targeting sequences) into concrete,
machine-actionable 3D Design Specifications ready for generative diffusion models
(RFdiffusion All-Atom, ESM-3, ProteinMPNN).

Key Capability:
Uses RDKit to compute 3D spatial conformer coordinates (.sdf) from 1D SMILES,
enabling true 3D geometric flow matching and active-site pocket conditioning.
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Any

from rich.console import Console

from uid_engine import config
from uid_engine.analysis.gap_detector import EpistemicGap
from uid_engine.graph.builder import EpistemicGraph
from uid_engine.graph.schema import GapPriority, NodeType

console = Console()

# Curated substrate chemical structures for known SENS targets
KNOWN_TARGET_SUBSTRATES = {
    "glucosepane": {
        "name": "Glucosepane",
        "smiles": "NCCCC(N)C(=O)O.NC(CCC1=NC=C(NC1)CCCC(N)C(=O)O)C(=O)O",
        "description": "Crosslink formed between lysine and arginine residues on collagen/elastin.",
        "catalytic_goal": "Selective amidine/imidazole ring hydrolysis preserving native peptide backbone.",
    },
    "senescent_cells": {
        "name": "Navitoclax (ABT-263) / BCL-xL Ligand Core",
        "smiles": "CC1(CCC(=C(C1)C2=CC=C(C=C2)Cl)CN3CCN(CC3)C4=CC=C(C=C4)C(=O)NS(=O)(=O)C5=CC(=C(C=C5)N(CC6=CC=CC=C6)C7=CC=CC=C7)[N+](=O)[O-])C",
        "description": "Potent BCL-2 and BCL-xL inhibitor core for senolytic PROTAC design.",
        "catalytic_goal": "Selective degradation of BCL-xL in senescent cells avoiding platelet toxicity.",
    },
    "mitochondrial_mutations": {
        "name": "DddA Cytosine Base Editor Core Ligand / Target Motif",
        "smiles": "NC1=NC(=O)N(C=C1)[C@H]2C[C@H](O)[C@@H](CO)O2",
        "description": "Deoxycytidine target motif for double-stranded DNA deamination in mtDNA.",
        "catalytic_goal": "Targeted C-to-T transition without double-strand breaks in mtDNA.",
    },
}


@dataclass
class HomologousScaffold:
    """A known protein scaffold retrieved from the epistemic graph to guide design."""
    uniprot_accession: str
    name: str
    plddt_score: Optional[float] = None
    alphafold_pdb_url: Optional[str] = None
    confidence_tier: Optional[str] = None


@dataclass
class DeNovoDesignSpec:
    """Complete 3D engineering specification for generative protein design."""
    spec_id: str
    target_name: str
    causal_gap_id: str
    gap_priority: str
    gap_description: str
    substrate_name: str
    substrate_smiles: str
    substrate_3d_sdf_path: Optional[str]
    substrate_molecular_weight: Optional[float]
    substrate_formula: Optional[str]
    target_plddt_minimum: float
    target_pocket_volume_angstrom3: str
    suggested_catalytic_motifs: list[str]
    homologous_scaffolds: list[dict]
    rfdiffusion_all_atom_flags: dict[str, Any]
    esm3_prompt_config: dict[str, Any]
    proteinmpnn_config: dict[str, Any]

    def to_dict(self) -> dict:
        return asdict(self)


# ─── Cheminformatics: 3D Conformer Generation ──────────────────────────────────

def generate_3d_ligand_conformer(
    smiles: str,
    output_path: Path | str,
) -> Optional[Path]:
    """Generate 3D spatial conformer coordinates from a 1D SMILES string using RDKit.

    Generates atomic Euclidean coordinates (.sdf) required by RFdiffusion All-Atom
    for geometric flow matching and pocket scaffolding.

    Args:
        smiles: 1D chemical SMILES representation.
        output_path: Filepath where .sdf conformer will be saved.

    Returns:
        Path to saved .sdf file, or None if generation failed.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem, Descriptors, rdMolDescriptors

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            console.print(f"[yellow]⚠ RDKit could not parse SMILES: {smiles}[/yellow]")
            return None

        # Add explicit hydrogens for 3D physics
        mol_with_h = Chem.AddHs(mol)

        # Generate 3D conformer using ETKDG algorithm (Experimental-Torsion Knowledge Distance Geometry)
        params = AllChem.ETKDGv3()
        params.randomSeed = 42
        embed_result = AllChem.EmbedMolecule(mol_with_h, params)

        if embed_result == -1:
            # Fallback to standard embedding if v3 fails on complex macrocycle
            AllChem.EmbedMolecule(mol_with_h, useRandomCoords=True)

        # Energy minimize conformer with Universal Force Field (UFF) or MMFF
        try:
            AllChem.MMFFOptimizeMolecule(mol_with_h, maxIters=500)
        except Exception:
            AllChem.UFFOptimizeMolecule(mol_with_h, maxIters=500)

        # Write out .sdf conformer
        writer = Chem.SDWriter(str(output_path))
        writer.write(mol_with_h)
        writer.close()

        console.print(f"[green]  ✓ Generated 3D ligand conformer (.sdf) at {output_path}[/green]")
        return output_path

    except ImportError:
        console.print("[yellow]⚠ RDKit not installed. Writing mock coordinate stub.[/yellow]")
        output_path.write_text(f"# 3D Conformer stub for SMILES: {smiles}\n", encoding="utf-8")
        return output_path
    except Exception as e:
        console.print(f"[yellow]⚠ Failed to generate 3D conformer: {e}[/yellow]")
        return None


def calculate_molecular_properties(smiles: str) -> tuple[Optional[float], Optional[str]]:
    """Compute molecular weight and chemical formula from SMILES using RDKit."""
    try:
        from rdkit import Chem
        from rdkit.Chem import Descriptors, rdMolDescriptors

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None, None
        mw = round(Descriptors.ExactMolWt(mol), 2)
        formula = rdMolDescriptors.CalcMolFormula(mol)
        return mw, formula
    except Exception:
        return None, None


# ─── Spec Compiler ─────────────────────────────────────────────────────────────

def compile_design_spec_for_gap(
    gap: EpistemicGap,
    graph: EpistemicGraph,
    target: str = "glucosepane",
    output_dir: Optional[Path | str] = None,
) -> DeNovoDesignSpec:
    """Compile a single EpistemicGap into a complete Layer 3 De Novo Design Spec.

    Args:
        gap: The detected EpistemicGap.
        graph: The EpistemicGraph (used to search closest AlphaFold scaffolds).
        target: Biological target identifier.
        output_dir: Directory for storing output .sdf and spec files.
    """
    out_dir = Path(output_dir) if output_dir else config.PROJECT_ROOT / "data" / "specs"
    out_dir.mkdir(parents=True, exist_ok=True)

    spec_id = f"SPEC-{target.upper()}-{gap.causal_node_id.replace(':', '-').upper()}"

    # 1. Chemical substrate retrieval
    substrate_info = KNOWN_TARGET_SUBSTRATES.get(target, {
        "name": f"{target.capitalize()} Target Substrate",
        "smiles": "C1=CC=C(C=C1)C=O",
        "description": "General substrate representation.",
        "catalytic_goal": gap.description,
    })

    smiles = substrate_info["smiles"]
    sdf_path = out_dir / f"{spec_id}_substrate_3d.sdf"
    generated_sdf = generate_3d_ligand_conformer(smiles, sdf_path)
    mw, formula = calculate_molecular_properties(smiles)

    # 2. Extract closest homologous AlphaFold scaffolds from epistemic graph
    scaffolds = []
    for node_id, data in graph.graph.nodes(data=True):
        if data.get("node_type") == NodeType.PROTEIN.value and data.get("has_3d_structure"):
            scaffolds.append({
                "uniprot_accession": node_id.replace("protein:", ""),
                "name": data.get("name", node_id),
                "plddt_score": data.get("alphafold_plddt"),
                "alphafold_pdb_url": data.get("alphafold_pdb_url"),
                "confidence_tier": data.get("alphafold_confidence"),
            })

    # Sort scaffolds by highest pLDDT score
    scaffolds.sort(key=lambda s: s.get("plddt_score") or 0.0, reverse=True)
    top_scaffolds = scaffolds[:3]

    # 3. Formulate generative toolchain configs
    rfdiffusion_flags = {
        "model": "RFdiffusion_AllAtom_v1",
        "input_ligand_sdf": str(generated_sdf) if generated_sdf else str(sdf_path),
        "target_pocket_conditioning": True,
        "num_designs": 100,
        "diffusion_steps": 50,
        "catalytic_site_clash_penalty": 2.5,
    }

    esm3_prompt_config = {
        "model": "esmc-600m",
        "task": "active_site_scaffolding",
        "target_plddt_min": 85.0,
        "sampling_temperature": 0.2,
        "num_iterations": 3,
    }

    proteinmpnn_config = {
        "model": "protein_mpnn_v48_020",
        "sampling_temp": 0.1,
        "backbone_noise": 0.02,
        "num_sequences_per_target": 8,
    }

    spec = DeNovoDesignSpec(
        spec_id=spec_id,
        target_name=substrate_info["name"],
        causal_gap_id=gap.causal_node_id,
        gap_priority=gap.priority.value,
        gap_description=gap.description,
        substrate_name=substrate_info["name"],
        substrate_smiles=smiles,
        substrate_3d_sdf_path=str(generated_sdf) if generated_sdf else str(sdf_path),
        substrate_molecular_weight=mw,
        substrate_formula=formula,
        target_plddt_minimum=85.0,
        target_pocket_volume_angstrom3="450 - 750 Å³",
        suggested_catalytic_motifs=["His-Asp-Ser", "Glu-His-Asp", "Cys-His-Glu"],
        homologous_scaffolds=top_scaffolds,
        rfdiffusion_all_atom_flags=rfdiffusion_flags,
        esm3_prompt_config=esm3_prompt_config,
        proteinmpnn_config=proteinmpnn_config,
    )

    return spec


# ─── Exporters ─────────────────────────────────────────────────────────────────

def export_spec_json(spec: DeNovoDesignSpec, output_path: Path | str) -> Path:
    """Save Design Spec as structured JSON for programmatic ingestion by ML pipelines."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(spec.to_dict(), f, indent=2, ensure_ascii=False)
    console.print(f"[bold green]✓ Exported Design Spec (JSON): {output_path}[/bold green]")
    return output_path


def export_spec_markdown(spec: DeNovoDesignSpec, output_path: Path | str) -> Path:
    """Save Design Spec as a human-readable engineering blueprint."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    scaffolds_md = ""
    if spec.homologous_scaffolds:
        for s in spec.homologous_scaffolds:
            scaffolds_md += f"- **{s['name']}** (UniProt: `{s['uniprot_accession']}`, pLDDT: `{s['plddt_score']}`, Tier: `{s['confidence_tier']}`)\n"
    else:
        scaffolds_md = "_No high-confidence AlphaFold scaffolds found in current local graph._\n"

    md = f"""# Layer 3 De Novo Design Specification: {spec.spec_id}

**Target Domain:** {spec.target_name}  
**Addressed Epistemic Gap:** `{spec.causal_gap_id}` ({spec.gap_priority} Priority)  
**Objective:** {spec.gap_description}

---

## 1. Substrate & Active Pocket 3D Geometry

| Property | Value |
|:---|:---|
| **Substrate Name** | {spec.substrate_name} |
| **1D SMILES** | `{spec.substrate_smiles}` |
| **Formula** | `{spec.substrate_formula or 'N/A'}` |
| **Molecular Weight** | `{spec.substrate_molecular_weight or 'N/A'} Da` |
| **3D Conformer File (.sdf)** | [`{spec.substrate_3d_sdf_path}`](file://{spec.substrate_3d_sdf_path}) |
| **Target Pocket Volume** | `{spec.target_pocket_volume_angstrom3}` |
| **Target pLDDT Confidence** | `≥ {spec.target_plddt_minimum}` |

---

## 2. Homologous AlphaFold Scaffolds (Seed Templates)

{scaffolds_md}

---

## 3. Generative Model Handoff Configurations

### RFdiffusion All-Atom (Pocket Conditioning)
```json
{json.dumps(spec.rfdiffusion_all_atom_flags, indent=2)}
```

### ESM-3 Active Site Prompt
```json
{json.dumps(spec.esm3_prompt_config, indent=2)}
```

### ProteinMPNN Sequence Optimization
```json
{json.dumps(spec.proteinmpnn_config, indent=2)}
```
"""
    output_path.write_text(md, encoding="utf-8")
    console.print(f"[bold green]✓ Exported Design Blueprint (Markdown): {output_path}[/bold green]")
    return output_path


def compile_all_specs_for_target(
    target: str,
    output_dir: Optional[Path | str] = None,
) -> list[DeNovoDesignSpec]:
    """Detect CRITICAL/HIGH gaps for a target and compile Design Specs for each."""
    from uid_engine.graph.store import load_graph
    from uid_engine.chains.registry import CausalChainRegistry
    from uid_engine.analysis.gap_detector import NegativeSpaceDetector

    console.print(f"\n[bold cyan]═══ Compiling Layer 3 Design Specs: {target} ═══[/bold cyan]\n")

    graph = load_graph()
    registry = CausalChainRegistry()
    chain = registry.load(target)

    detector = NegativeSpaceDetector(graph)
    gaps = detector.detect_gaps(chain)

    # Filter to CRITICAL and HIGH priority gaps that require de novo solutions
    priority_gaps = [g for g in gaps if g.priority in (GapPriority.CRITICAL, GapPriority.HIGH)]

    specs = []
    out_dir = Path(output_dir) if output_dir else config.PROJECT_ROOT / "data" / "specs" / target
    out_dir.mkdir(parents=True, exist_ok=True)

    for gap in priority_gaps:
        spec = compile_design_spec_for_gap(gap, graph, target=target, output_dir=out_dir)
        json_path = out_dir / f"{spec.spec_id}.json"
        md_path = out_dir / f"{spec.spec_id}.md"
        export_spec_json(spec, json_path)
        export_spec_markdown(spec, md_path)
        specs.append(spec)

    console.print(f"\n[bold green]✓ Successfully compiled {len(specs)} Layer 3 Design Specs for {target}![/bold green]")
    return specs

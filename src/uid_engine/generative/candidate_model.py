"""Candidate Protein Data Models & Serialization Schema.

Represents computationally generated de novo candidate proteins, their 3D structural
coordinates, and biophysical quality control metrics.
"""

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Any


@dataclass
class BiophysicalProperties:
    """Biophysical metrics evaluated during in silico screening."""
    molecular_weight: float
    isoelectric_point: float  # pI
    net_charge_ph74: float
    gravy_score: float        # Grand Average of Hydropathy (GRAVY: < 0 is hydrophilic/soluble)
    aromaticity: float
    instability_index: float  # < 40 indicates in vitro stability


@dataclass
class ScreeningResult:
    """Multi-gate quality control evaluation result."""
    passed: bool
    gate_1_plddt: bool
    gate_2_sc_rmsd: bool
    gate_3_catalytic_retention: bool
    gate_4_biophysical_solubility: bool
    mean_plddt: float
    sc_rmsd: float
    gravy_score: float
    failure_reasons: list[str] = field(default_factory=list)


@dataclass
class CandidateProtein:
    """A generated de novo protein candidate designed to resolve an epistemic gap."""
    candidate_id: str
    target_spec_id: str
    target_domain: str
    causal_gap_id: str
    sequence: str
    length: int
    predicted_plddt: float
    predicted_ptm: float
    sc_rmsd: float
    catalytic_residues: dict[str, str]  # e.g., {"H54": "HIS", "D112": "ASP", "S198": "SER"}
    biophysical_properties: BiophysicalProperties
    screening_result: ScreeningResult
    pdb_path: Optional[str] = None
    fasta_path: Optional[str] = None
    generation_model: str = "ESM-3 + ProteinMPNN"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_fasta(self) -> str:
        """Export candidate as standard FASTA format string."""
        header = (
            f">{self.candidate_id} | spec:{self.target_spec_id} | "
            f"pLDDT:{self.predicted_plddt:.1f} | scRMSD:{self.sc_rmsd:.2f}Å | "
            f"GRAVY:{self.biophysical_properties.gravy_score:.2f}"
        )
        # Wrap sequence to 80 chars per line
        seq_lines = [self.sequence[i:i+80] for i in range(0, len(self.sequence), 80)]
        return f"{header}\n" + "\n".join(seq_lines) + "\n"

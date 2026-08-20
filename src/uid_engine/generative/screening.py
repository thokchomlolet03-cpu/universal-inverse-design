"""In Silico Screening & Multi-Gate Quality Control Filter.

Evaluates generated candidate proteins through 4 rigorous biophysical and structural gates
before allowing them to be injected into the Epistemic Knowledge Graph:
- Gate 1: Structural Confidence (mean pLDDT >= 80.0)
- Gate 2: Self-Consistency Foldability (scRMSD <= 2.0 Å)
- Gate 3: Active Site Catalytic Integrity (exact residue identity & alignment)
- Gate 4: Biophysical Screen (GRAVY hydropathy <= 0.2 to prevent blood/serum precipitation)
"""

from typing import Optional
from Bio.SeqUtils.ProtParam import ProteinAnalysis
from rich.console import Console

from uid_engine.generative.candidate_model import BiophysicalProperties, ScreeningResult

console = Console()


def compute_biophysical_properties(sequence: str) -> BiophysicalProperties:
    """Compute molecular weight, isoelectric point, GRAVY score, and stability using BioPython."""
    # Clean sequence of any non-standard characters
    clean_seq = "".join([aa for aa in sequence.upper() if aa in "ACDEFGHIKLMNPQRSTVWY"])
    analysis = ProteinAnalysis(clean_seq)

    mw = round(analysis.molecular_weight(), 2)
    pI = round(analysis.isoelectric_point(), 2)
    gravy = round(analysis.gravy(), 3)
    aromaticity = round(analysis.aromaticity(), 3)
    instability = round(analysis.instability_index(), 2)

    # Net charge at physiological pH 7.4 (approximate from pI)
    net_charge = round(analysis.charge_at_pH(7.4), 2)

    return BiophysicalProperties(
        molecular_weight=mw,
        isoelectric_point=pI,
        net_charge_ph74=net_charge,
        gravy_score=gravy,
        aromaticity=aromaticity,
        instability_index=instability,
    )


def screen_candidate_sequence(
    sequence: str,
    predicted_plddt: float,
    sc_rmsd: float,
    expected_catalytic_residues: Optional[dict[str, str]] = None,
    min_plddt: float = 80.0,
    max_sc_rmsd: float = 2.0,
    max_gravy: float = 0.2,
    max_instability: float = 50.0,
) -> tuple[BiophysicalProperties, ScreeningResult]:
    """Execute the complete 4-gate in silico screening pipeline on a candidate protein.

    Args:
        sequence: Amino acid sequence.
        predicted_plddt: Mean pLDDT score from folding prediction (0-100).
        sc_rmsd: Self-consistency RMSD against target backbone (in Å).
        expected_catalytic_residues: Dict of required active site positions (e.g. {"H54": "H"}).
        min_plddt: Minimum acceptable pLDDT (default: 80.0).
        max_sc_rmsd: Maximum acceptable scRMSD (default: 2.0 Å).
        max_gravy: Maximum acceptable GRAVY score (default: 0.2, negative is hydrophilic).
        max_instability: Maximum instability index (default: 50.0).

    Returns:
        Tuple of (BiophysicalProperties, ScreeningResult).
    """
    props = compute_biophysical_properties(sequence)
    failure_reasons = []

    # Gate 1: pLDDT structural confidence
    gate_1 = predicted_plddt >= min_plddt
    if not gate_1:
        failure_reasons.append(
            f"Gate 1 Failed: pLDDT {predicted_plddt:.1f} < threshold {min_plddt:.1f}"
        )

    # Gate 2: Self-consistency RMSD
    gate_2 = sc_rmsd <= max_sc_rmsd
    if not gate_2:
        failure_reasons.append(
            f"Gate 2 Failed: scRMSD {sc_rmsd:.2f}Å > threshold {max_sc_rmsd:.2f}Å"
        )

    # Gate 3: Catalytic residue retention
    gate_3 = True
    if expected_catalytic_residues:
        for pos_str, expected_aa in expected_catalytic_residues.items():
            # Extract 0-indexed position (e.g. 'H54' -> index 53)
            digits = "".join(filter(str.isdigit, pos_str))
            if digits:
                idx = int(digits) - 1
                if idx < 0 or idx >= len(sequence):
                    gate_3 = False
                    failure_reasons.append(f"Gate 3 Failed: Position {pos_str} out of bounds")
                    break
                actual_aa = sequence[idx]
                expected_single = expected_aa[0].upper()
                if actual_aa != expected_single:
                    gate_3 = False
                    failure_reasons.append(
                        f"Gate 3 Failed: Active site mutation at {pos_str} (expected {expected_single}, got {actual_aa})"
                    )
                    break

    # Gate 4: Biophysical solubility & anti-aggregation screen
    # GRAVY <= 0.2 ensures the protein is predominantly hydrophilic and will not precipitate into amyloid fibrils
    gate_4 = (props.gravy_score <= max_gravy) and (props.instability_index <= max_instability)
    if not gate_4:
        if props.gravy_score > max_gravy:
            failure_reasons.append(
                f"Gate 4 Failed: Hydrophobicity GRAVY {props.gravy_score:.2f} > {max_gravy:.2f} (High aggregation risk)"
            )
        if props.instability_index > max_instability:
            failure_reasons.append(
                f"Gate 4 Failed: Instability index {props.instability_index:.1f} > {max_instability:.1f}"
            )

    overall_passed = gate_1 and gate_2 and gate_3 and gate_4

    result = ScreeningResult(
        passed=overall_passed,
        gate_1_plddt=gate_1,
        gate_2_sc_rmsd=gate_2,
        gate_3_catalytic_retention=gate_3,
        gate_4_biophysical_solubility=gate_4,
        mean_plddt=predicted_plddt,
        sc_rmsd=sc_rmsd,
        gravy_score=props.gravy_score,
        failure_reasons=failure_reasons,
    )

    return props, result

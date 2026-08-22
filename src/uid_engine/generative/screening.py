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
from uid_engine.generative.docking_gate import evaluate_molecular_docking, DockingResult
from uid_engine.generative.off_target_screen import evaluate_off_target_selectivity, SelectivityResult

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
    substrate_smiles: Optional[str] = None,
    max_docking_energy: float = -8.0,
    min_selectivity_ratio: float = 100.0,
    receptor_pdb: Optional[str] = None,
) -> tuple[BiophysicalProperties, ScreeningResult]:
    """Execute the complete in silico screening pipeline on a candidate protein.

    Evaluates up to 6 rigorous quality control gates:
    - Gate 1: Structural Confidence (pLDDT >= 80.0)
    - Gate 2: Self-Consistency Foldability (scRMSD <= 2.0 Å)
    - Gate 3: Active Site Catalytic Integrity (exact residue sequence match)
    - Gate 4: Biophysical Solubility (GRAVY <= 0.2, Instability <= 50.0)
    - Gate 5 (Optional/Thermodynamic): AutoDock Vina Binding Affinity (ΔG <= -8.0 kcal/mol)
    - Gate 6 (Optional/Safety): Off-Target Selectivity vs Native Decoys (>= 100x selectivity)

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

    # Optional Gate 5: AutoDock Vina Docking
    gate_5 = None
    binding_energy = None
    if substrate_smiles:
        docking_res = evaluate_molecular_docking(
            receptor_pdb=receptor_pdb,
            substrate_smiles=substrate_smiles,
            max_binding_energy_threshold=max_docking_energy,
        )
        gate_5 = docking_res.passed_gate_5
        binding_energy = docking_res.binding_energy_kcal_mol
        if not gate_5:
            failure_reasons.append(
                f"Gate 5 Failed: AutoDock Vina ΔG {binding_energy:.2f} kcal/mol > {max_docking_energy:.1f} kcal/mol"
            )

    # Optional Gate 6: Off-Target Selectivity Screen
    gate_6 = None
    selectivity_val = None
    if substrate_smiles and gate_5 and binding_energy is not None:
        selectivity_res = evaluate_off_target_selectivity(
            candidate_sequence=sequence,
            target_delta_g=binding_energy,
            min_selectivity_ratio=min_selectivity_ratio,
        )
        gate_6 = selectivity_res.passed_gate_6
        selectivity_val = selectivity_res.selectivity_ratio
        if not gate_6:
            failure_reasons.append(
                f"Gate 6 Failed: Off-target selectivity {selectivity_val:.1f}x < threshold {min_selectivity_ratio:.0f}x"
            )

    # Overall pass: Gates 1-4 are mandatory; Gates 5-6 are evaluated if substrate provided
    overall_passed = gate_1 and gate_2 and gate_3 and gate_4
    if gate_5 is not None:
        overall_passed = overall_passed and gate_5
    if gate_6 is not None:
        overall_passed = overall_passed and gate_6

    result = ScreeningResult(
        passed=overall_passed,
        gate_1_plddt=gate_1,
        gate_2_sc_rmsd=gate_2,
        gate_3_catalytic_retention=gate_3,
        gate_4_biophysical_solubility=gate_4,
        gate_5_docking=gate_5,
        gate_6_selectivity=gate_6,
        binding_energy_kcal_mol=binding_energy,
        selectivity_ratio=selectivity_val,
        mean_plddt=predicted_plddt,
        sc_rmsd=sc_rmsd,
        gravy_score=props.gravy_score,
        failure_reasons=failure_reasons,
    )

    return props, result

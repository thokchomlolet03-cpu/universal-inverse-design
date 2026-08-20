# Layer 3 De Novo Design Specification: SPEC-GLUCOSEPANE-REQ-IN_VIVO_DELIVERY

**Target Domain:** Glucosepane  
**Addressed Epistemic Gap:** `req:in_vivo_delivery` (HIGH Priority)  
**Objective:** In vivo delivery mechanism to transport AGE-breaker to arterial ECM

---

## 1. Substrate & Active Pocket 3D Geometry

| Property | Value |
|:---|:---|
| **Substrate Name** | Glucosepane |
| **1D SMILES** | `NCCCC(N)C(=O)O.NC(CCC1=NC=C(NC1)CCCC(N)C(=O)O)C(=O)O` |
| **Formula** | `C18H34N6O6` |
| **Molecular Weight** | `430.25 Da` |
| **3D Conformer File (.sdf)** | [`/Users/lolet/Universal Inverse Design/data/specs/glucosepane/SPEC-GLUCOSEPANE-REQ-IN_VIVO_DELIVERY_substrate_3d.sdf`](file:///Users/lolet/Universal Inverse Design/data/specs/glucosepane/SPEC-GLUCOSEPANE-REQ-IN_VIVO_DELIVERY_substrate_3d.sdf) |
| **Target Pocket Volume** | `450 - 750 Å³` |
| **Target pLDDT Confidence** | `≥ 85.0` |

---

## 2. Homologous AlphaFold Scaffolds (Seed Templates)

_No high-confidence AlphaFold scaffolds found in current local graph._


---

## 3. Generative Model Handoff Configurations

### RFdiffusion All-Atom (Pocket Conditioning)
```json
{
  "model": "RFdiffusion_AllAtom_v1",
  "input_ligand_sdf": "/Users/lolet/Universal Inverse Design/data/specs/glucosepane/SPEC-GLUCOSEPANE-REQ-IN_VIVO_DELIVERY_substrate_3d.sdf",
  "target_pocket_conditioning": true,
  "num_designs": 100,
  "diffusion_steps": 50,
  "catalytic_site_clash_penalty": 2.5
}
```

### ESM-3 Active Site Prompt
```json
{
  "model": "esmc-600m",
  "task": "active_site_scaffolding",
  "target_plddt_min": 85.0,
  "sampling_temperature": 0.2,
  "num_iterations": 3
}
```

### ProteinMPNN Sequence Optimization
```json
{
  "model": "protein_mpnn_v48_020",
  "sampling_temp": 0.1,
  "backbone_noise": 0.02,
  "num_sequences_per_target": 8
}
```

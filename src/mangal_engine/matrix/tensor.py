"""Project Mangal — Combinatorial Interrogation Tensor Engine.

Constructs, slices, indexes, and synthesizes diagnostic inquiries across
3D (1,000), 4D (10,000), and 5D (100,000) combinatorial vector spaces.
"""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass
from enum import Enum
from typing import Iterator, Optional, Sequence

from mangal_engine.matrix.dimensions import (
    ArchetypeLens,
    CoreElement,
    CognitiveOperation,
    ScaleShift,
    ThermodynamicVector,
    InformationState,
    PhilosophicalOperator,
    VectorCoordinate,
    is_heuristic_compatible,
)


class MatrixScale(str, Enum):
    """Supported tensor dimensionalities."""
    SCALE_1K = "1,000 (3D: Element x Operation x Scale)"
    SCALE_10K = "10,000 (4D: Archetype x Element x Operation x Scale)"
    SCALE_100K = "100,000 (5D: Scale x Info x Consciousness x Thermo x Philosophy)"


@dataclass(frozen=True)
class SynthesizedInquiry:
    """A fully contextualized diagnostic question generated from a tensor vector."""
    coordinate: VectorCoordinate
    seed_problem: str
    inquiry_text: str
    lens_summary: str
    is_compatible: bool


class InterrogationTensor:
    """Combinatorial tensor matrix for Project Mangal."""

    def __init__(self, scale: MatrixScale = MatrixScale.SCALE_10K) -> None:
        self.scale = scale

    @property
    def total_theoretical_combinations(self) -> int:
        """Total combinatorial state-space size."""
        if self.scale == MatrixScale.SCALE_1K:
            return len(CoreElement) * len(CognitiveOperation) * len(ScaleShift)  # 1,000
        elif self.scale == MatrixScale.SCALE_10K:
            return (
                len(ArchetypeLens)
                * len(CoreElement)
                * len(CognitiveOperation)
                * len(ScaleShift)
            )  # 10,000
        elif self.scale == MatrixScale.SCALE_100K:
            return (
                len(ScaleShift)
                * len(InformationState)
                * len(ArchetypeLens)
                * len(ThermodynamicVector)
                * len(PhilosophicalOperator)
            )  # 100,000
        return 10_000

    def iterate_coordinates(self, filter_compatible_only: bool = False) -> Iterator[VectorCoordinate]:
        """Generate vector coordinates sequentially across the tensor dimensions."""
        if self.scale == MatrixScale.SCALE_1K:
            for elem, op, scale in itertools.product(CoreElement, CognitiveOperation, ScaleShift):
                coord = VectorCoordinate(element=elem, operation=op, scale=scale)
                if not filter_compatible_only or is_heuristic_compatible(coord):
                    yield coord

        elif self.scale == MatrixScale.SCALE_10K:
            for arch, elem, op, scale in itertools.product(
                ArchetypeLens, CoreElement, CognitiveOperation, ScaleShift
            ):
                coord = VectorCoordinate(archetype=arch, element=elem, operation=op, scale=scale)
                if not filter_compatible_only or is_heuristic_compatible(coord):
                    yield coord

        elif self.scale == MatrixScale.SCALE_100K:
            for scale, info, arch, thermo, phil in itertools.product(
                ScaleShift, InformationState, ArchetypeLens, ThermodynamicVector, PhilosophicalOperator
            ):
                coord = VectorCoordinate(
                    archetype=arch,
                    scale=scale,
                    information=info,
                    thermodynamic=thermo,
                    philosophical=phil,
                )
                if not filter_compatible_only or is_heuristic_compatible(coord):
                    yield coord

    def get_coordinate_by_index(self, index: int) -> VectorCoordinate:
        """Deterministic O(1) index lookup across the tensor dimensions."""
        total = self.total_theoretical_combinations
        if index < 0 or index >= total:
            raise IndexError(f"Index {index} out of bounds for tensor of size {total}")

        if self.scale == MatrixScale.SCALE_1K:
            z_idx = index % len(ScaleShift)
            y_idx = (index // len(ScaleShift)) % len(CognitiveOperation)
            x_idx = index // (len(ScaleShift) * len(CognitiveOperation))
            return VectorCoordinate(
                element=list(CoreElement)[x_idx],
                operation=list(CognitiveOperation)[y_idx],
                scale=list(ScaleShift)[z_idx],
            )

        elif self.scale == MatrixScale.SCALE_10K:
            z_idx = index % len(ScaleShift)
            y_idx = (index // len(ScaleShift)) % len(CognitiveOperation)
            x_idx = (index // (len(ScaleShift) * len(CognitiveOperation))) % len(CoreElement)
            w_idx = index // (len(ScaleShift) * len(CognitiveOperation) * len(CoreElement))
            return VectorCoordinate(
                archetype=list(ArchetypeLens)[w_idx],
                element=list(CoreElement)[x_idx],
                operation=list(CognitiveOperation)[y_idx],
                scale=list(ScaleShift)[z_idx],
            )

        else:
            # 5D: Scale x Info x Arch x Thermo x Phil
            p_idx = index % len(PhilosophicalOperator)
            t_idx = (index // 10) % len(ThermodynamicVector)
            w_idx = (index // 100) % len(ArchetypeLens)
            i_idx = (index // 1000) % len(InformationState)
            z_idx = (index // 10000) % len(ScaleShift)
            return VectorCoordinate(
                archetype=list(ArchetypeLens)[w_idx],
                scale=list(ScaleShift)[z_idx],
                information=list(InformationState)[i_idx],
                thermodynamic=list(ThermodynamicVector)[t_idx],
                philosophical=list(PhilosophicalOperator)[p_idx],
            )

    def sample_diverse_coordinates(
        self,
        count: int = 20,
        filter_compatible_only: bool = True,
        seed: Optional[int] = None,
    ) -> list[VectorCoordinate]:
        """Stratified / uniform random sampling of coordinates across the matrix."""
        rng = random.Random(seed)
        total = self.total_theoretical_combinations
        sampled: list[VectorCoordinate] = []
        seen_indices: set[int] = set()

        max_attempts = count * 20
        attempts = 0

        while len(sampled) < count and attempts < max_attempts:
            attempts += 1
            idx = rng.randint(0, total - 1)
            if idx in seen_indices:
                continue
            seen_indices.add(idx)
            coord = self.get_coordinate_by_index(idx)
            if filter_compatible_only and not is_heuristic_compatible(coord):
                continue
            sampled.append(coord)

        return sampled

    def synthesize_inquiry(self, coordinate: VectorCoordinate, seed_problem: str) -> SynthesizedInquiry:
        """Synthesize a sharp, bias-shattering diagnostic question from coordinate & problem."""
        is_comp = is_heuristic_compatible(coordinate)

        arch_label = coordinate.archetype.value if coordinate.archetype else "First Principles Observer"
        elem_label = coordinate.element.value
        op_label = coordinate.operation.value
        scale_label = coordinate.scale.value

        # Build lens summary
        lens_summary = f"[{coordinate.coordinate_id}] {arch_label} | {elem_label} | {op_label} | {scale_label}"

        # Context-dependent question synthesis template
        arch_name = coordinate.archetype.name if coordinate.archetype else "ANALYST"
        elem_name = coordinate.element.name
        op_name = coordinate.operation.name
        scale_name = coordinate.scale.name

        # Synthesize targeted question
        if self.scale == MatrixScale.SCALE_100K and coordinate.philosophical:
            phil_val = coordinate.philosophical.value
            thermo_val = coordinate.thermodynamic.value if coordinate.thermodynamic else "Entropy"
            info_val = coordinate.information.value if coordinate.information else "Signals"
            inquiry_text = (
                f"From the perspective of {arch_label} operating under {scale_label} and {thermo_val}, "
                f"how does the fundamental informational reality of '{seed_problem}' ({info_val}) "
                f"resolve the philosophical challenge of {phil_val} without collapsing into contradiction?"
            )
        else:
            inquiry_text = (
                f"Acting strictly as {arch_label}: If we {op_label.lower()} the {elem_label.lower()} "
                f"of '{seed_problem}' while operating under {scale_label.lower()}, "
                f"what irreducible physical or causal breakdown immediately occurs, and what emergent behavior replaces it?"
            )

        return SynthesizedInquiry(
            coordinate=coordinate,
            seed_problem=seed_problem,
            inquiry_text=inquiry_text,
            lens_summary=lens_summary,
            is_compatible=is_comp,
        )

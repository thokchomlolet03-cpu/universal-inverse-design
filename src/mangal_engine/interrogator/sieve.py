"""Project Mangal — Multi-Gate Interrogation Sieve.

Implements the 3-gate automated filter:
- Gate 1: Fast O(1) heuristic compatibility & redundancy purge (pure Python, 0 compute/API cost)
- Gate 2: Anomaly & deviation scoring (quantifies divergence from default human cognitive bias)
- Gate 3: Core high-impact insight extraction (reduces 1,000–100,000 vectors down to actionable core)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from mangal_engine.matrix.dimensions import (
    ArchetypeLens,
    CognitiveOperation,
    ScaleShift,
    VectorCoordinate,
    is_heuristic_compatible,
)
from mangal_engine.matrix.tensor import SynthesizedInquiry


@dataclass(frozen=True)
class ScoredInquiry:
    """An inquiry scored through the multi-gate sieve."""
    inquiry: SynthesizedInquiry
    gate1_passed: bool
    anomaly_score: float      # 0.0 to 1.0 (higher = more disruptive to status quo)
    leverage_score: float     # 0.0 to 1.0 (higher = deeper first-principle penetration)
    total_impact_score: float # Weighted composite score


class InterrogationSieve:
    """The multi-gate elimination filter for Project Mangal."""

    def __init__(
        self,
        anomaly_weight: float = 0.55,
        leverage_weight: float = 0.45,
    ) -> None:
        self.anomaly_weight = anomaly_weight
        self.leverage_weight = leverage_weight

    def evaluate_gate1(self, coordinate: VectorCoordinate) -> bool:
        """Gate 1: Fast O(1) heuristic ruleset."""
        return is_heuristic_compatible(coordinate)

    def calculate_anomaly_score(self, coord: VectorCoordinate) -> float:
        """Gate 2: Quantifies conceptual distance from conventional human thinking.
        
        High anomaly: Extreme archetypes (Quantum, Adversary, Alien, Glitch) +
        radical operations (Invert, Subvert, Eliminate) + extreme scales (Atomic, Absolute Zero, Geologic).
        """
        score = 0.5  # Baseline

        # Archetype deviation
        if coord.archetype in (
            ArchetypeLens.QUANTUM_PHYSICIST,
            ArchetypeLens.ALIEN_ARCHEOLOGIST,
            ArchetypeLens.GLITCH,
            ArchetypeLens.THERMODYNAMICIST,
        ):
            score += 0.20
        elif coord.archetype in (ArchetypeLens.ADVERSARY, ArchetypeLens.PARASITE):
            score += 0.15

        # Operation disruption
        if coord.operation in (
            CognitiveOperation.INVERT,
            CognitiveOperation.SUBVERT,
            CognitiveOperation.ELIMINATE,
            CognitiveOperation.DISCRETIZE,
        ):
            score += 0.18
        elif coord.operation in (CognitiveOperation.RANDOMIZE, CognitiveOperation.OBSCURE):
            score += 0.12

        # Scale extremity
        if coord.scale in (
            ScaleShift.ATOMIC,
            ScaleShift.ABSOLUTE_ZERO,
            ScaleShift.GEOLOGIC_TIME,
            ScaleShift.LIGHT_SPEED,
            ScaleShift.INFINITE_ABUNDANCE,
        ):
            score += 0.15

        return min(1.0, max(0.0, score))

    def calculate_leverage_score(self, coord: VectorCoordinate) -> float:
        """Gate 2: Quantifies depth of first-principle penetration."""
        score = 0.5

        # Fundamental physics & mechanics give higher leverage
        if coord.thermodynamic or coord.information:
            score += 0.25

        if coord.operation in (
            CognitiveOperation.QUANTIFY,
            CognitiveOperation.AUTOMATE,
            CognitiveOperation.STANDARDIZE,
        ):
            score += 0.15

        return min(1.0, max(0.0, score))

    def score_inquiry(self, inquiry: SynthesizedInquiry) -> ScoredInquiry:
        """Run all gates on a single inquiry."""
        g1_pass = self.evaluate_gate1(inquiry.coordinate)

        if not g1_pass:
            return ScoredInquiry(
                inquiry=inquiry,
                gate1_passed=False,
                anomaly_score=0.0,
                leverage_score=0.0,
                total_impact_score=0.0,
            )

        anomaly = self.calculate_anomaly_score(inquiry.coordinate)
        leverage = self.calculate_leverage_score(inquiry.coordinate)
        total = (anomaly * self.anomaly_weight) + (leverage * self.leverage_weight)

        return ScoredInquiry(
            inquiry=inquiry,
            gate1_passed=True,
            anomaly_score=round(anomaly, 4),
            leverage_score=round(leverage, 4),
            total_impact_score=round(total, 4),
        )

    def sieve_inquiries(
        self,
        inquiries: Sequence[SynthesizedInquiry],
        top_k: int = 20,
    ) -> list[ScoredInquiry]:
        """Gate 3: Filter, rank, and extract top high-leverage inquiries."""
        scored = [self.score_inquiry(inq) for inq in inquiries]
        passing = [s for s in scored if s.gate1_passed]
        passing.sort(key=lambda s: s.total_impact_score, reverse=True)
        return passing[:top_k]

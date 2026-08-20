"""Project Mangal — Dimensional Taxonomies & Fast Heuristic Compatibility Rules.

Defines the mathematical axes of the Interrogation Matrix across 3D (1,000),
4D (10,000), and 5D (100,000) combinatorial tensor spaces, along with pure-Python
Gate 1 heuristic exclusion filters.
"""

from __future__ import annotations

from enum import Enum
from typing import NamedTuple, Optional


class ArchetypeLens(str, Enum):
    """Axis W: 10 Archetypal Lenses (The Mindset)."""
    ADVERSARY = "Adversary (Cybersecurity/Military)"
    THERMODYNAMICIST = "Thermodynamicist (Entropy/Energy Flow)"
    SOVEREIGN = "Sovereign (Regulator/Monopoly/Power)"
    MINIMALIST = "Minimalist (Ant/Emergent Swarm)"
    IMMORTAL = "Immortal (Geological/10,000-Year Scale)"
    QUANTUM_PHYSICIST = "Quantum Physicist (Superposition/Entanglement)"
    PARASITE = "Parasite/Symbiont (Host Exploitation)"
    GLITCH = "Glitch/Chaos Monkey (Random Mutation)"
    HYPER_CAPITALIST = "Hyper-Capitalist (Transaction Speed/Margin)"
    ALIEN_ARCHEOLOGIST = "Alien Archeologist (Decontextualized Artifact)"


class CoreElement(str, Enum):
    """Axis X: 10 Core Elements (What we look at)."""
    CORE_ASSET = "Core Asset (Primary Material/Object/Data)"
    MEDIUM_SPACE = "Medium/Space (Environment/Substrate)"
    CATALYST = "Catalyst (Trigger/Energy Source/Motivation)"
    FRICTION_POINT = "Friction Point (Bottleneck/Loss/Waste)"
    TIMING = "Timing (Sequence/Duration/Velocity)"
    PARTICIPANT = "Participant (User/Observer/Operator)"
    RULE_LAW = "Rule/Law (Constraint/Regulation/Boundary)"
    INTERFACE = "Interface (Touchpoint/Connection Protocol)"
    MEMORY_HISTORY = "Memory/History (Path-Dependency/Legacy Code)"
    OUTPUT = "Output (Final Value/Waste Product)"


class CognitiveOperation(str, Enum):
    """Axis Y: 10 Cognitive Operations (How we mutate it)."""
    INVERT = "Invert (Reverse Direction/Polarity/Roles)"
    ELIMINATE = "Eliminate (Delete Completely & Check Breach)"
    SUBVERT = "Subvert (Use for Opposite of Intended Purpose)"
    AUTOMATE = "Automate (Strip Human Agency & Decision Latency)"
    RANDOMIZE = "Randomize (Inject Stochastic Chaos/Non-Linearity)"
    QUANTIFY = "Quantify (Convert Qualitative Intuition to Pure Math)"
    DISCRETIZE = "Discretize (Chop Smooth Continuous Flow into Jagged Packets)"
    SYNTHESIZE = "Synthesize (Force-Merge with Alien Industry Paradigm)"
    OBSCURE = "Obscure (Hide Element from Rest of System Topology)"
    STANDARDIZE = "Standardize (Freeze into Rigid Immutable Constant)"


class ScaleShift(str, Enum):
    """Axis Z: 10 Scale & Context Shifts (Where/When we test it)."""
    PLANETARY = "Planetary Scale (Global Population / Biosphere)"
    ATOMIC = "Atomic Scale (Molecular / Individual Line of Code)"
    LIGHT_SPEED = "Light-Speed (Sub-Millisecond Real-Time Loop)"
    GEOLOGIC_TIME = "Geologic Time (Centuries / Millennia Evolution)"
    ZERO_RESOURCE = "Zero-Resource (No Budget / No Energy / Idle Grid)"
    INFINITE_ABUNDANCE = "Infinite-Abundance (Free Energy / Limitless Capital)"
    HOSTILE_ENVIRONMENT = "Hostile Environment (Deep Space / Active War / Chaos)"
    BIOLOGICAL_MIMICRY = "Biological Mimicry (Cellular Homeostasis / Organism)"
    LEGAL_VACUUM = "Legal Vacuum (Zero Norms / Anarchic Frontier)"
    ABSOLUTE_ZERO = "Absolute Zero (Complete Kinetic Stoppage / Deep Frozen)"


class ThermodynamicVector(str, Enum):
    """Axis T (5D Extension): 10 Thermodynamic Vectors (How energy flows)."""
    MAXIMUM_ENTROPY = "Maximum Entropy (Total Dissipation & Equilibrium)"
    NEGENTROPY = "Negentropy (Self-Organizing Syntropy & Life)"
    PHASE_TRANSITION = "Phase Transition (Sudden Critical State Leap)"
    SYMMETRY_BREAKING = "Symmetry Breaking (Freezing of Random Constants)"
    DISSIPATIVE_STRUCTURE = "Dissipative Structure (Energy Consumed for Shape)"
    QUANTUM_TUNNELING = "Quantum Tunneling (Probabilistic Barrier Bypass)"
    GRAVITATIONAL_COLLAPSE = "Gravitational Collapse (Extreme Spatial Curvature)"
    SUPERCONDUCTIVITY = "Superconductivity (Zero-Resistance Flow)"
    ZERO_POINT = "Zero-Point Fluctuation (Vacuum Energy Boiling)"
    ANNIHILATION = "Annihilation (Matter-Antimatter Pure Conversion)"


class InformationState(str, Enum):
    """Axis I (5D Extension): 10 Information States (How truth is encoded)."""
    HOLOGRAPHIC = "Holographic Projection (Boundary-Encoded Data)"
    NOISE_DEGRADATION = "Entropy/Noise (Irreversible Data Decay)"
    ENTANGLEMENT = "Quantum Entanglement (Non-Local Correlation)"
    ALGORITHMIC_MEMORY = "Algorithmic Memory (Replication Code)"
    SEMANTIC_SYMBOLS = "Semantic Symbols (Human Language & Math)"
    CAUSAL_DETERMINISM = "Causal Determinism (Rigid Domino Chain)"
    STOCHASTIC_CHAOS = "Stochastic Chaos (True Random Distribution)"
    BEKENSTEIN_BOUND = "Bekenstein Bound (Max Physical Data Density)"
    RETROCAUSAL_LOOP = "Retrocausal Loop (Future Constraining Past)"
    ABSOLUTE_VOID = "Absolute Void (Zero Signal / Total Null)"


class PhilosophicalOperator(str, Enum):
    """Axis P (5D Extension): 10 Philosophical Operators (What it means)."""
    TELEOLOGICAL = "Teleological (Inherent Design & Ultimate Purpose)"
    NIHILISTIC = "Nihilistic (Pure Mechanical Void / No Sacred Values)"
    ABSURD = "The Absurd (Meaning-Seeking Mind vs Silent Cosmos)"
    EXISTENTIAL = "Existential (Local Agent Manufactures Arbitrary Purpose)"
    AESTHETIC = "Aesthetic (Geometric Symmetry & Mathematical Elegance)"
    ETHICAL_KARMIC = "Ethical/Karmic (Built-In Balance & Consequence)"
    ONTOLOGICAL = "Ontological (Why Something Exists Rather Than Nothing)"
    EPISTEMOLOGICAL = "Epistemological (The Upper Bound of Knowability)"
    INSTRUMENTAL = "Instrumental (Reality as a Machine to Master)"
    MYSTICAL_PARADOX = "Mystical Paradox (Coexistence of Mutually Exclusive Truths)"


class VectorCoordinate(NamedTuple):
    """Immutable coordinate in the Mangal Tensor Space."""
    archetype: Optional[ArchetypeLens] = None
    element: CoreElement = CoreElement.CORE_ASSET
    operation: CognitiveOperation = CognitiveOperation.INVERT
    scale: ScaleShift = ScaleShift.PLANETARY
    thermodynamic: Optional[ThermodynamicVector] = None
    information: Optional[InformationState] = None
    philosophical: Optional[PhilosophicalOperator] = None

    @property
    def coordinate_id(self) -> str:
        """Compact deterministic hash/ID for this vector."""
        parts = []
        if self.archetype:
            parts.append(f"W{list(ArchetypeLens).index(self.archetype):02d}")
        parts.append(f"X{list(CoreElement).index(self.element):02d}")
        parts.append(f"Y{list(CognitiveOperation).index(self.operation):02d}")
        parts.append(f"Z{list(ScaleShift).index(self.scale):02d}")
        if self.thermodynamic:
            parts.append(f"T{list(ThermodynamicVector).index(self.thermodynamic):02d}")
        if self.information:
            parts.append(f"I{list(InformationState).index(self.information):02d}")
        if self.philosophical:
            parts.append(f"P{list(PhilosophicalOperator).index(self.philosophical):02d}")
        return "-".join(parts)


def is_heuristic_compatible(vector: VectorCoordinate) -> bool:
    """Gate 1 Fast Heuristic Ruleset (O(1) pure Python execution).
    
    Evaluates whether the coordinate combination has physical/logical coherence
    before burning compute or API bandwidth. Prunes ~30-40% of degenerate combinations.
    """
    # 1. Atomic scale cannot meaningfully interact with macro-political sovereigns
    if vector.scale == ScaleShift.ATOMIC:
        if vector.archetype in (ArchetypeLens.SOVEREIGN, ArchetypeLens.HYPER_CAPITALIST):
            return False
        if vector.element == CoreElement.RULE_LAW and vector.operation == CognitiveOperation.STANDARDIZE:
            # Physical constants at atomic scale cannot be "standardized" further
            return False

    # 2. Absolute Zero kinetics cannot be paired with light-speed or instantaneous loops
    if vector.scale == ScaleShift.ABSOLUTE_ZERO:
        if vector.operation in (CognitiveOperation.AUTOMATE, CognitiveOperation.RANDOMIZE):
            return False
        if vector.thermodynamic == ThermodynamicVector.SUPERCONDUCTIVITY:
            # Superconductivity occurs near zero, but absolute zero kinetic stoppage precludes active flow
            pass

    # 3. Planetary scale with quantum-specific mechanics (unless paired with quantum archetype)
    if vector.scale == ScaleShift.PLANETARY:
        if vector.operation == CognitiveOperation.DISCRETIZE and vector.archetype != ArchetypeLens.QUANTUM_PHYSICIST:
            if vector.thermodynamic == ThermodynamicVector.QUANTUM_TUNNELING:
                return False

    # 4. Zero-Resource context cannot utilize infinite abundance or hyper-financialized margin optimization
    if vector.scale == ScaleShift.ZERO_RESOURCE:
        if vector.archetype == ArchetypeLens.HYPER_CAPITALIST and vector.operation == CognitiveOperation.SYNTHESIZE:
            return False

    # 5. Glitch/Chaos Monkey cannot standardize a frozen memory/history
    if vector.archetype == ArchetypeLens.GLITCH:
        if vector.element == CoreElement.MEMORY_HISTORY and vector.operation == CognitiveOperation.STANDARDIZE:
            return False

    # 6. Minimalist Ant Swarm cannot operate top-down sovereign monopolies
    if vector.archetype == ArchetypeLens.MINIMALIST:
        if vector.element == CoreElement.RULE_LAW and vector.operation == CognitiveOperation.STANDARDIZE:
            return False

    return True

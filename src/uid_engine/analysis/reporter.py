"""Epistemic Gap Report Generator — Transforms detected gaps into actionable reports.

Generates structured Markdown reports that tell you EXACTLY what humanity
still needs to discover to achieve the target repair goal.
"""

from datetime import datetime
from pathlib import Path

from rich.console import Console

from uid_engine import config
from uid_engine.graph.builder import EpistemicGraph
from uid_engine.analysis.gap_detector import EpistemicGap, NegativeSpaceDetector
from uid_engine.analysis.causal_chains import CausalNode

console = Console()


class GapReporter:
    """Generates structured Markdown reports from detected epistemic gaps."""

    def __init__(self, graph: EpistemicGraph, gaps: list[EpistemicGap]):
        self.graph = graph
        self.gaps = gaps

    def generate_report(self, target_name: str = "Glucosepane Crosslink Repair") -> str:
        """Generate a full Markdown report of all epistemic gaps."""
        stats = self.graph.stats()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        sections = [
            self._header(target_name, now),
            self._executive_summary(stats),
            self._gap_details(),
            self._candidate_summary(),
            self._research_roadmap(),
            self._methodology_note(stats),
        ]

        return "\n\n".join(sections)

    def save_report(self, target_name: str = "Glucosepane Crosslink Repair") -> Path:
        """Generate and save the report to disk."""
        report = self.generate_report(target_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"epistemic_gap_report_{timestamp}.md"
        filepath = config.REPORTS_DIR / filename
        filepath.write_text(report, encoding="utf-8")
        console.print(f"[bold green]✓ Report saved to {filepath}[/bold green]")
        return filepath

    # ─── Report Sections ────────────────────────────────────────────────────

    def _header(self, target_name: str, timestamp: str) -> str:
        return f"""# Epistemic Gap Report: {target_name}

**Generated:** {timestamp}
**Engine:** Universal Inverse Design Engine v0.1.0
**Target:** SENS Damage Category — Extracellular Crosslinks (GlycoSENS)

---

> This report identifies what humanity **does not know** — the precise missing
> scientific unknowns preventing us from solving {target_name.lower()}.
> Each gap represents a concrete research target that, if solved, advances
> humanity toward biological immortality."""

    def _executive_summary(self, stats: dict) -> str:
        critical = sum(1 for g in self.gaps if g.priority.value == "CRITICAL")
        high = sum(1 for g in self.gaps if g.priority.value == "HIGH")
        medium = sum(1 for g in self.gaps if g.priority.value == "MEDIUM")
        low = sum(1 for g in self.gaps if g.priority.value == "LOW")

        return f"""## Executive Summary

| Metric | Value |
|--------|-------|
| Total epistemic gaps identified | **{len(self.gaps)}** |
| 🔴 CRITICAL gaps (block all progress) | **{critical}** |
| 🟠 HIGH gaps (block major pathways) | **{high}** |
| 🟡 MEDIUM gaps (single pathway blocks) | **{medium}** |
| 🟢 LOW gaps (nice to have) | **{low}** |
| Knowledge graph nodes | {stats['total_nodes']} |
| Knowledge graph edges | {stats['total_edges']} |
| Explicit UNKNOWN nodes | {stats['unknowns']} |"""

    def _gap_details(self) -> str:
        lines = ["## Identified Epistemic Gaps\n"]

        for i, gap in enumerate(self.gaps, 1):
            priority_emoji = {
                "CRITICAL": "🔴",
                "HIGH": "🟠",
                "MEDIUM": "🟡",
                "LOW": "🟢",
            }.get(gap.priority.value, "⚪")

            lines.append(f"### Gap #{i} ({priority_emoji} {gap.priority.value}): {gap.gap_type}")
            lines.append(f"\n**{gap.description}**\n")

            # Evidence
            if gap.source_evidence:
                lines.append("**Evidence / Reason:**")
                for ev in gap.source_evidence:
                    lines.append(f"- {ev}")
                lines.append("")

            # Closest candidates
            if gap.closest_candidates:
                lines.append("**Closest Known Candidates:**")
                for c in gap.closest_candidates:
                    name = c.get("name", c.get("entity_id", "unknown"))
                    conf = c.get("confidence", "N/A")
                    source = c.get("source", "")
                    status = c.get("status", "")
                    context = c.get("context", "")
                    lines.append(f"- **{name}**")
                    if status:
                        lines.append(f"  - Status: {status}")
                    if context:
                        lines.append(f'  - Evidence: *"{context}"*')
                    lines.append(f"  - Confidence: {conf}")
                    if source:
                        lines.append(f"  - Source: {source}")
                lines.append("")

            # Downstream impact
            if gap.downstream_impact:
                lines.append("**Downstream Impact (blocked if unsolved):**")
                for impact in gap.downstream_impact:
                    lines.append(f"- {impact}")
                lines.append("")

            # Suggested directions
            if gap.suggested_directions:
                lines.append("**Suggested Research Directions:**")
                for d in gap.suggested_directions:
                    lines.append(f"1. {d}")
                lines.append("")

            lines.append("---\n")

        return "\n".join(lines)

    def _candidate_summary(self) -> str:
        """Summarize all candidates across all gaps."""
        all_candidates = []
        for gap in self.gaps:
            for c in gap.closest_candidates:
                all_candidates.append({
                    "gap": gap.description[:60] + "...",
                    **c,
                })

        if not all_candidates:
            return "## Candidate Summary\n\nNo candidates identified in the current knowledge graph."

        lines = ["## Candidate Summary\n"]
        lines.append("| Candidate | Gap | Confidence | Status |")
        lines.append("|-----------|-----|------------|--------|")
        for c in all_candidates:
            name = c.get("name", c.get("entity_id", "?"))
            gap_desc = c.get("gap", "")
            conf = c.get("confidence", "N/A")
            status = c.get("status", "N/A")
            lines.append(f"| {name} | {gap_desc} | {conf} | {status} |")

        return "\n".join(lines)

    def _research_roadmap(self) -> str:
        """Generate a prioritized research roadmap from the gaps."""
        lines = ["## Prioritized Research Roadmap\n"]
        lines.append("Based on gap severity and downstream impact:\n")

        for i, gap in enumerate(self.gaps, 1):
            priority_emoji = {
                "CRITICAL": "🔴",
                "HIGH": "🟠",
                "MEDIUM": "🟡",
                "LOW": "🟢",
            }.get(gap.priority.value, "⚪")

            lines.append(f"**{i}. {priority_emoji} {gap.description[:80]}**")
            if gap.suggested_directions:
                lines.append(f"   - Next step: {gap.suggested_directions[0]}")
            lines.append("")

        return "\n".join(lines)

    def _methodology_note(self, stats: dict) -> str:
        return f"""## Methodology

This report was generated by the Universal Inverse Design Engine using
**Causal Chain Inversion** — starting from the desired end state and working
backward to identify every prerequisite condition. Each condition was checked
against a knowledge graph containing {stats['total_nodes']} nodes and
{stats['total_edges']} edges sourced from curated biological databases.

Gaps were identified by detecting **topological holes** in the causal chain —
requirements for which no validated mechanism, enzyme, or compound exists
in the current scientific literature.

### Limitations

- This report is based on the current knowledge graph, which may not contain
  all published research. Gaps may be resolved by papers not yet ingested.
- Confidence scores are heuristic and should be validated against primary sources.
- Suggested research directions are generated algorithmically and should be
  reviewed by domain experts.

---

*Universal Inverse Design Engine v0.1.0 — Finding what humanity doesn't know.*"""

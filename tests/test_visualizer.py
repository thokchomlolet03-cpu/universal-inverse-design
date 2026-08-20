"""Tests for the interactive Epistemic Graph HTML visualizer."""

import json
from pathlib import Path
from uid_engine.analysis.visualizer import export_interactive_html
from uid_engine.graph.builder import build_mock_glucosepane_graph


class TestEpistemicVisualizer:
    """Test standalone interactive HTML graph generation."""

    def test_export_interactive_html_creates_file(self, tmp_path):
        graph = build_mock_glucosepane_graph()
        out_file = tmp_path / "test_map.html"
        res = export_interactive_html(graph, output_path=out_file, target_name="Test Target")

        assert res.exists()
        assert res.stat().st_size > 5000  # Non-trivial HTML file

    def test_html_contains_cytoscape_elements(self, tmp_path):
        graph = build_mock_glucosepane_graph()
        out_file = tmp_path / "test_map.html"
        export_interactive_html(graph, output_path=out_file, target_name="Glucosepane Repair")

        content = out_file.read_text(encoding="utf-8")
        assert "cytoscape" in content
        assert "Glucosepane Repair" in content
        assert "NEGATIVE SPACE GAP" in content
        assert "req:selective_enzyme" in content or "unknown:" in content

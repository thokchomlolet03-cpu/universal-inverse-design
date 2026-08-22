"""Interactive Epistemic Graph Visualizer — Generates standalone zero-dependency HTML maps.

Renders the complete knowledge graph in an interactive browser view using Cytoscape.js:
- Clearly differentiates PROVEN biological facts from NEGATIVE SPACE (UNKNOWN nodes).
- Visualizes edge confidence and evidence status (PROVEN vs HYPOTHESIZED vs FAILED).
- Interactive sidebar displaying node attributes, source citations, and AlphaFold 3D structure links.
- Filter and search controls for exploring causal chains.
"""

import json
from pathlib import Path
from typing import Optional

import networkx as nx
from rich.console import Console

from uid_engine import config
from uid_engine.graph.builder import EpistemicGraph
from uid_engine.graph.schema import NodeType, EvidenceStatus

console = Console()

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Epistemic Knowledge Graph — __TARGET_NAME__</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js"></script>
  <style>
    :root {
      --bg: #0b0f19;
      --panel-bg: rgba(15, 23, 42, 0.85);
      --border: #1e293b;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --accent: #38bdf8;
      --unknown: #f43f5e;
      --proven: #10b981;
      --hypo: #f59e0b;
      --failed: #ef4444;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      overflow: hidden;
      display: flex;
      height: 100vh;
      width: 100vw;
    }
    #cy {
      flex: 1;
      height: 100%;
      background: radial-gradient(circle at center, #131d33 0%, #070a12 100%);
    }
    #sidebar {
      width: 380px;
      height: 100%;
      background: var(--panel-bg);
      backdrop-filter: blur(12px);
      border-left: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      padding: 20px;
      gap: 16px;
      z-index: 10;
      box-shadow: -4px 0 24px rgba(0,0,0,0.5);
    }
    .header h1 { font-size: 1.15rem; font-weight: 700; color: var(--accent); }
    .header p { font-size: 0.8rem; color: var(--text-muted); margin-top: 4px; }
    .search-box input {
      width: 100%;
      padding: 10px 12px;
      border-radius: 8px;
      border: 1px solid var(--border);
      background: #0f172a;
      color: var(--text);
      font-size: 0.85rem;
      outline: none;
    }
    .search-box input:focus { border-color: var(--accent); }
    .stats-card {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      background: #0f172a;
      padding: 12px;
      border-radius: 8px;
      border: 1px solid var(--border);
      text-align: center;
    }
    .stat-val { font-size: 1.1rem; font-weight: 700; color: var(--accent); }
    .stat-lbl { font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; }
    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      font-size: 0.75rem;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 4px 8px;
      border-radius: 6px;
      background: #1e293b;
    }
    .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
    #details {
      flex: 1;
      overflow-y: auto;
      background: #0f172a;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 14px;
      font-size: 0.85rem;
    }
    #details h3 { color: var(--accent); margin-bottom: 8px; font-size: 0.95rem; }
    .detail-field { margin-bottom: 10px; }
    .detail-field .lbl { font-size: 0.7rem; text-transform: uppercase; color: var(--text-muted); display: block; }
    .detail-field .val { font-size: 0.85rem; color: var(--text); word-break: break-word; }
    .unknown-badge {
      background: rgba(244, 63, 94, 0.15);
      border: 1px solid var(--unknown);
      color: #fda4af;
      padding: 8px;
      border-radius: 6px;
      font-weight: 600;
      margin-bottom: 12px;
      display: block;
      text-align: center;
    }
    .plddt-pill {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 700;
    }
  </style>
</head>
<body>
  <div id="cy"></div>
  <div id="sidebar">
    <div class="header">
      <h1>Universal Inverse Design Engine</h1>
      <p>Epistemic Knowledge Graph: <strong>__TARGET_NAME__</strong></p>
    </div>
    <div class="stats-card">
      <div>
        <div class="stat-val" id="cnt-nodes">0</div>
        <div class="stat-lbl">Nodes</div>
      </div>
      <div>
        <div class="stat-val" id="cnt-edges">0</div>
        <div class="stat-lbl">Edges</div>
      </div>
      <div>
        <div class="stat-val" id="cnt-gaps" style="color: var(--unknown);">0</div>
        <div class="stat-lbl">Unknowns</div>
      </div>
    </div>
    <div class="search-box">
      <input type="text" id="search" placeholder="Search entity, protein, or gap..." />
    </div>
    <div class="legend">
      <span class="badge"><span class="dot" style="background: #38bdf8;"></span> Molecule</span>
      <span class="badge"><span class="dot" style="background: #a855f7;"></span> Protein</span>
      <span class="badge"><span class="dot" style="background: #10b981;"></span> Pathway</span>
      <span class="badge"><span class="dot" style="background: #f43f5e;"></span> Negative Space</span>
    </div>
    <div id="details">
      <p style="color: var(--text-muted); text-align: center; margin-top: 40px;">
        Click any node or edge to inspect its epistemic evidence, confidence metrics, and structural properties.
      </p>
    </div>
  </div>

  <script>
    const graphData = __GRAPH_JSON__;

    document.getElementById('cnt-nodes').innerText = graphData.elements.nodes ? graphData.elements.nodes.length : 0;
    document.getElementById('cnt-edges').innerText = graphData.elements.edges ? graphData.elements.edges.length : 0;

    let unknownCount = 0;
    if (graphData.elements.nodes) {
      unknownCount = graphData.elements.nodes.filter(n => n.data.node_type === 'UNKNOWN').length;
    }
    document.getElementById('cnt-gaps').innerText = unknownCount;

    const cy = cytoscape({
      container: document.getElementById('cy'),
      elements: graphData.elements,
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(name)',
            'font-size': '11px',
            'color': '#cbd5e1',
            'text-valign': 'bottom',
            'text-margin-y': 4,
            'background-color': '#38bdf8',
            'width': 26,
            'height': 26,
            'border-width': 2,
            'border-color': '#0f172a'
          }
        },
        {
          selector: 'node[node_type = "UNKNOWN"]',
          style: {
            'background-color': '#f43f5e',
            'width': 34,
            'height': 34,
            'border-width': 3,
            'border-style': 'dashed',
            'border-color': '#fda4af',
            'shadow-blur': 15,
            'shadow-color': '#f43f5e',
            'shadow-opacity': 0.8
          }
        },
        {
          selector: 'node[node_type = "PROTEIN"]',
          style: { 'background-color': '#a855f7', 'width': 28, 'height': 28 }
        },
        {
          selector: 'node[node_type = "PATHWAY"]',
          style: { 'background-color': '#10b981', 'width': 30, 'height': 30 }
        },
        {
          selector: 'node[node_type = "TISSUE"]',
          style: { 'background-color': '#f97316', 'width': 30, 'height': 30 }
        },
        {
          selector: 'node[node_type = "PAPER"]',
          style: { 'background-color': '#64748b', 'width': 18, 'height': 18 }
        },
        {
          selector: 'edge',
          style: {
            'width': 1.5,
            'line-color': '#334155',
            'target-arrow-color': '#334155',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'opacity': 0.7
          }
        },
        {
          selector: 'edge[status = "PROVEN"]',
          style: { 'line-color': '#10b981', 'target-arrow-color': '#10b981' }
        },
        {
          selector: 'edge[status = "HYPOTHESIZED_IN_SILICO"], edge[status = "HYPOTHESIZED"]',
          style: { 'line-color': '#f59e0b', 'target-arrow-color': '#f59e0b', 'line-style': 'dashed' }
        },
        {
          selector: 'edge[status = "SYNTHESIS_ORDERED"]',
          style: { 'line-color': '#38bdf8', 'target-arrow-color': '#38bdf8', 'line-style': 'dashed' }
        },
        {
          selector: 'edge[status = "ASSAY_VALIDATED"]',
          style: { 'line-color': '#06b6d4', 'target-arrow-color': '#06b6d4' }
        },
        {
          selector: 'edge[status = "ANIMAL_MODEL_TESTED"]',
          style: { 'line-color': '#8b5cf6', 'target-arrow-color': '#8b5cf6' }
        },
        {
          selector: 'edge[status = "FAILED"]',
          style: { 'line-color': '#ef4444', 'target-arrow-color': '#ef4444' }
        },
        {
          selector: ':selected',
          style: {
            'border-width': 4,
            'border-color': '#f8fafc',
            'line-color': '#38bdf8',
            'target-arrow-color': '#38bdf8',
            'opacity': 1.0
          }
        }
      ],
      layout: {
        name: 'cose',
        idealEdgeLength: 60,
        nodeOverlap: 20,
        refresh: 20,
        fit: true,
        padding: 30,
        randomize: false,
        componentSpacing: 100,
        nodeRepulsion: 400000,
        edgeElasticity: 100,
        nestingFactor: 5,
        gravity: 80,
        numIter: 1000
      }
    });

    cy.on('tap', 'node', function(evt) {
      const data = evt.target.data();
      const details = document.getElementById('details');
      
      let html = '';
      if (data.node_type === 'UNKNOWN') {
        html += `<div class="unknown-badge">⚠️ NEGATIVE SPACE GAP</div>`;
      }
      
      html += `<h3>${data.name || data.id}</h3>`;
      html += `<div class="detail-field"><span class="lbl">Node ID</span><span class="val">${data.id}</span></div>`;
      html += `<div class="detail-field"><span class="lbl">Type</span><span class="val">${data.node_type}</span></div>`;
      
      if (data.description) {
        html += `<div class="detail-field"><span class="lbl">Description</span><span class="val">${data.description}</span></div>`;
      }
      if (data.source) {
        html += `<div class="detail-field"><span class="lbl">Source</span><span class="val">${data.source}</span></div>`;
      }
      if (data.confidence !== undefined) {
        html += `<div class="detail-field"><span class="lbl">Confidence Score</span><span class="val">${data.confidence}</span></div>`;
      }

      if (data.has_3d_structure) {
        const plddt = data.alphafold_plddt || 0;
        const color = plddt >= 90 ? '#10b981' : plddt >= 70 ? '#38bdf8' : '#f59e0b';
        html += `<div class="detail-field"><span class="lbl">AlphaFold 3D Structure</span>`;
        html += `<span class="plddt-pill" style="background:${color}22; color:${color}; border:1px solid ${color};">pLDDT: ${plddt} (${data.alphafold_confidence})</span>`;
        if (data.alphafold_pdb_url) {
          html += `<div style="margin-top:6px;"><a href="${data.alphafold_pdb_url}" target="_blank" style="color:var(--accent); text-decoration:none; font-size:0.75rem;">⬇ Download Coordinate PDB</a></div>`;
        }
        html += `</div>`;
      }

      details.innerHTML = html;
    });

    cy.on('tap', 'edge', function(evt) {
      const data = evt.target.data();
      const details = document.getElementById('details');
      let html = `<h3>Causal Edge: ${data.edge_type || 'RELATION'}</h3>`;
      html += `<div class="detail-field"><span class="lbl">Source</span><span class="val">${data.source}</span></div>`;
      html += `<div class="detail-field"><span class="lbl">Target</span><span class="val">${data.target}</span></div>`;
      html += `<div class="detail-field"><span class="lbl">Status</span><span class="val">${data.status || 'PROVEN'}</span></div>`;
      if (data.confidence !== undefined) {
        html += `<div class="detail-field"><span class="lbl">Confidence</span><span class="val">${data.confidence}</span></div>`;
      }
      if (data.context) {
        html += `<div class="detail-field"><span class="lbl">Context</span><span class="val">${data.context}</span></div>`;
      }
      details.innerHTML = html;
    });

    document.getElementById('search').addEventListener('input', function(e) {
      const term = e.target.value.toLowerCase().trim();
      if (!term) {
        cy.elements().removeClass('highlighted');
        return;
      }
      cy.batch(() => {
        cy.nodes().forEach(node => {
          const name = (node.data('name') || '').toLowerCase();
          const id = (node.data('id') || '').toLowerCase();
          if (name.includes(term) || id.includes(term)) {
            node.select();
          } else {
            node.unselect();
          }
        });
      });
    });
  </script>
</body>
</html>
"""


def export_interactive_html(
    graph: EpistemicGraph,
    output_path: Optional[Path | str] = None,
    target_name: str = "Glucosepane Crosslink Repair",
) -> Path:
    """Export the EpistemicGraph to a standalone interactive HTML Cytoscape map.

    Args:
        graph: EpistemicGraph instance.
        output_path: Destination path for the HTML file.
        target_name: Human-readable target name for display.

    Returns:
        Path to the saved HTML file.
    """
    if output_path is None:
        out_dir = config.REPORTS_DIR
        out_dir.mkdir(parents=True, exist_ok=True)
        target_slug = target_name.lower().replace(" ", "_").replace("(", "").replace(")", "")
        output_path = out_dir / f"epistemic_map_{target_slug}.html"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # Use NetworkX built-in cytoscape format exporter
    cy_data = nx.cytoscape_data(graph.graph)

    # Inject data into template
    html_content = _HTML_TEMPLATE.replace("__TARGET_NAME__", target_name)
    html_content = html_content.replace("__GRAPH_JSON__", json.dumps(cy_data, ensure_ascii=False))

    output_path.write_text(html_content, encoding="utf-8")
    console.print(f"[bold green]✓ Interactive epistemic map exported to {output_path}[/bold green]")
    return output_path

#!/usr/bin/env python3
"""
Forecast Dashboard - Browser-based visualization for forecast runs.

Usage:
    python -m src.dashboard [--port 8000] [--data-dir ./data]

Then open http://localhost:8000 in your browser.
"""

import argparse
import json
import os
import re
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, unquote


def read_file_safe(path: Path) -> str | None:
    """Read file contents, return None if not found."""
    try:
        return path.read_text()
    except FileNotFoundError:
        return None


def read_json_safe(path: Path) -> dict | None:
    """Read JSON file, return None if not found or invalid."""
    content = read_file_safe(path)
    if content is None:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def list_forecast_runs(data_dir: Path) -> list[dict]:
    """List all forecast runs with metadata."""
    runs = []
    for entry in data_dir.iterdir():
        if not entry.is_dir():
            continue
        # Match pattern: {question_id}_{timestamp}
        match = re.match(r"(\d+)_(\d{8}_\d{6})", entry.name)
        if not match:
            continue

        question_id, timestamp = match.groups()
        metadata = read_json_safe(entry / "metadata.json")
        prediction = read_json_safe(entry / "prediction.json")

        if metadata is None:
            continue

        analysis = metadata.get("analysis", {})
        costs = metadata.get("costs", {})

        runs.append({
            "folder": entry.name,
            "question_id": question_id,
            "timestamp": timestamp,
            "title": analysis.get("title", "Unknown"),
            "type": analysis.get("type", "unknown"),
            "prediction": prediction.get("prediction") if prediction else None,
            "community_prediction": analysis.get("community_prediction"),
            "dry_run": prediction.get("dry_run", True) if prediction else True,
            "total_cost": costs.get("total_cost", 0),
            "mode": metadata.get("config_snapshot", {}).get("_effective_mode", "unknown"),
        })

    # Sort by timestamp descending (most recent first)
    runs.sort(key=lambda x: x["timestamp"], reverse=True)
    return runs


def load_forecast_detail(data_dir: Path, folder: str) -> dict[str, Any]:
    """Load full forecast details for visualization."""
    run_dir = data_dir / folder

    if not run_dir.exists():
        return {"error": f"Folder not found: {folder}"}

    data = {
        "folder": folder,
        "metadata": read_json_safe(run_dir / "metadata.json"),
        "prediction": read_json_safe(run_dir / "prediction.json"),
        "question": read_json_safe(run_dir / "question.json"),
        "research": {
            "query_historical_prompt": read_file_safe(run_dir / "research" / "query_historical_prompt.md"),
            "query_historical": read_file_safe(run_dir / "research" / "query_historical.md"),
            "query_current_prompt": read_file_safe(run_dir / "research" / "query_current_prompt.md"),
            "query_current": read_file_safe(run_dir / "research" / "query_current.md"),
            "search_historical": read_json_safe(run_dir / "research" / "search_historical.json"),
            "search_current": read_json_safe(run_dir / "research" / "search_current.json"),
        },
        "ensemble": {
            "step1_prompt": read_file_safe(run_dir / "ensemble" / "step1_prompt.md"),
            "aggregation": read_json_safe(run_dir / "ensemble" / "aggregation.json"),
            "agents": [],
        },
    }

    # Load agent data (1-5)
    for i in range(1, 6):
        agent_data = {
            "name": f"Agent {i}",
            "step1": read_file_safe(run_dir / "ensemble" / f"agent_{i}_step1.md"),
            "step2": read_file_safe(run_dir / "ensemble" / f"agent_{i}_step2.md"),
            "result": read_json_safe(run_dir / "ensemble" / f"agent_{i}.json"),
        }

        # Get model from metadata
        if data["metadata"]:
            agents = data["metadata"].get("config_snapshot", {}).get("_active_agents", [])
            if i <= len(agents):
                agent_data["model"] = agents[i - 1].get("model", "unknown")

        data["ensemble"]["agents"].append(agent_data)

    return data


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def format_probability(prob: float | None) -> str:
    """Format probability for display."""
    if prob is None:
        return "N/A"
    if isinstance(prob, (int, float)):
        # Handle both 0-1 and 0-100 ranges
        if prob > 1:
            return f"{prob:.1f}%"
        return f"{prob * 100:.1f}%"
    return str(prob)


def format_cost(cost: float | None) -> str:
    """Format cost for display."""
    if cost is None:
        return "N/A"
    return f"${cost:.4f}"


def format_timestamp(ts: str) -> str:
    """Format timestamp for display."""
    try:
        dt = datetime.strptime(ts, "%Y%m%d_%H%M%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return ts


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Forecast Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        .collapsible-content { max-height: 0; overflow: hidden; transition: max-height 0.3s ease-out; }
        .collapsible-content.open { max-height: none; }
        .markdown-content h1 { font-size: 1.5rem; font-weight: bold; margin-top: 1rem; }
        .markdown-content h2 { font-size: 1.25rem; font-weight: bold; margin-top: 0.75rem; }
        .markdown-content h3 { font-size: 1.1rem; font-weight: bold; margin-top: 0.5rem; }
        .markdown-content p { margin: 0.5rem 0; }
        .markdown-content ul { list-style-type: disc; margin-left: 1.5rem; }
        .markdown-content ol { list-style-type: decimal; margin-left: 1.5rem; }
        .markdown-content code { background: #1f2937; padding: 0.125rem 0.25rem; border-radius: 0.25rem; font-size: 0.875rem; }
        .markdown-content pre { background: #1f2937; padding: 1rem; border-radius: 0.5rem; overflow-x: auto; margin: 0.5rem 0; }
        .markdown-content pre code { background: none; padding: 0; }
        .markdown-content blockquote { border-left: 4px solid #4b5563; padding-left: 1rem; margin: 0.5rem 0; color: #9ca3af; }
    </style>
</head>
<body class="bg-gray-900 text-gray-100 min-h-screen">
    <div id="app" class="container mx-auto px-4 py-8 max-w-6xl">
        <!-- Content injected by JavaScript -->
    </div>

    <script>
        // State
        let currentView = 'list';
        let currentFolder = null;
        let forecastData = null;

        // Navigation
        function navigateTo(view, folder = null) {
            currentView = view;
            currentFolder = folder;
            if (view === 'list') {
                history.pushState({}, '', '/');
                loadList();
            } else if (view === 'detail' && folder) {
                history.pushState({}, '', '/view/' + folder);
                loadDetail(folder);
            }
        }

        window.onpopstate = () => {
            const path = window.location.pathname;
            if (path.startsWith('/view/')) {
                const folder = path.substring(6);
                currentView = 'detail';
                currentFolder = folder;
                loadDetail(folder);
            } else {
                currentView = 'list';
                currentFolder = null;
                loadList();
            }
        };

        // Toggle collapsible sections
        function toggleSection(id) {
            const content = document.getElementById(id);
            const icon = document.getElementById(id + '-icon');
            if (content.classList.contains('open')) {
                content.classList.remove('open');
                icon.textContent = '+';
            } else {
                content.classList.add('open');
                icon.textContent = '-';
            }
        }

        // Render markdown
        function renderMarkdown(text) {
            if (!text) return '<span class="text-gray-500 italic">Not available</span>';
            return marked.parse(text);
        }

        // Load forecast list
        async function loadList() {
            const app = document.getElementById('app');
            app.innerHTML = '<div class="text-center py-8">Loading...</div>';

            try {
                const response = await fetch('/api/list');
                const runs = await response.json();
                renderList(runs);
            } catch (err) {
                app.innerHTML = '<div class="text-red-500">Error loading forecasts: ' + err.message + '</div>';
            }
        }

        function renderList(runs) {
            const app = document.getElementById('app');

            let html = `
                <h1 class="text-3xl font-bold mb-6">Forecast Dashboard</h1>
                <p class="text-gray-400 mb-6">${runs.length} forecast runs</p>
                <div class="space-y-3">
            `;

            for (const run of runs) {
                const predDisplay = run.prediction !== null
                    ? (run.prediction > 1 ? run.prediction.toFixed(1) + '%' : (run.prediction * 100).toFixed(1) + '%')
                    : 'N/A';
                const communityDisplay = run.community_prediction !== null
                    ? (run.community_prediction * 100).toFixed(1) + '%'
                    : 'N/A';
                const costDisplay = run.total_cost ? '$' + run.total_cost.toFixed(4) : '';
                const modeColor = run.dry_run ? 'text-yellow-500' : 'text-green-500';
                const modeBadge = run.dry_run ? 'DRY RUN' : 'SUBMITTED';

                html += `
                    <div class="bg-gray-800 rounded-lg p-4 hover:bg-gray-750 cursor-pointer border border-gray-700 hover:border-gray-600 transition-colors"
                         onclick="navigateTo('detail', '${run.folder}')">
                        <div class="flex justify-between items-start mb-2">
                            <span class="text-sm text-gray-400">${run.timestamp.replace('_', ' ')}</span>
                            <span class="text-xs ${modeColor} font-mono">${modeBadge}</span>
                        </div>
                        <h2 class="text-lg font-medium mb-2 text-blue-400 hover:text-blue-300">${escapeHtml(run.title)}</h2>
                        <div class="flex gap-6 text-sm">
                            <span class="text-gray-400">Type: <span class="text-gray-200">${run.type}</span></span>
                            <span class="text-gray-400">Prediction: <span class="text-green-400 font-mono">${predDisplay}</span></span>
                            <span class="text-gray-400">Community: <span class="text-blue-400 font-mono">${communityDisplay}</span></span>
                            ${costDisplay ? `<span class="text-gray-400">Cost: <span class="text-gray-200">${costDisplay}</span></span>` : ''}
                        </div>
                    </div>
                `;
            }

            html += '</div>';
            app.innerHTML = html;
        }

        // Load forecast detail
        async function loadDetail(folder) {
            const app = document.getElementById('app');
            app.innerHTML = '<div class="text-center py-8">Loading...</div>';

            try {
                const response = await fetch('/api/detail/' + folder);
                forecastData = await response.json();
                renderDetail(forecastData);
            } catch (err) {
                app.innerHTML = '<div class="text-red-500">Error loading forecast: ' + err.message + '</div>';
            }
        }

        function renderDetail(data) {
            const app = document.getElementById('app');
            const meta = data.metadata || {};
            const analysis = meta.analysis || {};
            const costs = meta.costs || {};
            const timing = meta.timing || {};
            const prediction = data.prediction || {};
            const agg = data.ensemble?.aggregation || {};

            const predDisplay = prediction.prediction !== undefined
                ? (prediction.prediction > 1 ? prediction.prediction.toFixed(1) + '%' : (prediction.prediction * 100).toFixed(1) + '%')
                : 'N/A';

            let html = `
                <button onclick="navigateTo('list')" class="text-blue-400 hover:text-blue-300 mb-4 flex items-center gap-2">
                    <span>&larr;</span> Back to list
                </button>

                <!-- Question Header -->
                <div class="bg-gray-800 rounded-lg p-6 mb-6 border border-gray-700">
                    <div class="flex justify-between items-start mb-4">
                        <span class="text-sm text-gray-400">${data.folder}</span>
                        <span class="text-xs ${prediction.dry_run ? 'text-yellow-500' : 'text-green-500'} font-mono">
                            ${prediction.dry_run ? 'DRY RUN' : 'SUBMITTED'}
                        </span>
                    </div>
                    <h1 class="text-2xl font-bold mb-4">${escapeHtml(analysis.title || 'Unknown Question')}</h1>

                    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                            <span class="text-gray-400">Type</span>
                            <div class="text-lg">${analysis.type || 'unknown'}</div>
                        </div>
                        <div>
                            <span class="text-gray-400">Final Prediction</span>
                            <div class="text-lg text-green-400 font-mono">${predDisplay}</div>
                        </div>
                        <div>
                            <span class="text-gray-400">Community</span>
                            <div class="text-lg text-blue-400 font-mono">${analysis.community_prediction ? (analysis.community_prediction * 100).toFixed(1) + '%' : 'N/A'}</div>
                        </div>
                        <div>
                            <span class="text-gray-400">Cost</span>
                            <div class="text-lg">$${(costs.total_cost || 0).toFixed(4)}</div>
                        </div>
                    </div>

                    ${timing.duration_seconds ? `
                    <div class="mt-4 text-sm text-gray-400">
                        Duration: ${timing.duration_seconds.toFixed(1)}s |
                        LLM Calls: ${costs.total_calls || 0} |
                        Tokens: ${(costs.total_input_tokens || 0).toLocaleString()} in / ${(costs.total_output_tokens || 0).toLocaleString()} out
                    </div>
                    ` : ''}
                </div>

                <!-- Research Section -->
                <div class="bg-gray-800 rounded-lg mb-6 border border-gray-700">
                    <div class="p-4 border-b border-gray-700">
                        <h2 class="text-xl font-bold">Research</h2>
                    </div>

                    ${renderCollapsible('research-hist-prompt', 'Historical Query Prompt', data.research?.query_historical_prompt, false)}
                    ${renderCollapsible('research-hist-queries', 'Historical Queries', data.research?.query_historical, true)}
                    ${renderCollapsible('research-curr-prompt', 'Current Query Prompt', data.research?.query_current_prompt, false)}
                    ${renderCollapsible('research-curr-queries', 'Current Queries', data.research?.query_current, true)}
                    ${renderCollapsible('research-hist-results', 'Historical Search Results', formatSearchResults(data.research?.search_historical), true)}
                    ${renderCollapsible('research-curr-results', 'Current Search Results', formatSearchResults(data.research?.search_current), true)}
                </div>

                <!-- Ensemble Section -->
                <div class="bg-gray-800 rounded-lg mb-6 border border-gray-700">
                    <div class="p-4 border-b border-gray-700">
                        <h2 class="text-xl font-bold">Ensemble (${data.ensemble?.agents?.length || 0} Agents)</h2>
                    </div>

                    ${renderCollapsible('step1-prompt', 'Step 1 Prompt (Outside View)', data.ensemble?.step1_prompt, false)}

                    <!-- Agents -->
                    ${(data.ensemble?.agents || []).map((agent, i) => renderAgent(agent, i, agg)).join('')}
                </div>

                <!-- Aggregation -->
                <div class="bg-gray-800 rounded-lg mb-6 border border-gray-700 p-4">
                    <h2 class="text-xl font-bold mb-4">Aggregation</h2>
                    <div class="grid grid-cols-5 gap-4 mb-4">
                        ${(agg.individual_probabilities || []).map((p, i) => `
                            <div class="text-center">
                                <div class="text-sm text-gray-400">Agent ${i + 1}</div>
                                <div class="text-lg font-mono ${getAgentColor(i)}">${p > 1 ? p.toFixed(1) : (p * 100).toFixed(1)}%</div>
                                <div class="text-xs text-gray-500">weight: ${(agg.weights || [])[i] || 1}</div>
                            </div>
                        `).join('')}
                    </div>
                    <div class="text-center pt-4 border-t border-gray-700">
                        <div class="text-sm text-gray-400">Final (${agg.method || 'weighted_average'})</div>
                        <div class="text-3xl font-mono text-green-400">${predDisplay}</div>
                    </div>
                </div>
            `;

            app.innerHTML = html;
        }

        function renderCollapsible(id, title, content, startOpen = false) {
            const hasContent = content && content.trim();
            return `
                <div class="border-b border-gray-700 last:border-b-0">
                    <button onclick="toggleSection('${id}')"
                            class="w-full p-4 text-left flex justify-between items-center hover:bg-gray-750 transition-colors">
                        <span class="font-medium">${title}</span>
                        <span id="${id}-icon" class="text-gray-400 w-6 text-center">${startOpen ? '-' : '+'}</span>
                    </button>
                    <div id="${id}" class="collapsible-content ${startOpen ? 'open' : ''} px-4 pb-4">
                        <div class="markdown-content bg-gray-850 rounded p-4 text-sm overflow-auto max-h-96">
                            ${hasContent ? renderMarkdown(content) : '<span class="text-gray-500 italic">Not available</span>'}
                        </div>
                    </div>
                </div>
            `;
        }

        function renderAgent(agent, index, agg) {
            const prob = agent.result?.probability;
            const probDisplay = prob !== undefined ? (prob > 1 ? prob.toFixed(1) + '%' : (prob * 100).toFixed(1) + '%') : 'N/A';
            const error = agent.result?.error;
            const modelShort = agent.model ? agent.model.split('/').pop() : 'unknown';

            return `
                <div class="border-b border-gray-700">
                    <div class="p-4 bg-gray-750">
                        <div class="flex justify-between items-center">
                            <div>
                                <span class="font-bold ${getAgentColor(index)}">Agent ${index + 1}</span>
                                <span class="text-gray-400 text-sm ml-2">${modelShort}</span>
                            </div>
                            <div class="text-right">
                                ${error
                                    ? `<span class="text-red-400">Error: ${escapeHtml(error)}</span>`
                                    : `<span class="font-mono ${getAgentColor(index)}">${probDisplay}</span>`
                                }
                            </div>
                        </div>
                    </div>
                    ${renderCollapsible('agent-' + index + '-step1', 'Step 1: Outside View', agent.step1, false)}
                    ${renderCollapsible('agent-' + index + '-step2', 'Step 2: Inside View', agent.step2, false)}
                </div>
            `;
        }

        function formatSearchResults(searchData) {
            if (!searchData) return null;
            if (typeof searchData === 'string') return searchData;
            if (searchData.context) return searchData.context;
            return JSON.stringify(searchData, null, 2);
        }

        function getAgentColor(index) {
            const colors = ['text-blue-400', 'text-green-400', 'text-yellow-400', 'text-purple-400', 'text-pink-400'];
            return colors[index % colors.length];
        }

        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Initialize
        const path = window.location.pathname;
        if (path.startsWith('/view/')) {
            const folder = path.substring(6);
            currentView = 'detail';
            currentFolder = folder;
            loadDetail(folder);
        } else {
            loadList();
        }
    </script>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the dashboard."""

    data_dir: Path = Path("./data")

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def send_json(self, data: Any, status: int = 200):
        """Send JSON response."""
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html: str, status: int = 200):
        """Send HTML response."""
        body = html.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path == "/api/list":
            runs = list_forecast_runs(self.data_dir)
            self.send_json(runs)

        elif path.startswith("/api/detail/"):
            folder = path[12:]  # Remove "/api/detail/"
            data = load_forecast_detail(self.data_dir, folder)
            self.send_json(data)

        elif path == "/" or path.startswith("/view/"):
            self.send_html(HTML_TEMPLATE)

        else:
            self.send_response(404)
            self.end_headers()


def run_server(port: int = 8000, data_dir: str = "./data"):
    """Run the dashboard server."""
    DashboardHandler.data_dir = Path(data_dir)

    if not DashboardHandler.data_dir.exists():
        print(f"Error: Data directory not found: {data_dir}")
        return

    server = HTTPServer(("", port), DashboardHandler)
    print(f"Dashboard running at http://localhost:{port}")
    print(f"Data directory: {DashboardHandler.data_dir.absolute()}")
    print("Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


def main():
    parser = argparse.ArgumentParser(description="Forecast Dashboard")
    parser.add_argument("--port", type=int, default=8000, help="Port to run on (default: 8000)")
    parser.add_argument("--data-dir", default="./data", help="Data directory (default: ./data)")
    args = parser.parse_args()

    run_server(port=args.port, data_dir=args.data_dir)


if __name__ == "__main__":
    main()

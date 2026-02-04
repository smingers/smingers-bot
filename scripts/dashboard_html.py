#!/usr/bin/env python3
"""
Forecast Dashboard - Browser-based visualization for forecast runs.

Usage:
    python scripts/dashboard_html.py [--port 8000] [--data-dir ./data]

Then open http://localhost:8000 in your browser.
"""

import argparse
import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


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


def compute_percentiles_from_cdf(cdf: list[float], scaling: dict) -> dict[str, float]:
    """
    Compute actual percentile values from CDF and question scaling.

    For numeric questions, the CDF array contains cumulative probabilities,
    and scaling.continuous_range contains the corresponding actual values.
    """
    if not cdf or not scaling:
        return {}

    continuous_range = scaling.get("continuous_range", [])
    if not continuous_range:
        # Try to compute range from min/max
        range_min = scaling.get("range_min") or scaling.get("nominal_min")
        range_max = scaling.get("range_max") or scaling.get("nominal_max")
        if range_min is not None and range_max is not None:
            # Create linear range with same number of points as CDF
            n = len(cdf)
            continuous_range = [range_min + (range_max - range_min) * i / (n - 1) for i in range(n)]
        else:
            return {}

    percentile_targets = [1, 5, 10, 25, 50, 75, 90, 95, 99]
    result = {}

    for p in percentile_targets:
        target = p / 100.0
        # Find index where CDF crosses this threshold
        for i, cdf_val in enumerate(cdf):
            if cdf_val >= target:
                # Linear interpolation for better accuracy
                if i > 0 and cdf[i - 1] < target:
                    # Interpolate between i-1 and i
                    frac = (
                        (target - cdf[i - 1]) / (cdf_val - cdf[i - 1])
                        if cdf_val != cdf[i - 1]
                        else 0
                    )
                    if i < len(continuous_range) and i - 1 < len(continuous_range):
                        val = continuous_range[i - 1] + frac * (
                            continuous_range[i] - continuous_range[i - 1]
                        )
                        result[str(p)] = val
                elif i < len(continuous_range):
                    result[str(p)] = continuous_range[i]
                break
        else:
            # CDF never reached target, use max value
            if continuous_range:
                result[str(p)] = continuous_range[-1]

    return result


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

        if metadata is None:
            continue

        analysis = metadata.get("analysis", {})
        final_pred = read_json_safe(entry / "prediction.json")
        question = read_json_safe(entry / "question.json")

        costs = metadata.get("costs", {})
        question_type = analysis.get("type", "unknown")

        # Extract prediction based on question type
        prediction = None
        if final_pred:
            if question_type == "binary":
                prediction = final_pred.get("prediction")
            elif question_type == "numeric":
                # For numeric, compute actual median value from CDF
                cdf = final_pred.get("cdf", [])
                if cdf and question:
                    scaling = question.get("question", {}).get("scaling", {})
                    if scaling:
                        computed = compute_percentiles_from_cdf(cdf, scaling)
                        prediction = computed.get("50")
                # Fallback to raw percentile if computation failed
                if prediction is None:
                    percentiles = final_pred.get("percentiles", {})
                    prediction = percentiles.get("50") or percentiles.get(50)
            elif question_type == "multiple_choice":
                # For MC, just indicate it exists
                prediction = "distribution"

        # Check if prediction was actually submitted
        # submitted=true in prediction file, or mode=live in config
        if final_pred:
            submitted = final_pred.get("submitted", False)
        else:
            submitted = False

        runs.append(
            {
                "folder": entry.name,
                "question_id": question_id,
                "timestamp": timestamp,
                "title": analysis.get("title", "Unknown"),
                "type": question_type,
                "prediction": prediction,
                "community_prediction": analysis.get("community_prediction"),
                "submitted": submitted,
                "total_cost": costs.get("total_cost", 0),
                "mode": metadata.get("config_snapshot", {}).get("mode", "unknown"),
            }
        )

    # Sort by timestamp descending (most recent first)
    runs.sort(key=lambda run: run["timestamp"], reverse=True)
    return runs


def load_forecast_detail(data_dir: Path, folder: str) -> dict[str, Any]:
    """Load full forecast details for visualization."""
    run_dir = data_dir / folder

    if not run_dir.exists():
        return {"error": f"Folder not found: {folder}"}

    metadata = read_json_safe(run_dir / "metadata.json")
    prediction = read_json_safe(run_dir / "prediction.json")
    analysis = metadata.get("analysis", {}) if metadata else {}
    question = read_json_safe(run_dir / "question.json")

    # For numeric questions, compute actual percentile values from CDF
    computed_percentiles = None
    if analysis.get("type") == "numeric" and prediction and question:
        cdf = prediction.get("cdf", [])
        # Get scaling from nested question structure
        scaling = question.get("question", {}).get("scaling", {})
        if cdf and scaling:
            computed_percentiles = compute_percentiles_from_cdf(cdf, scaling)

    data = {
        "folder": folder,
        "metadata": metadata,
        "analysis": analysis,
        "question_type": analysis.get("type", "unknown"),
        "prediction": prediction,
        "computed_percentiles": computed_percentiles,  # Actual values at percentiles
        "question": question,
        "research": {
            "query_historical_prompt": read_file_safe(
                run_dir / "research" / "query_historical_prompt.md"
            ),
            "query_historical": read_file_safe(run_dir / "research" / "query_historical.md"),
            "query_current_prompt": read_file_safe(
                run_dir / "research" / "query_current_prompt.md"
            ),
            "query_current": read_file_safe(run_dir / "research" / "query_current.md"),
            "search_historical": read_json_safe(run_dir / "research" / "search_historical.json"),
            "search_current": read_json_safe(run_dir / "research" / "search_current.json"),
        },
        "ensemble": {
            # Try current naming first, fall back to old naming
            "step1_prompt": (
                read_file_safe(run_dir / "ensemble" / "outside_view_prompt.md")
                or read_file_safe(run_dir / "ensemble" / "step1_prompt.md")
            ),
            "aggregation": read_json_safe(run_dir / "ensemble" / "aggregation.json"),
            "agents": [],
        },
    }

    # Load agent data (1-5)
    # Try current naming (forecaster_{i}_outside_view.md) first, fall back to old (agent_{i}_step1.md)
    for i in range(1, 6):
        agent_data = {
            "name": f"Forecaster {i}",
            "step1": (
                read_file_safe(run_dir / "ensemble" / f"forecaster_{i}_outside_view.md")
                or read_file_safe(run_dir / "ensemble" / f"agent_{i}_step1.md")
            ),
            "step2": (
                read_file_safe(run_dir / "ensemble" / f"forecaster_{i}_inside_view.md")
                or read_file_safe(run_dir / "ensemble" / f"agent_{i}_step2.md")
            ),
            "result": (
                read_json_safe(run_dir / "ensemble" / f"forecaster_{i}.json")
                or read_json_safe(run_dir / "ensemble" / f"agent_{i}.json")
            ),
        }

        # Get model from metadata
        if metadata:
            agents = metadata.get("config_snapshot", {}).get("_active_agents", [])
            if i <= len(agents):
                agent_data["model"] = agents[i - 1].get("model", "unknown")

        data["ensemble"]["agents"].append(agent_data)

    return data


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
        .bar-chart { display: flex; flex-direction: column; gap: 0.5rem; }
        .bar-row { display: flex; align-items: center; gap: 0.5rem; }
        .bar-label { width: 200px; font-size: 0.875rem; text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .bar-container { flex: 1; background: #374151; border-radius: 0.25rem; height: 1.5rem; }
        .bar-fill { height: 100%; border-radius: 0.25rem; transition: width 0.3s; }
        .bar-value { width: 60px; font-size: 0.875rem; font-family: monospace; }
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

        function formatListPrediction(run) {
            if (run.prediction === null || run.prediction === undefined) return 'N/A';
            if (run.type === 'numeric') {
                return 'median: ' + run.prediction.toLocaleString();
            }
            if (run.type === 'multiple_choice') {
                return 'distribution';
            }
            // Binary
            const p = run.prediction;
            return (p > 1 ? p.toFixed(1) : (p * 100).toFixed(1)) + '%';
        }

        function renderList(runs) {
            const app = document.getElementById('app');

            let html = `
                <h1 class="text-3xl font-bold mb-6">Forecast Dashboard</h1>
                <p class="text-gray-400 mb-6">${runs.length} forecast runs</p>
                <div class="space-y-3">
            `;

            for (const run of runs) {
                const predDisplay = formatListPrediction(run);
                const communityDisplay = run.community_prediction !== null
                    ? (run.community_prediction * 100).toFixed(1) + '%'
                    : 'N/A';
                const costDisplay = run.total_cost ? '$' + run.total_cost.toFixed(4) : '';
                const modeColor = getModeColor(run.mode);
                const modeBadge = (run.mode || 'unknown').toUpperCase();
                const typeColor = {
                    'binary': 'bg-blue-900 text-blue-300',
                    'numeric': 'bg-purple-900 text-purple-300',
                    'multiple_choice': 'bg-orange-900 text-orange-300'
                }[run.type] || 'bg-gray-700 text-gray-300';

                html += `
                    <div class="bg-gray-800 rounded-lg p-4 hover:bg-gray-750 cursor-pointer border border-gray-700 hover:border-gray-600 transition-colors"
                         onclick="navigateTo('detail', '${run.folder}')">
                        <div class="flex justify-between items-start mb-2">
                            <div class="flex items-center gap-2">
                                <span class="text-sm text-gray-400">${run.timestamp.replace('_', ' ')}</span>
                                <span class="text-xs px-2 py-0.5 rounded ${typeColor}">${run.type}</span>
                            </div>
                            <span class="text-xs ${modeColor} font-mono">${modeBadge}</span>
                        </div>
                        <h2 class="text-lg font-medium mb-2 text-blue-400 hover:text-blue-300">${escapeHtml(run.title)}</h2>
                        <div class="flex gap-6 text-sm">
                            <span class="text-gray-400">Prediction: <span class="text-green-400 font-mono">${predDisplay}</span></span>
                            ${run.type === 'binary' ? `<span class="text-gray-400">Community: <span class="text-blue-400 font-mono">${communityDisplay}</span></span>` : ''}
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
            const analysis = data.analysis || {};
            const costs = meta.costs || {};
            const timing = meta.timing || {};
            const prediction = data.prediction || {};
            const agg = data.ensemble?.aggregation || {};
            const questionType = data.question_type || 'binary';
            const computedPercentiles = data.computed_percentiles || null;

            let html = `
                <button onclick="navigateTo('list')" class="text-blue-400 hover:text-blue-300 mb-4 flex items-center gap-2">
                    <span>&larr;</span> Back to list
                </button>

                <!-- Question Header -->
                <div class="bg-gray-800 rounded-lg p-6 mb-6 border border-gray-700">
                    <div class="flex justify-between items-start mb-4">
                        <div class="flex items-center gap-2">
                            <span class="text-sm text-gray-400">${data.folder}</span>
                            <span class="text-xs px-2 py-0.5 rounded ${getTypeColor(questionType)}">${questionType}</span>
                        </div>
                        <span class="text-xs ${getModeColor(meta.config_snapshot?.mode)} font-mono">
                            ${(meta.config_snapshot?.mode || 'unknown').toUpperCase()}
                        </span>
                    </div>
                    <h1 class="text-2xl font-bold mb-4">${escapeHtml(analysis.title || 'Unknown Question')}</h1>

                    ${renderPredictionHeader(questionType, prediction, analysis, costs, computedPercentiles)}

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
                    ${(data.ensemble?.agents || []).map((agent, i) => renderAgent(agent, i, questionType)).join('')}
                </div>

                <!-- Aggregation -->
                ${renderAggregation(questionType, agg, prediction)}
            `;

            app.innerHTML = html;
        }

        function getTypeColor(type) {
            return {
                'binary': 'bg-blue-900 text-blue-300',
                'numeric': 'bg-purple-900 text-purple-300',
                'multiple_choice': 'bg-orange-900 text-orange-300'
            }[type] || 'bg-gray-700 text-gray-300';
        }

        function getModeColor(mode) {
            return {
                'test': 'text-yellow-500',
                'preview': 'text-blue-500',
                'live': 'text-green-500'
            }[mode] || 'text-gray-500';
        }

        function renderPredictionHeader(type, prediction, analysis, costs, computedPercentiles) {
            if (type === 'binary') {
                const prob = prediction.prediction;
                const probDisplay = prob !== undefined
                    ? (prob > 1 ? prob.toFixed(1) + '%' : (prob * 100).toFixed(1) + '%')
                    : 'N/A';
                return `
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                            <span class="text-gray-400">Type</span>
                            <div class="text-lg">${type}</div>
                        </div>
                        <div>
                            <span class="text-gray-400">Final Prediction</span>
                            <div class="text-lg text-green-400 font-mono">${probDisplay}</div>
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
                `;
            } else if (type === 'numeric') {
                // Use computed percentiles (actual values) if available, fall back to raw percentiles
                const percentiles = computedPercentiles || prediction.percentiles || {};
                const hasComputedPercentiles = computedPercentiles !== null;

                // Format numbers nicely - use integers for large values, decimals for small
                const formatValue = (val) => {
                    if (val === undefined || val === null) return '-';
                    if (Math.abs(val) >= 100) return Math.round(val).toLocaleString();
                    if (Math.abs(val) >= 10) return val.toFixed(1);
                    if (Math.abs(val) >= 1) return val.toFixed(2);
                    return val.toFixed(3);
                };

                return `
                    <div class="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm mb-4">
                        <div>
                            <span class="text-gray-400">Type</span>
                            <div class="text-lg">${type}</div>
                        </div>
                        <div>
                            <span class="text-gray-400">Median (P50)</span>
                            <div class="text-lg text-green-400 font-mono">${formatValue(percentiles['50'])}</div>
                        </div>
                        <div>
                            <span class="text-gray-400">Cost</span>
                            <div class="text-lg">$${(costs.total_cost || 0).toFixed(4)}</div>
                        </div>
                    </div>
                    <div class="bg-gray-750 rounded p-4">
                        <div class="text-sm text-gray-400 mb-2">Percentile Distribution${hasComputedPercentiles ? '' : ' <span class="text-yellow-500">(raw CDF values - scaling unavailable)</span>'}</div>
                        <div class="grid grid-cols-5 gap-2 text-center text-sm">
                            ${['1', '5', '10', '25', '50', '75', '90', '95', '99'].map(p => `
                                <div>
                                    <div class="text-gray-500">P${p}</div>
                                    <div class="font-mono ${p === '50' ? 'text-green-400' : 'text-gray-300'}">${formatValue(percentiles[p])}</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            } else if (type === 'multiple_choice') {
                return `
                    <div class="grid grid-cols-2 gap-4 text-sm mb-4">
                        <div>
                            <span class="text-gray-400">Type</span>
                            <div class="text-lg">${type}</div>
                        </div>
                        <div>
                            <span class="text-gray-400">Cost</span>
                            <div class="text-lg">$${(costs.total_cost || 0).toFixed(4)}</div>
                        </div>
                    </div>
                `;
            }
            return '';
        }

        function renderAggregation(type, agg, prediction) {
            if (type === 'binary') {
                const prob = prediction.prediction;
                const probDisplay = prob !== undefined
                    ? (prob > 1 ? prob.toFixed(1) + '%' : (prob * 100).toFixed(1) + '%')
                    : 'N/A';
                return `
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
                            <div class="text-3xl font-mono text-green-400">${probDisplay}</div>
                        </div>
                    </div>
                `;
            } else if (type === 'numeric') {
                // Get individual agent percentiles from the data
                const agents = forecastData?.ensemble?.agents || [];
                const percentileKeys = ['1', '5', '10', '20', '40', '60', '80', '90', '95', '99'];

                // Format value for display - use B/M/K suffixes for large numbers
                const formatValue = (val) => {
                    if (val === undefined || val === null) return '-';
                    const absVal = Math.abs(val);
                    if (absVal >= 1e9) return (val / 1e9).toFixed(1) + 'B';
                    if (absVal >= 1e6) return (val / 1e6).toFixed(1) + 'M';
                    if (absVal >= 1e3) return (val / 1e3).toFixed(1) + 'K';
                    if (absVal >= 100) return Math.round(val).toLocaleString();
                    if (absVal >= 10) return val.toFixed(1);
                    if (absVal >= 1) return val.toFixed(2);
                    return val.toFixed(3);
                };

                // Get final percentiles from computed percentiles if available
                const finalPercentiles = forecastData?.computed_percentiles || {};

                // Build table rows
                const tableRows = percentileKeys.map(p => {
                    const agentValues = agents.map(agent => {
                        const percentiles = agent.result?.percentiles || {};
                        return percentiles[p] || percentiles[parseInt(p)];
                    });
                    const finalVal = finalPercentiles[p];
                    return { percentile: p, agentValues, finalVal };
                });

                return `
                    <div class="bg-gray-800 rounded-lg mb-6 border border-gray-700 p-4">
                        <h2 class="text-xl font-bold mb-4">Aggregation</h2>
                        <div class="overflow-x-auto">
                            <table class="w-full text-sm">
                                <thead>
                                    <tr class="border-b border-gray-600">
                                        <th class="text-left py-2 px-3 text-gray-400 font-medium">Percentile</th>
                                        ${agents.map((_, i) => `
                                            <th class="text-right py-2 px-3 ${getAgentColor(i)} font-medium">Agent ${i + 1}</th>
                                        `).join('')}
                                        <th class="text-right py-2 px-3 text-green-400 font-medium">Final</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${tableRows.map(row => `
                                        <tr class="border-b border-gray-700 hover:bg-gray-750">
                                            <td class="py-2 px-3 text-gray-300">P${row.percentile}</td>
                                            ${row.agentValues.map((val, i) => `
                                                <td class="text-right py-2 px-3 font-mono ${getAgentColor(i)}">${formatValue(val)}</td>
                                            `).join('')}
                                            <td class="text-right py-2 px-3 font-mono text-green-400 font-semibold">${formatValue(row.finalVal)}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                        <div class="mt-4 text-sm text-gray-400 text-center">
                            ${agg.num_valid_cdfs || agents.length} CDFs aggregated using ${agg.method || 'weighted_average'}
                        </div>
                    </div>
                `;
            } else if (type === 'multiple_choice') {
                const finalProbs = agg.final_probabilities || {};
                const entries = Object.entries(finalProbs).sort((a, b) => b[1] - a[1]);
                const maxProb = Math.max(...Object.values(finalProbs), 0.01);

                return `
                    <div class="bg-gray-800 rounded-lg mb-6 border border-gray-700 p-4">
                        <h2 class="text-xl font-bold mb-4">Final Distribution</h2>
                        <div class="bar-chart">
                            ${entries.map(([option, prob], i) => `
                                <div class="bar-row">
                                    <div class="bar-label text-gray-300" title="${escapeHtml(option)}">${escapeHtml(option)}</div>
                                    <div class="bar-container">
                                        <div class="bar-fill ${getBarColor(i)}" style="width: ${(prob / maxProb * 100).toFixed(1)}%"></div>
                                    </div>
                                    <div class="bar-value text-gray-300">${(prob * 100).toFixed(1)}%</div>
                                </div>
                            `).join('')}
                        </div>
                        <div class="mt-4 text-sm text-gray-400">
                            Aggregated using ${agg.method || 'weighted_average'} across ${(agg.weights || []).length} agents
                        </div>
                    </div>
                `;
            }
            return '';
        }

        function getBarColor(index) {
            const colors = ['bg-blue-500', 'bg-green-500', 'bg-yellow-500', 'bg-purple-500', 'bg-pink-500', 'bg-indigo-500', 'bg-red-500', 'bg-orange-500'];
            return colors[index % colors.length];
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

        function renderAgent(agent, index, questionType) {
            const result = agent.result || {};
            const error = result.error;
            const modelShort = agent.model ? agent.model.split('/').pop() : 'unknown';

            let resultDisplay;
            if (error) {
                resultDisplay = `<span class="text-red-400">Error: ${escapeHtml(error)}</span>`;
            } else if (questionType === 'binary') {
                const prob = result.probability;
                const probDisplay = prob !== undefined ? (prob > 1 ? prob.toFixed(1) + '%' : (prob * 100).toFixed(1) + '%') : 'N/A';
                resultDisplay = `<span class="font-mono ${getAgentColor(index)}">${probDisplay}</span>`;
            } else if (questionType === 'numeric') {
                const percentiles = result.percentiles || {};
                // Agents use different percentile points (40, 60) not (50)
                // Use 40 and 60 to approximate median, or fall back to any available percentile
                let median = percentiles['50'] || percentiles[50];
                if (median === undefined) {
                    // Interpolate between P40 and P60
                    const p40 = percentiles['40'] || percentiles[40];
                    const p60 = percentiles['60'] || percentiles[60];
                    if (p40 !== undefined && p60 !== undefined) {
                        median = (p40 + p60) / 2;
                    } else {
                        // Fallback to any available percentile
                        median = p40 || p60 || percentiles['20'] || percentiles[20];
                    }
                }
                const formatValue = (val) => {
                    if (val === undefined || val === null) return 'N/A';
                    if (Math.abs(val) >= 100) return Math.round(val).toLocaleString();
                    if (Math.abs(val) >= 10) return val.toFixed(1);
                    if (Math.abs(val) >= 1) return val.toFixed(2);
                    return val.toFixed(3);
                };
                resultDisplay = `<span class="font-mono ${getAgentColor(index)}">~P50: ${formatValue(median)}</span>`;
            } else if (questionType === 'multiple_choice') {
                const probs = result.probabilities || [];
                const max = Math.max(...probs);
                resultDisplay = `<span class="font-mono ${getAgentColor(index)}">max: ${(max * 100).toFixed(1)}%</span>`;
            } else {
                resultDisplay = '<span class="text-gray-500">N/A</span>';
            }

            return `
                <div class="border-b border-gray-700">
                    <div class="p-4 bg-gray-750">
                        <div class="flex justify-between items-center">
                            <div>
                                <span class="font-bold ${getAgentColor(index)}">Agent ${index + 1}</span>
                                <span class="text-gray-400 text-sm ml-2">${modelShort}</span>
                            </div>
                            <div class="text-right">
                                ${resultDisplay}
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

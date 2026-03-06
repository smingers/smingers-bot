#!/usr/bin/env python3
"""
Scraping & Content Extraction Analysis

Aggregates data from tool_usage.json (and research/search_research_plan.json for
planner runs) across all forecasts to show:
- Per-domain success/failure rates
- Extraction method distribution (which backends win)
- Common error types and frequencies
- Scrape efficiency (URLs returned vs extracted vs summarized)
- Question URL scraping success rates (includes iterative planner pre-research)

Usage:
    python scripts/analyze_scraping.py
    python scripts/analyze_scraping.py --json
    python scripts/analyze_scraping.py --data-dir data/
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

DATA_DIR = Path("./data")


def _question_url_queries_from_plan(plan_path: Path) -> list[dict] | None:
    """
    Load question URL scraping data from research/search_research_plan.json
    (phases.pre_research) and normalize to the same shape as
    tool_usage.centralized_research.question_urls.queries.
    """
    try:
        plan = json.loads(plan_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    pre = plan.get("phases", {}).get("pre_research", {})
    urls = pre.get("urls", [])
    if not urls:
        return None
    queries = []
    for u in urls:
        url = u.get("url", "")
        domain = u.get("domain") or (urlparse(url).netloc if url else "unknown")
        if domain.startswith("www."):
            domain = domain[4:]
        success = u.get("success", u.get("scraped", False))
        queries.append(
            {
                "query": url,
                "success": success,
                "num_results": 1 if success else 0,
                "domain": domain,
                "method": u.get("method"),
                "error": u.get("error"),
            }
        )
    return queries


def load_tool_usage_files(data_dir: Path) -> list[dict]:
    """Load all tool_usage.json files from forecast artifact directories.

    For runs that used the iterative planner, question_urls.queries may be
    empty in tool_usage.json. When so, backfill from
    research/search_research_plan.json (phases.pre_research) so planner runs
    are included in question URL scraping stats.
    """
    files = sorted(data_dir.glob("*/tool_usage.json"))
    results = []
    for f in files:
        try:
            data = json.loads(f.read_text())
            data["_source_file"] = str(f)
            forecast_dir = f.parent
            research_plan_path = forecast_dir / "research" / "search_research_plan.json"
            q_urls = data.get("centralized_research", {}).get("question_urls", {})
            queries = q_urls.get("queries", [])
            if not queries and research_plan_path.exists():
                plan_queries = _question_url_queries_from_plan(research_plan_path)
                if plan_queries:
                    if "centralized_research" not in data:
                        data["centralized_research"] = {}
                    if "question_urls" not in data["centralized_research"]:
                        data["centralized_research"]["question_urls"] = {}
                    data["centralized_research"]["question_urls"]["queries"] = plan_queries
                    data["centralized_research"]["question_urls"]["searched"] = True
                    data["centralized_research"]["question_urls"]["num_queries"] = len(plan_queries)
                    data["centralized_research"]["question_urls"]["tools_used"] = [
                        "QuestionURLScrape"
                    ]
            results.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return results


def analyze_google_scraping(all_data: list[dict]) -> dict:
    """Analyze per-URL scrape results from Google search queries."""
    domain_success = Counter()
    domain_fail = Counter()
    domain_errors = defaultdict(Counter)
    method_counts = Counter()
    status_codes = Counter()
    total_urls_returned = 0
    total_urls_extracted = 0
    total_urls_failed = 0
    total_urls_summarized = 0
    queries_with_url_data = 0
    queries_without_url_data = 0
    truncated_count = 0
    content_chars_by_domain = defaultdict(list)
    usage_counts = Counter()

    for data in all_data:
        research = data.get("centralized_research", {})
        for phase_id in ("historical", "current"):
            phase = research.get(phase_id, {})
            for query_info in phase.get("queries", []):
                tool = query_info.get("tool", "")
                if tool not in ("Google", "Google News"):
                    continue

                url_results = query_info.get("url_results")
                if url_results is None:
                    queries_without_url_data += 1
                    continue

                queries_with_url_data += 1
                scrape_stats = query_info.get("scrape_stats", {})
                total_urls_returned += scrape_stats.get("urls_returned", len(url_results))
                total_urls_extracted += scrape_stats.get("urls_extracted", 0)
                total_urls_failed += scrape_stats.get("urls_failed", 0)
                total_urls_summarized += scrape_stats.get("urls_summarized", 0)

                for url_info in url_results:
                    domain = url_info.get("domain", "unknown")
                    # Strip www. prefix for cleaner grouping
                    if domain.startswith("www."):
                        domain = domain[4:]

                    if url_info.get("success"):
                        domain_success[domain] += 1
                        method = url_info.get("method")
                        if method:
                            method_counts[method] += 1
                        chars = url_info.get("content_chars", 0)
                        if chars > 0:
                            content_chars_by_domain[domain].append(chars)
                        if url_info.get("truncated"):
                            truncated_count += 1
                    else:
                        domain_fail[domain] += 1
                        error = url_info.get("error", "Unknown error")
                        domain_errors[domain][error] += 1

                    status = url_info.get("status_code")
                    if status is not None:
                        status_codes[status] += 1

                    usage = url_info.get("usage") or "unknown"
                    usage_counts[usage] += 1

    # Compute per-domain success rates
    all_domains = set(domain_success.keys()) | set(domain_fail.keys())
    domain_stats = []
    for domain in all_domains:
        s = domain_success[domain]
        f = domain_fail[domain]
        total = s + f
        rate = s / total if total > 0 else 0
        domain_stats.append(
            {
                "domain": domain,
                "success": s,
                "fail": f,
                "total": total,
                "success_rate": round(rate, 3),
                "top_errors": dict(domain_errors[domain].most_common(3)),
                "avg_content_chars": (
                    round(
                        sum(content_chars_by_domain[domain]) / len(content_chars_by_domain[domain])
                    )
                    if content_chars_by_domain[domain]
                    else 0
                ),
            }
        )
    domain_stats.sort(key=lambda x: x["total"], reverse=True)

    # Aggregate errors
    all_errors = Counter()
    for domain_errs in domain_errors.values():
        all_errors.update(domain_errs)

    # Domains with most HTTP 403 (and other top error status codes for JSON)
    domains_most_403 = [
        (d, domain_errors[d].get("HTTP 403", 0))
        for d in all_domains
        if domain_errors[d].get("HTTP 403", 0) > 0
    ]
    domains_most_403.sort(key=lambda x: x[1], reverse=True)

    return {
        "queries_with_url_data": queries_with_url_data,
        "queries_without_url_data": queries_without_url_data,
        "totals": {
            "urls_returned": total_urls_returned,
            "urls_extracted": total_urls_extracted,
            "urls_failed": total_urls_failed,
            "urls_summarized": total_urls_summarized,
            "extraction_rate": (
                round(total_urls_extracted / total_urls_returned, 3)
                if total_urls_returned > 0
                else 0
            ),
            "truncated": truncated_count,
        },
        "extraction_methods": dict(method_counts.most_common()),
        "status_codes": dict(status_codes.most_common()),
        "top_errors": dict(all_errors.most_common(10)),
        "domains": domain_stats,
        "domains_most_403": [{"domain": d, "count": c} for d, c in domains_most_403],
        "usage_breakdown": dict(usage_counts.most_common()),
    }


def analyze_question_url_scraping(all_data: list[dict]) -> dict:
    """Analyze question URL scraping results."""
    domain_success = Counter()
    domain_fail = Counter()
    domain_errors = defaultdict(Counter)
    method_counts = Counter()
    total_found = 0
    total_scraped = 0
    total_summarized = 0
    forecasts_with_urls = 0

    for data in all_data:
        research = data.get("centralized_research", {})
        q_urls = research.get("question_urls", {})

        queries = q_urls.get("queries", [])
        if not queries:
            continue

        forecasts_with_urls += 1
        total_found += len(queries)
        total_scraped += sum(1 for q in queries if q.get("success"))
        total_summarized += sum(q.get("num_results", 0) for q in queries)

        for query_info in queries:
            url = query_info.get("query", "")
            domain = query_info.get("domain")
            if not domain:
                domain = urlparse(url).netloc
            if domain.startswith("www."):
                domain = domain[4:]

            method = query_info.get("method")
            if method:
                method_counts[method] += 1

            if query_info.get("success"):
                domain_success[domain] += 1
            else:
                domain_fail[domain] += 1
                error = query_info.get("error", "Unknown")
                domain_errors[domain][error] += 1

    all_domains = set(domain_success.keys()) | set(domain_fail.keys())
    domain_stats = []
    for domain in all_domains:
        s = domain_success[domain]
        f = domain_fail[domain]
        total = s + f
        domain_stats.append(
            {
                "domain": domain,
                "success": s,
                "fail": f,
                "total": total,
                "success_rate": round(s / total, 3) if total > 0 else 0,
                "top_errors": dict(domain_errors[domain].most_common(3)),
            }
        )
    domain_stats.sort(key=lambda x: x["total"], reverse=True)

    all_domains_qu = set(domain_success.keys()) | set(domain_fail.keys())
    domains_most_403 = [
        (d, domain_errors[d].get("HTTP 403", 0))
        for d in all_domains_qu
        if domain_errors[d].get("HTTP 403", 0) > 0
    ]
    domains_most_403.sort(key=lambda x: x[1], reverse=True)

    return {
        "forecasts_with_urls": forecasts_with_urls,
        "totals": {
            "urls_found": total_found,
            "urls_scraped": total_scraped,
            "urls_summarized": total_summarized,
            "scrape_rate": round(total_scraped / total_found, 3) if total_found > 0 else 0,
        },
        "extraction_methods": dict(method_counts.most_common()),
        "domains": domain_stats,
        "domains_most_403": [{"domain": d, "count": c} for d, c in domains_most_403],
    }


def print_report(google: dict, question_urls: dict, total_files: int) -> None:
    """Print a human-readable report to stdout."""
    print(f"=== Scraping Analysis ({total_files} forecasts) ===\n")

    # Google search scraping
    print("--- Google Search Scraping ---")
    if google["queries_with_url_data"] > 0:
        t = google["totals"]
        print(f"Queries with per-URL data: {google['queries_with_url_data']}")
        print(f"URLs returned: {t['urls_returned']}")
        print(f"URLs extracted: {t['urls_extracted']} ({t['extraction_rate']:.1%})")
        print(f"URLs failed: {t['urls_failed']}")
        print(f"URLs summarized: {t['urls_summarized']}")
        print(f"Truncated: {t['truncated']}")

        if google["extraction_methods"]:
            print("\nExtraction methods:")
            for method, count in google["extraction_methods"].items():
                print(f"  {method}: {count}")

        if google["status_codes"]:
            print("\nHTTP status codes:")
            for code, count in google["status_codes"].items():
                print(f"  {code}: {count}")

        if google["top_errors"]:
            print("\nTop errors:")
            for error, count in google["top_errors"].items():
                print(f"  {error}: {count}")

        if google.get("usage_breakdown"):
            print("\nURL usage (extracted vs dropped vs failed):")
            for usage, count in google["usage_breakdown"].items():
                print(f"  {usage}: {count}")

        if google.get("domains_most_403"):
            print("\nDomains with most HTTP 403 (Google search URLs):")
            for entry in google["domains_most_403"][:25]:
                print(f"  {entry['domain']:40s}  {entry['count']:4d} 403s")

        # Top domains by volume
        print("\nTop domains (by volume):")
        for d in google["domains"][:20]:
            rate_pct = f"{d['success_rate']:.0%}"
            print(
                f"  {d['domain']:40s}  "
                f"{d['success']:3d}/{d['total']:3d} ({rate_pct:>4s})  "
                f"avg {d['avg_content_chars']:,} chars"
            )

        # Worst domains (by failure rate, min 3 attempts)
        worst = [d for d in google["domains"] if d["total"] >= 3 and d["success_rate"] < 0.5]
        if worst:
            worst.sort(key=lambda x: x["success_rate"])
            print("\nProblematic domains (>50% failure, min 3 attempts):")
            for d in worst[:10]:
                rate_pct = f"{d['success_rate']:.0%}"
                errors = ", ".join(f"{e}: {c}" for e, c in list(d["top_errors"].items())[:2])
                print(f"  {d['domain']:40s}  {rate_pct:>4s} success  ({errors})")
    else:
        print(
            f"No per-URL data available yet ({google['queries_without_url_data']} queries "
            f"from before this tracking was added)"
        )

    # Question URL scraping
    print("\n--- Question URL Scraping ---")
    if question_urls["forecasts_with_urls"] > 0:
        t = question_urls["totals"]
        print(f"Forecasts with question URLs: {question_urls['forecasts_with_urls']}")
        print(f"URLs found: {t['urls_found']}")
        print(f"URLs scraped: {t['urls_scraped']} ({t['scrape_rate']:.1%})")
        print(f"URLs summarized: {t['urls_summarized']}")

        if question_urls["extraction_methods"]:
            print("\nExtraction methods:")
            for method, count in question_urls["extraction_methods"].items():
                print(f"  {method}: {count}")

        if question_urls["domains"]:
            print("\nDomains:")
            for d in question_urls["domains"][:15]:
                rate_pct = f"{d['success_rate']:.0%}"
                print(f"  {d['domain']:40s}  {d['success']:2d}/{d['total']:2d} ({rate_pct:>4s})")

        if question_urls.get("domains_most_403"):
            print("\nDomains with most HTTP 403 (question URLs):")
            for entry in question_urls["domains_most_403"][:25]:
                print(f"  {entry['domain']:40s}  {entry['count']:4d} 403s")
    else:
        print("No question URL data found")


def main():
    parser = argparse.ArgumentParser(description="Analyze scraping performance across forecasts")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR, help="Data directory")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    all_data = load_tool_usage_files(args.data_dir)
    if not all_data:
        print(f"No tool_usage.json files found in {args.data_dir}", file=sys.stderr)
        sys.exit(1)

    google = analyze_google_scraping(all_data)
    question_urls = analyze_question_url_scraping(all_data)

    if args.json:
        output = {
            "total_forecasts": len(all_data),
            "google_scraping": google,
            "question_url_scraping": question_urls,
        }
        print(json.dumps(output, indent=2))
    else:
        print_report(google, question_urls, len(all_data))


if __name__ == "__main__":
    main()

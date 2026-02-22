#!/usr/bin/env python3
"""
Scraping & Content Extraction Analysis

Aggregates data from tool_usage.json files across all forecasts to show:
- Per-domain success/failure rates
- Extraction method distribution (which backends win)
- Common error types and frequencies
- Scrape efficiency (URLs returned vs extracted vs summarized)
- Question URL scraping success rates

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

DATA_DIR = Path("./data")


def load_tool_usage_files(data_dir: Path) -> list[dict]:
    """Load all tool_usage.json files from forecast artifact directories."""
    files = sorted(data_dir.glob("*/tool_usage.json"))
    results = []
    for f in files:
        try:
            data = json.loads(f.read_text())
            data["_source_file"] = str(f)
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
                from urllib.parse import urlparse

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

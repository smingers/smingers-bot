#!/usr/bin/env python3
"""
Compare distribution widths: smingers-bot vs GreeneiBot2 vs ManticAI.

Uses tracking file data (browser-scraped, verified) for my forecasts,
and Metaculus comments API data for the other two bots.

Core question: Are my distributions narrower/more confident than top bots?
"""

import json

# Load my data from tracking files (verified via browser scraping)
my_data = {}
for fname in [
    "data/tracking/32916.json",
    "data/tracking/minibench.json",
    "data/tracking/other.json",
]:
    try:
        with open(fname) as f:
            data = json.load(f)
        for fc in data["forecasts"]:
            if fc["question_type"] in ("numeric", "discrete") and fc.get("comparison"):
                c = fc["comparison"]
                if c.get("my_median") is not None:
                    my_data[fc["question_id"]] = {
                        "title": fc["question_title"],
                        "p25": c.get("my_lower_quartile"),
                        "p50": c.get("my_median"),
                        "p75": c.get("my_upper_quartile"),
                        "my_iqr": c.get("my_iqr"),
                        "community_iqr": c.get("community_iqr"),
                        "uncertainty_ratio": c.get("uncertainty_ratio"),
                    }
    except Exception:
        pass

# Manual entries for discrete questions missing my_median in tracking files
# (verified by scraping Metaculus question pages on 2026-02-23)
for qid, entry in {
    41894: {"title": 'Number of Oscars "Sinners" film will win?', "p25": 5, "p50": 6, "p75": 6},
    41895: {"title": "Total runs in knockout stage of 2026 WBC?", "p25": 71, "p50": 75, "p75": 79},
    41841: {
        "title": "What will U.S. score on 2025 Corruption Perceptions Index?",
        "p25": 62,
        "p50": 62,
        "p75": 63,
    },
}.items():
    if qid not in my_data:
        my_data[qid] = {
            "title": entry["title"],
            "p25": entry["p25"],
            "p50": entry["p50"],
            "p75": entry["p75"],
            "my_iqr": entry["p75"] - entry["p25"],
            "community_iqr": None,
            "uncertainty_ratio": None,
        }

# GreeneiBot2 percentiles (scraped from Metaculus comments API)
GREENEI = {
    41569: {"p25": 6669, "p50": 6965, "p75": 7261},
    41759: {"p25": 10, "p50": 10.5, "p75": 10.5},
    41760: {"p25": 431.45, "p50": 431.95, "p75": 432.55},
    41838: {"p25": 29.6e9, "p50": 30.3e9, "p75": 31.6e9},
    41840: {"p25": 4.05, "p50": 4.28, "p75": 4.52},
    41843: {"p25": 4.88, "p50": 8.75, "p75": 12.63},
    41845: {"p25": 4.45, "p50": 4.65, "p75": 4.85},
    41852: {"p25": 1800000, "p50": 1930000, "p75": 2050000},
    41854: {"p25": 326.5, "p50": 331, "p75": 335.5},
    41859: {"p25": 2.75, "p50": 3.5, "p75": 5},
    41896: {"p25": 10.5, "p50": 11.5, "p75": 13},
    41899: {"p25": 8500, "p50": 10000, "p75": 12000},
    41905: {"p25": 3.8e9, "p50": 4.35e9, "p75": 4.9e9},
    41907: {"p25": 340000, "p50": 365000, "p75": 395000},
    41909: {"p25": 6.2e9, "p50": 6.9e9, "p75": 7.6e9},
    41935: {"p25": 7, "p50": 10, "p75": 15},
    42029: {"p25": 82.13, "p50": 89.5, "p75": 97.13},
    42036: {"p25": 3.5, "p50": 3.75, "p75": 4},
    42037: {"p25": 2.85, "p50": 2.95, "p75": 3.05},
    42038: {"p25": 86.25, "p50": 87.5, "p75": 88.75},
    42039: {"p25": 3.5, "p50": 3.75, "p75": 4},
    42040: {"p25": 86.25, "p50": 87.5, "p75": 88.75},
    42042: {"p25": 4.25, "p50": 4.4, "p75": 4.55},
    42043: {"p25": 2.85, "p50": 2.95, "p75": 3.05},
    42047: {"p25": 2.9, "p50": 3.03, "p75": 3.15},
    42049: {"p25": 1250, "p50": 2000, "p75": 3100},
    42051: {"p25": 3.5, "p50": 3.63, "p75": 3.75},
    42097: {"p25": 15600000, "p50": 16550000, "p75": 17175000},
    42098: {"p25": 16020000, "p50": 16425000, "p75": 16815000},
    42099: {"p25": 16150000, "p50": 16800000, "p75": 17500000},
    42100: {"p25": 27, "p50": 30, "p75": 33},
    42105: {"p25": 30, "p50": 38, "p75": 46},
    42107: {"p25": 55, "p50": 58.5, "p75": 61},
    42109: {"p25": 55, "p50": 67, "p75": 79},
    42114: {"p25": 50, "p50": 62.5, "p75": 75},
    # 6 new questions added 2026-02-23 (from Metaculus comments API)
    42096: {"p25": 31, "p50": 37, "p75": 43},
    42077: {"p25": 9, "p50": 9, "p75": 11},
    42050: {"p25": 0.0007, "p50": 0.0065, "p75": 0.035},
    41895: {"p25": 56, "p50": 64, "p75": 73},
    41894: {"p25": 3, "p50": 4, "p75": 6},
    41841: {"p25": 59.3, "p50": 61.8, "p75": 64.3},
}

# ManticAI percentiles (computed from continuous_cdf via Metaculus comments API)
MANTIC = {
    41569: {"p25": 6812.47, "p50": 7020.95, "p75": 7213.75},
    41759: {"p25": 9.85, "p50": 10.35, "p75": 10.78},
    41760: {"p25": 430.51, "p50": 431.66, "p75": 432.47},
    41838: {"p25": 30.97e9, "p50": 31.41e9, "p75": 31.97e9},
    41840: {"p25": 4.16, "p50": 4.36, "p75": 4.60},
    41843: {"p25": 4.38, "p50": 8.74, "p75": 13.28},
    41845: {"p25": 4.47, "p50": 4.67, "p75": 4.90},
    41852: {"p25": 1722082, "p50": 1861116, "p75": 2053826},
    41854: {"p25": 327.93, "p50": 332.31, "p75": 336.32},
    41859: {"p25": 2.43, "p50": 3.00, "p75": 3.67},
    41896: {"p25": 10.33, "p50": 11.53, "p75": 13.38},
    41899: {"p25": 7887, "p50": 9621, "p75": 12014},
    41905: {"p25": 3.78e9, "p50": 4.19e9, "p75": 4.68e9},
    41907: {"p25": 346619, "p50": 376070, "p75": 407966},
    41909: {"p25": 6.54e9, "p50": 7.17e9, "p75": 7.84e9},
    41935: {"p25": 7.11, "p50": 10.46, "p75": 16.02},
    42029: {"p25": 83.04, "p50": 92.07, "p75": 100.96},
    42037: {"p25": 2.82, "p50": 2.96, "p75": 3.14},
    42038: {"p25": 86.23, "p50": 87.92, "p75": 89.68},
    42039: {"p25": 3.35, "p50": 3.71, "p75": 4.08},
    42040: {"p25": 85.50, "p50": 87.92, "p75": 90.10},
    42042: {"p25": 4.24, "p50": 4.42, "p75": 4.62},
    42043: {"p25": 2.80, "p50": 2.98, "p75": 3.19},
    42047: {"p25": 2.81, "p50": 3.01, "p75": 3.25},
    42049: {"p25": 1217, "p50": 2046, "p75": 3398},
    42097: {"p25": 15483019, "p50": 16069752, "p75": 16614393},
    42098: {"p25": 15682555, "p50": 16254979, "p75": 16841614},
    42099: {"p25": 15113637, "p50": 15878020, "p75": 16598975},
    42105: {"p25": 27.57, "p50": 36.87, "p75": 49.10},
    42107: {"p25": 55.98, "p50": 59.28, "p75": 62.44},
    42109: {"p25": 51.90, "p50": 63.52, "p75": 76.22},
    # 6 new questions added 2026-02-23 (from continuous_cdf via Metaculus comments API)
    42096: {"p25": 28.61, "p50": 33.32, "p75": 38.74},
    42077: {"p25": 9.42, "p50": 11.09, "p75": 13.32},
    42050: {"p25": -0.14, "p50": 0.23, "p75": 0.85},
    41895: {"p25": 62.27, "p50": 73.44, "p75": 84.31},
    41894: {"p25": 3.52, "p50": 4.82, "p75": 6.27},
    41841: {"p25": 61.89, "p50": 63.17, "p75": 64.41},
}


def fmt(v):
    if v is None:
        return "-"
    if abs(v) >= 1e9:
        return f"${v / 1e9:.1f}B"
    if abs(v) >= 1e6:
        return f"{v / 1e6:.2f}M"
    if abs(v) >= 10000:
        return f"{v:,.0f}"
    return f"{v:.2f}"


# Find questions where all three have data
common_qids = sorted(set(my_data.keys()) & set(GREENEI.keys()) & set(MANTIC.keys()))

print()
print("DISTRIBUTION WIDTH COMPARISON: smingers-bot vs GreeneiBot2 vs ManticAI")
print("=" * 120)
print(f"Questions with all 3 bots: {len(common_qids)}")
print()
print("IQR = p75 - p25 (interquartile range). Ratio = my IQR / avg(Greenei, Mantic).")
print("Ratio < 1 = I'm narrower/more confident. Ratio > 1 = I'm wider/less confident.")
print()
print(
    f"{'Q#':<6} {'Question':<50} {'My IQR':>10} {'Greenei':>10} {'Mantic':>10} {'Ratio':>7} {'':>2}"
)
print("-" * 120)

ratios = []
for qid in common_qids:
    me = my_data[qid]
    g = GREENEI[qid]
    m = MANTIC[qid]

    my_iqr = me["p75"] - me["p25"] if me["p75"] is not None and me["p25"] is not None else None
    g_iqr = g["p75"] - g["p25"]
    m_iqr = m["p75"] - m["p25"]

    if my_iqr is None:
        continue

    avg_other = (g_iqr + m_iqr) / 2
    ratio = my_iqr / avg_other if avg_other > 0 else None

    if ratio is not None:
        ratios.append(
            {"qid": qid, "ratio": ratio, "my_iqr": my_iqr, "g_iqr": g_iqr, "m_iqr": m_iqr}
        )

    if ratio is not None:
        if ratio < 0.5:
            tag = "<<"
        elif ratio < 0.8:
            tag = "<"
        elif ratio > 2.0:
            tag = ">>"
        elif ratio > 1.25:
            tag = ">"
        else:
            tag = "~"
    else:
        tag = ""

    title = me["title"][:48]
    print(
        f"{qid:<6} {title:<50} {fmt(my_iqr):>10} {fmt(g_iqr):>10} {fmt(m_iqr):>10} {ratio:>6.2f}x {tag:>2}"
    )

# Summary
print()
print("=" * 120)
print("SUMMARY")
print()
sorted_ratios = sorted(ratios, key=lambda r: r["ratio"])
vals = [r["ratio"] for r in sorted_ratios]
median_r = vals[len(vals) // 2]
mean_r = sum(vals) / len(vals)
narrower = sum(1 for v in vals if v < 1.0)
much_narrower = sum(1 for v in vals if v < 0.5)
much_wider = sum(1 for v in vals if v > 2.0)

print(f"  Median IQR ratio (me / avg others): {median_r:.2f}x")
print(f"  Mean IQR ratio:                     {mean_r:.2f}x")
print(f"  Narrower than both bots avg: {narrower}/{len(vals)} ({narrower / len(vals) * 100:.0f}%)")
print(f"  Much narrower (<0.5x):       {much_narrower}/{len(vals)}")
print(f"  Much wider (>2.0x):          {much_wider}/{len(vals)}")

# Comparison to community (from tracking data)
print()
print("  For context, my IQR vs full community (100+ forecasters):")
comm_ratios = [
    my_data[r["qid"]]["uncertainty_ratio"]
    for r in sorted_ratios
    if my_data[r["qid"]].get("uncertainty_ratio") is not None
]
if comm_ratios:
    med_comm = sorted(comm_ratios)[len(comm_ratios) // 2]
    mean_comm = sum(comm_ratios) / len(comm_ratios)
    narrower_comm = sum(1 for v in comm_ratios if v < 1.0)
    print(f"  Median uncertainty ratio vs community: {med_comm:.2f}x")
    print(
        f"  Narrower than community: {narrower_comm}/{len(comm_ratios)} ({narrower_comm / len(comm_ratios) * 100:.0f}%)"
    )

print()
print()
print("SORTED BY RATIO (narrowest to widest relative to other bots)")
print("-" * 90)
print(f"{'Q#':<6} {'Question':<55} {'Ratio':>7} {'Link'}")
print("-" * 90)
for r in sorted_ratios:
    title = my_data[r["qid"]]["title"][:53]
    url = f"https://www.metaculus.com/questions/{r['qid']}/"
    print(f"{r['qid']:<6} {title:<55} {r['ratio']:>6.2f}x  {url}")

#!/usr/bin/env python3
"""Compare numeric forecasts across three bots."""

# My data from tracking files
my_raw = [
    {
        "qid": 41569,
        "title": "S&P 500 closing value (March 13, 2026)",
        "p25": 6733.62,
        "p50": 6988.83,
        "p75": 7231.11,
    },
    {
        "qid": 41759,
        "title": "Pakistan policy rate (May 1, 2026 %)",
        "p25": 9.75,
        "p50": 10.07,
        "p75": 10.50,
    },
    {
        "qid": 41760,
        "title": "CO2 ppm Mauna Loa (April 2026)",
        "p25": 431.35,
        "p50": 432.07,
        "p75": 432.74,
    },
    {
        "qid": 41838,
        "title": "Alphabet Q4 2025 EMEA revenues ($)",
        "p25": 30.80e9,
        "p50": 32.02e9,
        "p75": 33.23e9,
    },
    {
        "qid": 41840,
        "title": "Australia unemployment (Feb 2026 %)",
        "p25": 4.03,
        "p50": 4.17,
        "p75": 4.36,
    },
    {
        "qid": 41843,
        "title": "Ground transport CO2 change 2020-30 (%)",
        "p25": 3.01,
        "p50": 9.60,
        "p75": 16.06,
    },
    {
        "qid": 41852,
        "title": "Tesla 2025 production (vehicles)",
        "p25": 5125000,
        "p50": 5500000,
        "p75": 5875000,
    },
    {
        "qid": 41854,
        "title": "Case-Shiller Home Price Index",
        "p25": 320.80,
        "p50": 325.00,
        "p75": 329.20,
    },
    {
        "qid": 41859,
        "title": "UK inflation if Truss wins (%)",
        "p25": 6.46,
        "p50": 7.50,
        "p75": 8.54,
    },
    {"qid": 41896, "title": "Egypt annual inflation (%)", "p25": 10.07, "p50": 11.15, "p75": 12.44},
    {"qid": 41899, "title": "Rivian Q1 2026 deliveries", "p25": 9310, "p50": 10471, "p75": 11912},
    {
        "qid": 41905,
        "title": "Zepbound Q1 2026 revenue ($)",
        "p25": 3.67e9,
        "p50": 4.05e9,
        "p75": 4.68e9,
    },
    {
        "qid": 41907,
        "title": "Tesla Q1 2026 deliveries",
        "p25": 329417,
        "p50": 356757,
        "p75": 397275,
    },
    {
        "qid": 41909,
        "title": "Mounjaro Q1 2026 revenue ($)",
        "p25": 7.07e9,
        "p50": 7.88e9,
        "p75": 8.90e9,
    },
    {"qid": 41935, "title": "Rotten Tomatoes - Melania", "p25": 10.00, "p50": 11.74, "p75": 15.22},
    {
        "qid": 42029,
        "title": "Highest silver price Apr 2026 ($/oz)",
        "p25": 72.11,
        "p50": 89.05,
        "p75": 106.89,
    },
    {
        "qid": 42037,
        "title": "US gasoline price Feb 2026 ($/gal)",
        "p25": 2.90,
        "p50": 2.98,
        "p75": 3.10,
    },
    {
        "qid": 42038,
        "title": "Ifo Index Germany (Feb 2026)",
        "p25": 83.75,
        "p50": 85.00,
        "p75": 86.25,
    },
    {
        "qid": 42039,
        "title": "Fed Funds upper bound (Mar 31 %)",
        "p25": 3.21,
        "p50": 3.50,
        "p75": 3.79,
    },
    {
        "qid": 42040,
        "title": "Ifo Index Germany (Mar 2026)",
        "p25": 81.04,
        "p50": 82.50,
        "p75": 83.95,
    },
    {"qid": 42042, "title": "US unemployment (Mar 2026 %)", "p25": 4.59, "p50": 5.00, "p75": 5.42},
    {
        "qid": 42043,
        "title": "US gasoline price Mar 2026 ($/gal)",
        "p25": 4.25,
        "p50": 4.50,
        "p75": 4.75,
    },
    {
        "qid": 42047,
        "title": "US gasoline price Apr 2026 ($/gal)",
        "p25": 4.25,
        "p50": 4.50,
        "p75": 4.75,
    },
    {
        "qid": 42049,
        "title": "CDC measles cases (cumul. April)",
        "p25": 4902,
        "p50": 5294,
        "p75": 5686,
    },
    {
        "qid": 42097,
        "title": "TSA passengers (Feb 9-15, 2026)",
        "p25": 14.29e6,
        "p50": 14.50e6,
        "p75": 14.71e6,
    },
    {
        "qid": 42098,
        "title": "TSA passengers (Feb 16-22, 2026)",
        "p25": 14.29e6,
        "p50": 14.50e6,
        "p75": 14.71e6,
    },
    {
        "qid": 42099,
        "title": "TSA passengers (Feb 23-Mar 1)",
        "p25": 14.29e6,
        "p50": 14.50e6,
        "p75": 14.71e6,
    },
    {
        "qid": 42105,
        "title": "Airbus deliveries (Feb 2026)",
        "p25": 68.77,
        "p50": 75.01,
        "p75": 81.26,
    },
    {
        "qid": 42107,
        "title": "Bavaria election turnout (%)",
        "p25": 50.21,
        "p50": 52.50,
        "p75": 54.79,
    },
]

greenei = {
    41569: {"p25": 6669, "p50": 6965, "p75": 7261},
    41759: {"p25": 10, "p50": 10.5, "p75": 10.5},
    41760: {"p25": 431.45, "p50": 431.95, "p75": 432.55},
    41838: {"p25": 29.6e9, "p50": 30.3e9, "p75": 31.6e9},
    41840: {"p25": 4.05, "p50": 4.28, "p75": 4.52},
    41843: {"p25": 4.88, "p50": 8.75, "p75": 12.63},
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
    42037: {"p25": 2.85, "p50": 2.95, "p75": 3.05},
    42038: {"p25": 86.25, "p50": 87.5, "p75": 88.75},
    42039: {"p25": 3.5, "p50": 3.75, "p75": 4},
    42040: {"p25": 86.25, "p50": 87.5, "p75": 88.75},
    42042: {"p25": 4.25, "p50": 4.4, "p75": 4.55},
    42043: {"p25": 2.85, "p50": 2.95, "p75": 3.05},
    42047: {"p25": 2.9, "p50": 3.03, "p75": 3.15},
    42049: {"p25": 1250, "p50": 2000, "p75": 3100},
    42097: {"p25": 15.6e6, "p50": 16.55e6, "p75": 17.175e6},
    42098: {"p25": 16.02e6, "p50": 16.425e6, "p75": 16.815e6},
    42099: {"p25": 16.15e6, "p50": 16.8e6, "p75": 17.5e6},
    42105: {"p25": 30, "p50": 38, "p75": 46},
    42107: {"p25": 55, "p50": 58.5, "p75": 61},
}

mantic = {
    41569: {"p25": 6812.47, "p50": 7020.95, "p75": 7213.75},
    41759: {"p25": 9.85, "p50": 10.35, "p75": 10.78},
    41760: {"p25": 430.51, "p50": 431.66, "p75": 432.47},
    41838: {"p25": 30.97e9, "p50": 31.41e9, "p75": 31.97e9},
    41840: {"p25": 4.16, "p50": 4.36, "p75": 4.60},
    41843: {"p25": 4.38, "p50": 8.74, "p75": 13.28},
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
    42097: {"p25": 15.48e6, "p50": 16.07e6, "p75": 16.61e6},
    42098: {"p25": 15.68e6, "p50": 16.25e6, "p75": 16.84e6},
    42099: {"p25": 15.11e6, "p50": 15.88e6, "p75": 16.60e6},
    42105: {"p25": 27.57, "p50": 36.87, "p75": 49.10},
    42107: {"p25": 55.98, "p50": 59.28, "p75": 62.44},
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


def fmt_range(d):
    if d is None:
        return "-"
    return f"{fmt(d['p25'])} / {fmt(d['p50'])} / {fmt(d['p75'])}"


print()
print("NUMERIC FORECAST COMPARISON: smingers-bot vs GreeneiBot2 vs ManticAI")
print("=" * 100)
print(f"{'Questions compared:':<25} {len(my_raw)}")
print()

# Print median comparison
print("MEDIAN (p50) COMPARISON")
print("-" * 100)
print(f"{'Q#':<6} {'Question':<40} {'Me':>12} {'GreeneiBot2':>12} {'ManticAI':>12}  Notes")
print("-" * 100)

notable_diffs = []

for q in my_raw:
    qid = q["qid"]
    g = greenei.get(qid)
    m = mantic.get(qid)

    my_p50 = q["p50"]
    g_p50 = g["p50"] if g else None
    m_p50 = m["p50"] if m else None

    notes = ""
    # Check for large divergences (my median vs others)
    if g_p50 and my_p50:
        if my_p50 != 0:
            pct_diff_g = abs(my_p50 - g_p50) / abs(my_p50)
            if pct_diff_g > 0.5:
                notes += " !!G"
                notable_diffs.append((qid, q["title"], my_p50, g_p50, m_p50, "vs GreeneiBot2"))

    if m_p50 and my_p50:
        if my_p50 != 0:
            pct_diff_m = abs(my_p50 - m_p50) / abs(my_p50)
            if pct_diff_m > 0.5:
                notes += " !!M"
                if not any(d[0] == qid for d in notable_diffs):
                    notable_diffs.append((qid, q["title"], my_p50, g_p50, m_p50, "vs ManticAI"))

    print(
        f"{qid:<6} {q['title'][:38]:<40} {fmt(my_p50):>12} {fmt(g_p50) if g_p50 else '-':>12} {fmt(m_p50) if m_p50 else '-':>12}  {notes}"
    )


print()
print()
print("UNCERTAINTY COMPARISON (IQR = p75 - p25)")
print("-" * 100)
print(f"{'Q#':<6} {'Question':<40} {'My IQR':>12} {'Greenei IQR':>12} {'Mantic IQR':>12}  Relative")
print("-" * 100)

narrower_count = 0
wider_count = 0

for q in my_raw:
    qid = q["qid"]
    g = greenei.get(qid)
    m = mantic.get(qid)

    my_iqr = q["p75"] - q["p25"]
    g_iqr = g["p75"] - g["p25"] if g else None
    m_iqr = m["p75"] - m["p25"] if m else None

    # Compare my IQR to average of others
    others = [x for x in [g_iqr, m_iqr] if x is not None]
    avg_other_iqr = sum(others) / len(others) if others else None

    rel = ""
    if avg_other_iqr and avg_other_iqr > 0:
        ratio = my_iqr / avg_other_iqr
        if ratio < 0.5:
            rel = f"MUCH NARROWER ({ratio:.1f}x)"
            narrower_count += 1
        elif ratio < 0.8:
            rel = f"narrower ({ratio:.1f}x)"
            narrower_count += 1
        elif ratio > 2.0:
            rel = f"MUCH WIDER ({ratio:.1f}x)"
            wider_count += 1
        elif ratio > 1.25:
            rel = f"wider ({ratio:.1f}x)"
            wider_count += 1
        else:
            rel = f"similar ({ratio:.1f}x)"

    print(
        f"{qid:<6} {q['title'][:38]:<40} {fmt(my_iqr):>12} {fmt(g_iqr) if g_iqr else '-':>12} {fmt(m_iqr) if m_iqr else '-':>12}  {rel}"
    )

print()
print(f"My distribution is NARROWER than others: {narrower_count}/{len(my_raw)} questions")
print(f"My distribution is WIDER than others:    {wider_count}/{len(my_raw)} questions")

print()
print()
print("BIGGEST MEDIAN DISAGREEMENTS (>50% difference from my forecast)")
print("-" * 100)
if notable_diffs:
    for qid, title, my_v, g_v, m_v, _note in notable_diffs:
        print(f"  Q{qid}: {title[:50]}")
        print(
            f"    Me: {fmt(my_v)},  GreeneiBot2: {fmt(g_v) if g_v else '-'},  ManticAI: {fmt(m_v) if m_v else '-'}"
        )
        if g_v and my_v:
            print(f"    Diff vs Greenei: {((g_v - my_v) / my_v * 100):+.1f}%")
        if m_v and my_v:
            print(f"    Diff vs Mantic:  {((m_v - my_v) / my_v * 100):+.1f}%")
        print()
else:
    print("  No major disagreements found.")

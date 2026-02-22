# PR #59 Review: Add conditional base rates, percentile ranks, and 5-day return to stock return tool

**Commit:** 7b0882d
**Branch:** yfinance-enhance

## Summary

This PR adds three features to the stock return tool and cleans up the content extraction / search pipeline:

1. **5-day trailing return** — new `recent_return_5d` field in `StockReturnData`
2. **Historical percentile ranks** for trailing returns (5d, 1m, 3m)
3. **Conditional base rates** — P(positive N-day return) filtered by momentum, 52-week range, prior 5-day return, and volatility regime
4. **Cleanup** — removes `GoogleScrapeResult`, `_make_result`, per-URL tracking metadata, extraction method tracking, and `scripts/analyze_scraping.py`

All 44 stock_return tests pass. All 86 search/fred/yfinance tests pass (2 skipped).

---

## Feedback

### src/bot/stock_return.py

#### 1. Volatility loop is not vectorized (line 310-313)

The comment on line 307 says "Vectorized" but this is a Python `for` loop over every valid window index. With 10 years of data (~2,515 indices), this iterates ~2,485 times doing per-window numpy operations. The other conditionals (momentum, 52-week range, mean reversion) are properly vectorized. This loop is the performance bottleneck of the new code.

A vectorized approach using stride tricks (similar to what the 52-week range section does) would be:

```python
if len(closes) >= 32:
    daily_ret = np.diff(closes) / closes[:-1]
    # Build strided view of 30-day return windows
    shape = (len(daily_ret) - 29, 30)
    strides = (daily_ret.strides[0], daily_ret.strides[0])
    windowed_dr = np.lib.stride_tricks.as_strided(daily_ret, shape=shape, strides=strides)
    all_vols = np.std(windowed_dr, axis=1) * np.sqrt(252) * 100
    # all_vols[j] is the vol for the window ending at index j+30
    # Map back to window start indices
    for idx in vi:
        if idx - 30 >= 0 and (idx - 30) < len(all_vols):
            window_vols[idx] = all_vols[idx - 30]
```

Or even simpler with a single mapping step. Not blocking, but worth a follow-up.

#### 2. Overlapping return windows may overstate conditional sample sizes

The percentile rank computation and the conditional base rates both use overlapping windows (stride 1). For example, `all_5d = (closes[5:] - closes[:-5]) / closes[:-5]` produces ~2,510 overlapping 5-day return windows from 10 years of data. The conditional rates report `N=1298` etc., but these are highly autocorrelated overlapping windows, not independent samples.

This isn't necessarily wrong — it's consistent with how the unconditional base rate is computed — but the `sample_size` field could mislead the LLM forecasters into thinking there are more independent observations than there actually are. Consider either:
- Adding a note in the formatted output like "(overlapping windows)"
- Or computing the effective sample size (~N/trading_days for non-overlapping independence)

#### 3. `_compute_conditional_rates` return type annotation says `list[dict]` but returns `None`

Line 339: `return rates if rates else None` — the return type annotation is `list[dict]` but this can return `None`. Should be `list[dict] | None`.

#### 4. `datetime.UTC` import

Line 16: Changed from `from datetime import datetime, timezone` to `from datetime import UTC, datetime`. `datetime.UTC` was added in Python 3.11. This is fine given the project uses 3.11+, but worth noting if there's any plan to support 3.10.

#### 5. Minor: `has_recent` check includes `recent_return_5d` but old code didn't

Line 621-625: The `has_recent` boolean now also checks `recent_return_5d`, which is correct — just confirming this is intentional since it changes when the "RECENT CONTEXT" section appears.

### src/bot/content_extractor.py

#### 6. `_make_result` removal — clean but loses diagnostic information

The removal of `_make_result` and inline dict construction is cleaner. However, the result dicts no longer include `status_code`, `method`, `content_chars`, or `truncated` fields. These were useful diagnostics (the deleted `analyze_scraping.py` consumed them). If you ever need to debug extraction issues, you'll need to re-add these.

The `extract()` method signature change from returning `tuple[str | None, str | None]` to `str | None` is a good simplification.

#### 7. Repeated `urlparse(url).netloc` calls

In `_fetch_url` (and `_fetch_with_bright_data`), `urlparse(url).netloc` is called multiple times in each error path instead of once at the top. The old code assigned `domain = urlparse(url).netloc` once. Consider restoring the single assignment for clarity:

```python
domain = urlparse(url).netloc
```

This is minor but the function now has 5+ places that repeat this parsing.

#### 8. Lost `httpx.HTTPStatusError` specific handling in `_fetch_url`

The old code caught `httpx.HTTPStatusError` separately and logged the HTTP status code in the error. The new code collapses this into the generic `Exception` handler, so HTTP 403/429/etc. errors will just show the exception string rather than the clean `HTTP 403` format. Consider keeping the specific handler.

### src/bot/search.py

#### 9. `GoogleScrapeResult` removal — clean simplification

The removal of `GoogleScrapeResult` and the per-URL tracking in `_process_queries` is a reasonable simplification. The Google/Google News branch in the `_process_queries` result handling loop was removed since `google_search_and_scrape` now returns a plain string, which falls through to the `else` branch. This works correctly.

#### 10. Removal of `url_results` and `scrape_stats` from metadata

The `metadata["queries"][i]` entries no longer get `url_results` or `scrape_stats`. This data was consumed by the now-deleted `analyze_scraping.py` and by `base_forecaster.py`'s tool_usage tracking. Make sure no other consumers depend on this metadata structure.

#### 11. `_scrape_question_urls` lost `domain`, `method`, `status_code` from url_meta

Line 680-682: The per-URL metadata dict in `_scrape_question_urls` no longer includes `domain`, `method`, or `status_code`. The corresponding fields were also removed from `base_forecaster.py` (line 294-298). This is consistent.

### src/bot/base_forecaster.py

#### 12. Consistent with search.py cleanup

The removal of `domain`, `method`, `status_code`, `content_words`, `error` from the QuestionURLScrape tool_usage entries is consistent with the search.py changes. The remaining fields (`tool`, `success`, `num_results`) are sufficient for basic analytics.

### scripts/analyze_scraping.py (deleted)

#### 13. Deletion is justified

The script consumed `tool_usage.json` fields (`url_results`, `scrape_stats`, `method`, `status_code`, `content_chars`, etc.) that are no longer produced. Deleting it is the right call since keeping it would just be dead code. If scraping analysis is needed again, it can be rebuilt from the simplified data format.

### tests/

#### 14. Test coverage is thorough

The new test file adds 15 new test methods covering:
- 5-day return computation and formatting
- Percentile rank computation with monotonically rising stock
- Ordinal suffix formatting (standard, teens, higher numbers)
- Conditional rates with rising stock, random walk, insufficient data
- Applicability flags for momentum and mean reversion
- Formatted output for conditional rates section
- Edge case: None conditional rates

The existing test fixtures have been updated to include the new fields. The mock simplifications in `test_search.py`, `test_fred_search.py`, and `test_yfinance_search.py` (replacing `GoogleScrapeResult(formatted_output="", url_results=[])` with `""`) are clean.

One suggestion: add a test that validates the percentile rank is correct for a known distribution (e.g., construct closes where the most recent 5-day return is at a known position in the distribution), rather than just checking the bounds.

---

## Overall Assessment

**Approve with minor suggestions.** The stock return enhancements (conditional base rates, percentile ranks, 5-day return) are well-designed and should meaningfully improve the context given to forecaster agents for stock price questions. The cleanup of content extraction metadata is a reasonable simplification that removes unused complexity.

Key items to address:
1. **Vectorize the volatility loop** (performance, not blocking)
2. **Fix the return type annotation** on `_compute_conditional_rates` (should be `list[dict] | None`)
3. **Consider restoring** `httpx.HTTPStatusError` specific handling in `_fetch_url`

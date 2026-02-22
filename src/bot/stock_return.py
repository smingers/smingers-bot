"""
Programmatic stock return distribution for close price questions.

Detects stock close price questions from Metaculus metadata, fetches historical
price data from yFinance, computes the N-day return distribution, and formats
it as context for the forecaster prompts.

This replaces LLM-guided yFinance queries for these questions with a deterministic
computation that provides an accurate base rate.
"""

import asyncio
import logging
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ConditionalRate:
    """A single conditional base rate computed from historical data."""

    label: str  # e.g., "3-month return > 20%"
    condition: str  # e.g., "momentum_positive"
    probability: float  # P(positive N-day return | condition)
    sample_size: int  # N windows matching condition
    delta: float  # Difference vs unconditional rate (pp)
    applicable: bool  # Whether this condition matches current state


@dataclass
class StockReturnData:
    """Computed return distribution for a stock close price question."""

    ticker: str
    start_date: str  # YYYY-MM-DD (reference close price date)
    end_date: str  # YYYY-MM-DD (resolution close price date)
    trading_days: int  # Business days between start and end

    # Current state
    current_price: float | None  # Latest available close price
    reference_price: float | None  # Close price on start_date (if available)
    return_so_far: float | None  # % return from start_date to latest (if started)

    # Historical return distribution
    sample_size: int  # Number of overlapping N-day windows
    positive_return_rate: float  # Fraction with return > 0
    mean_return: float  # Mean N-day return (%)
    median_return: float  # Median N-day return (%)
    std_return: float  # Std dev of N-day return (%)
    percentile_5: float  # 5th percentile (%)
    percentile_25: float  # 25th percentile (%)
    percentile_75: float  # 75th percentile (%)
    percentile_95: float  # 95th percentile (%)

    # Recent context
    recent_return_5d: float | None  # Last ~5 trading days return (%)
    recent_return_1m: float | None  # Last ~21 trading days return (%)
    recent_return_3m: float | None  # Last ~63 trading days return (%)
    volatility_30d: float | None  # 30-day realized volatility, annualized (%)

    # Historical percentile ranks for trailing returns (0-100)
    recent_return_5d_percentile: int | None
    recent_return_1m_percentile: int | None
    recent_return_3m_percentile: int | None

    # Conditional base rates
    conditional_rates: list[dict] | None  # List of serialized ConditionalRate dicts


def is_stock_close_price_question(description: str) -> bool:
    """Check if a question is a stock close price question.

    Args:
        description: The question.description field (nested, not top-level).

    Returns:
        True if the description contains the close_price_rises metadata.
    """
    return '"close_price_rises"' in description


def parse_stock_question(description: str, title: str) -> tuple[str, str, str] | None:
    """Parse ticker and dates from a stock close price question.

    Args:
        description: The question.description field containing the JSON metadata.
        title: The question title containing the dates.

    Returns:
        (ticker, start_date, end_date) or None if parsing fails.
    """
    # Extract ticker from JSON metadata block
    ticker_match = re.search(
        r'"format"\s*:\s*"close_price_rises"\s*,\s*"info"\s*:\s*\{\s*"ticker"\s*:\s*"([^"]+)"',
        description,
    )
    if not ticker_match:
        return None
    ticker = ticker_match.group(1)

    # Extract dates from title
    # Pattern: "Will TICKER's market close price on END_DATE be higher than
    #           its market close price on START_DATE?"
    date_match = re.search(
        r"close price on (\d{4}-\d{2}-\d{2}).*close price on (\d{4}-\d{2}-\d{2})",
        title,
    )
    if not date_match:
        return None

    end_date = date_match.group(1)
    start_date = date_match.group(2)
    return ticker, start_date, end_date


def compute_trading_days(start_date: str, end_date: str) -> int:
    """Compute the number of business days between two dates.

    Args:
        start_date: YYYY-MM-DD
        end_date: YYYY-MM-DD

    Returns:
        Number of business days (Mon-Fri) between the dates.
    """
    start = np.datetime64(start_date)
    end = np.datetime64(end_date)
    return int(np.busday_count(start, end))


MIN_CONDITIONAL_SAMPLE_SIZE = 80


def _compute_conditional_rates(
    closes: np.ndarray,
    returns: np.ndarray,
    trading_days: int,
    unconditional_rate: float,
    recent_return_5d: float | None,
    recent_return_3m: float | None,
    volatility_30d: float | None,
) -> list[dict]:
    """Compute conditional base rates from the same historical windows.

    Each conditional filters the N-day return windows by a condition computed
    at the start of each window, then reports P(positive return) for that subset.

    Args:
        closes: Full array of historical close prices.
        returns: Array of N-day returns (fractional, not %).
        trading_days: N (the window size used for returns).
        unconditional_rate: P(positive return) across all windows.
        recent_return_5d: Current 5-day trailing return (%) or None.
        recent_return_3m: Current 3-month trailing return (%) or None.
        volatility_30d: Current 30-day realized vol (annualized %) or None.

    Returns:
        List of ConditionalRate dicts (serialized via asdict).
    """
    n_windows = len(returns)
    # Window starting indices: window i starts at index i, ends at i + trading_days
    # returns[i] = (closes[i + trading_days] - closes[i]) / closes[i]
    # So for window i, the "start of window" price is closes[i].
    positive = returns > 0
    rates: list[dict] = []

    # Helper to add a conditional if it meets the sample size threshold
    def _add(label: str, condition: str, mask: np.ndarray, applicable: bool) -> None:
        n = int(np.sum(mask))
        if n < MIN_CONDITIONAL_SAMPLE_SIZE:
            return
        prob = float(np.mean(positive[mask]))
        delta = round((prob - unconditional_rate) * 100, 1)  # percentage points
        rates.append(
            asdict(
                ConditionalRate(
                    label=label,
                    condition=condition,
                    probability=round(prob, 4),
                    sample_size=n,
                    delta=delta,
                    applicable=applicable,
                )
            )
        )

    # --- (a) Momentum: 3-month (63-day) trailing return ---
    min_lookback_63 = 63
    if n_windows > 0 and len(closes) > min_lookback_63 + trading_days:
        # For each window starting at index i, trailing 63-day return as of day i
        start_indices = np.arange(n_windows)
        # Only consider windows where i >= 63 so we have enough history
        valid = start_indices >= min_lookback_63
        trailing_63d = np.full(n_windows, np.nan)
        vi = start_indices[valid]
        trailing_63d[valid] = (closes[vi] - closes[vi - 63]) / closes[vi - 63] * 100

        momentum_up = valid & (trailing_63d > 20)
        momentum_down = valid & (trailing_63d < -20)

        current_3m_up = recent_return_3m is not None and recent_return_3m > 20
        current_3m_down = recent_return_3m is not None and recent_return_3m < -20

        _add("3-month return > 20%", "momentum_positive", momentum_up, current_3m_up)
        _add("3-month return < -20%", "momentum_negative", momentum_down, current_3m_down)

    # --- (b) 52-week range position ---
    min_lookback_252 = 252
    if n_windows > 0 and len(closes) > min_lookback_252 + trading_days:
        start_indices = np.arange(n_windows)
        valid = start_indices >= min_lookback_252

        # Compute rolling 252-day high and low for each valid window start
        # Use a vectorized approach: for each valid i, compute max/min of closes[i-252:i+1]
        range_pos = np.full(n_windows, np.nan)
        vi = start_indices[valid]
        # Build a strided view for efficient rolling max/min
        # Window of size 253 (252 lookback + current day)
        window_size = 253
        if len(closes) >= window_size:
            shape = (len(closes) - window_size + 1, window_size)
            strides = (closes.strides[0], closes.strides[0])
            windowed = np.lib.stride_tricks.as_strided(closes, shape=shape, strides=strides)
            rolling_max = np.max(windowed, axis=1)
            rolling_min = np.min(windowed, axis=1)
            # windowed[j] covers closes[j:j+253], so the "current day" is at index j+252
            # For window starting at index i, we want the rolling stats ending at i,
            # which means j + 252 = i, so j = i - 252
            for_valid = vi - 252
            in_range = (for_valid >= 0) & (for_valid < len(rolling_max))
            valid_subset = vi[in_range]
            fv = for_valid[in_range]
            high = rolling_max[fv]
            low = rolling_min[fv]
            span = high - low
            nonzero = span > 0
            range_pos_vals = np.where(
                nonzero,
                (closes[valid_subset] - low) / span,
                0.5,
            )
            # Map back into the full array
            mask_indices = np.where(valid)[0]
            mapped = mask_indices[in_range]
            range_pos[mapped] = range_pos_vals

        top_decile = valid & (range_pos > 0.9)
        bottom_decile = valid & (range_pos < 0.1)

        # Current 52-week range position
        if len(closes) >= 253:
            curr_high = float(np.max(closes[-253:]))
            curr_low = float(np.min(closes[-253:]))
            curr_span = curr_high - curr_low
            if curr_span > 0:
                curr_pos = (float(closes[-1]) - curr_low) / curr_span
            else:
                curr_pos = 0.5
        else:
            curr_pos = 0.5

        _add(
            "Price in top decile of 52wk range",
            "range_top_decile",
            top_decile,
            curr_pos > 0.9,
        )
        _add(
            "Price in bottom decile of 52wk range",
            "range_bottom_decile",
            bottom_decile,
            curr_pos < 0.1,
        )

    # --- (c) Short-term mean-reversion: prior 5-day return ---
    min_lookback_5 = 5
    if n_windows > 0 and len(closes) > min_lookback_5 + trading_days:
        start_indices = np.arange(n_windows)
        valid = start_indices >= min_lookback_5
        trailing_5d = np.full(n_windows, np.nan)
        vi = start_indices[valid]
        trailing_5d[valid] = (closes[vi] - closes[vi - 5]) / closes[vi - 5] * 100

        prior_up = valid & (trailing_5d > 0)
        prior_down = valid & (trailing_5d < 0)

        current_5d_up = recent_return_5d is not None and recent_return_5d > 0
        current_5d_down = recent_return_5d is not None and recent_return_5d < 0

        _add("Prior 5-day return > 0", "mean_reversion_up", prior_up, current_5d_up)
        _add("Prior 5-day return < 0", "mean_reversion_down", prior_down, current_5d_down)

    # --- (d) Volatility regime ---
    min_lookback_30 = 30
    if n_windows > 0 and len(closes) > min_lookback_30 + trading_days:
        start_indices = np.arange(n_windows)
        valid = start_indices >= min_lookback_30

        # Compute 30-day realized vol for each valid window start
        window_vols = np.full(n_windows, np.nan)
        vi = start_indices[valid]
        # Vectorized: build daily returns for 30-day windows ending at each vi
        # daily_ret[j] = (closes[j+1] - closes[j]) / closes[j] for j in [vi-30, vi-1]
        # Then std * sqrt(252) * 100
        for idx in vi:
            window_closes = closes[idx - 30 : idx + 1]
            dr = np.diff(window_closes) / window_closes[:-1]
            window_vols[idx] = float(np.std(dr) * np.sqrt(252) * 100)

        valid_vols = window_vols[valid]
        median_vol = float(np.nanmedian(valid_vols))

        vol_above = valid & (window_vols > median_vol)
        vol_below = valid & (window_vols <= median_vol)

        current_vol_above = volatility_30d is not None and volatility_30d > median_vol
        current_vol_below = volatility_30d is not None and volatility_30d <= median_vol

        _add(
            "30-day vol above median",
            "vol_high",
            vol_above,
            current_vol_above,
        )
        _add(
            "30-day vol below median",
            "vol_low",
            vol_below,
            current_vol_below,
        )

    return rates if rates else None


def _compute_return_distribution(
    ticker: str,
    start_date: str,
    end_date: str,
    trading_days: int,
    history_years: int,
) -> StockReturnData | None:
    """Fetch historical data and compute return distribution.

    This is a synchronous function (yFinance is sync). Callers should
    wrap in asyncio.to_thread().

    Returns:
        StockReturnData or None on failure.
    """
    import yfinance as yf

    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=f"{history_years}y")

        if hist.empty or len(hist) < 252:  # Minimum 1 year of data
            logger.warning(
                f"[stock_return] Insufficient data for {ticker}: {len(hist)} rows (need >= 252)"
            )
            return None

        closes = hist["Close"].values

        # Compute rolling N-day returns (overlapping windows)
        if trading_days < 1:
            logger.warning(f"[stock_return] Invalid trading_days={trading_days}")
            return None

        if len(closes) <= trading_days:
            logger.warning(
                f"[stock_return] Not enough data for {trading_days}-day windows: "
                f"{len(closes)} closes"
            )
            return None

        returns = (closes[trading_days:] - closes[:-trading_days]) / closes[:-trading_days]
        returns_pct = returns * 100

        # Current state
        current_price = float(closes[-1])

        # Try to find reference price (close on start_date)
        reference_price = None
        return_so_far = None
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        today = datetime.now(tz=UTC)
        if start_dt.date() <= today.date():
            # Question has started — find close price nearest to start_date
            # Strip timezone from yFinance index (which may be tz-aware) so
            # get_indexer can match against a naive date string.
            if hist.index.tz is not None:
                hist.index = hist.index.tz_localize(None)
            start_idx = hist.index.get_indexer([start_dt.strftime("%Y-%m-%d")], method="ffill")
            if start_idx[0] >= 0:
                reference_price = float(hist["Close"].iloc[start_idx[0]])
                return_so_far = round((current_price - reference_price) / reference_price * 100, 2)

        # Recent context
        recent_return_5d = None
        recent_return_1m = None
        recent_return_3m = None
        if len(closes) > 5:
            recent_return_5d = round((closes[-1] - closes[-6]) / closes[-6] * 100, 2)
        if len(closes) > 21:
            recent_return_1m = round((closes[-1] - closes[-22]) / closes[-22] * 100, 2)
        if len(closes) > 63:
            recent_return_3m = round((closes[-1] - closes[-64]) / closes[-64] * 100, 2)

        # 30-day realized volatility (annualized)
        volatility_30d = None
        if len(closes) > 30:
            daily_returns = np.diff(closes[-31:]) / closes[-31:-1]
            volatility_30d = round(float(np.std(daily_returns) * np.sqrt(252) * 100), 1)

        # Historical percentile ranks for trailing returns
        recent_return_5d_percentile = None
        recent_return_1m_percentile = None
        recent_return_3m_percentile = None

        if recent_return_5d is not None and len(closes) > 5:
            all_5d = (closes[5:] - closes[:-5]) / closes[:-5] * 100
            sorted_5d = np.sort(all_5d)
            recent_return_5d_percentile = int(
                np.searchsorted(sorted_5d, recent_return_5d) / len(sorted_5d) * 100
            )

        if recent_return_1m is not None and len(closes) > 21:
            all_21d = (closes[21:] - closes[:-21]) / closes[:-21] * 100
            sorted_21d = np.sort(all_21d)
            recent_return_1m_percentile = int(
                np.searchsorted(sorted_21d, recent_return_1m) / len(sorted_21d) * 100
            )

        if recent_return_3m is not None and len(closes) > 63:
            all_63d = (closes[63:] - closes[:-63]) / closes[:-63] * 100
            sorted_63d = np.sort(all_63d)
            recent_return_3m_percentile = int(
                np.searchsorted(sorted_63d, recent_return_3m) / len(sorted_63d) * 100
            )

        # Conditional base rates
        unconditional_rate = float(np.mean(returns > 0))
        conditional_rates = _compute_conditional_rates(
            closes,
            returns,
            trading_days,
            unconditional_rate,
            recent_return_5d,
            recent_return_3m,
            volatility_30d,
        )

        return StockReturnData(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            trading_days=trading_days,
            current_price=round(current_price, 2),
            reference_price=round(reference_price, 2) if reference_price else None,
            return_so_far=return_so_far,
            sample_size=len(returns),
            positive_return_rate=round(unconditional_rate, 4),
            mean_return=round(float(np.mean(returns_pct)), 2),
            median_return=round(float(np.median(returns_pct)), 2),
            std_return=round(float(np.std(returns_pct)), 2),
            percentile_5=round(float(np.percentile(returns_pct, 5)), 2),
            percentile_25=round(float(np.percentile(returns_pct, 25)), 2),
            percentile_75=round(float(np.percentile(returns_pct, 75)), 2),
            percentile_95=round(float(np.percentile(returns_pct, 95)), 2),
            recent_return_5d=recent_return_5d,
            recent_return_1m=recent_return_1m,
            recent_return_3m=recent_return_3m,
            volatility_30d=volatility_30d,
            recent_return_5d_percentile=recent_return_5d_percentile,
            recent_return_1m_percentile=recent_return_1m_percentile,
            recent_return_3m_percentile=recent_return_3m_percentile,
            conditional_rates=conditional_rates,
        )

    except Exception as e:
        logger.error(f"[stock_return] Error computing distribution for {ticker}: {e}")
        return None


async def compute_stock_return_distribution(
    description: str,
    title: str,
    config: dict,
) -> StockReturnData | None:
    """Detect stock question, compute return distribution.

    Args:
        description: The question.description field (nested).
        title: The question title.
        config: Bot configuration dict.

    Returns:
        StockReturnData or None if not a stock question or computation fails.
    """
    if not config.get("research", {}).get("stock_return_enabled", True):
        return None

    if not is_stock_close_price_question(description):
        return None

    parsed = parse_stock_question(description, title)
    if not parsed:
        logger.warning("[stock_return] Could not parse stock question details")
        return None

    ticker, start_date, end_date = parsed
    trading_days = compute_trading_days(start_date, end_date)

    if trading_days < 1:
        logger.warning(f"[stock_return] Invalid window: {start_date} to {end_date}")
        return None

    history_years = config.get("research", {}).get("stock_return_history_years", 10)

    logger.info(
        f"[stock_return] Computing {trading_days}-day return distribution "
        f"for {ticker} ({start_date} to {end_date})"
    )

    data = await asyncio.to_thread(
        _compute_return_distribution,
        ticker,
        start_date,
        end_date,
        trading_days,
        history_years,
    )

    if data:
        logger.info(
            f"[stock_return] {ticker}: P(positive {trading_days}-day return) = "
            f"{data.positive_return_rate:.1%} (N={data.sample_size})"
        )

    return data


def _ordinal(n: int) -> str:
    """Return ordinal string for an integer (e.g., 1 -> '1st', 62 -> '62nd')."""
    if 11 <= (n % 100) <= 13:
        return f"{n}th"
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def format_stock_return_context(data: StockReturnData) -> str:
    """Format StockReturnData as context for forecaster prompts.

    Args:
        data: Computed return distribution data.

    Returns:
        Formatted context string.
    """
    lines = [
        "=== STOCK RETURN DISTRIBUTION (Programmatic Analysis) ===",
        f"Ticker: {data.ticker} | "
        f"Window: {data.start_date} to {data.end_date} ({data.trading_days} trading days)",
    ]

    if data.current_price:
        lines.append(f"Latest close price: ${data.current_price:.2f}")
    if data.reference_price:
        lines.append(f"Reference close price ({data.start_date}): ${data.reference_price:.2f}")
    if data.return_so_far is not None:
        direction = "up" if data.return_so_far > 0 else "down"
        lines.append(f"Return so far: {data.return_so_far:+.2f}% ({direction} from reference)")

    lines.append("")
    lines.append(
        f"HISTORICAL BASE RATE "
        f"({data.trading_days}-trading-day returns, "
        f"N={data.sample_size} overlapping windows):"
    )
    lines.append(f"  P(positive {data.trading_days}-day return): {data.positive_return_rate:.1%}")
    lines.append(f"  Mean return: {data.mean_return:+.2f}%")
    lines.append(f"  Median return: {data.median_return:+.2f}%")
    lines.append(f"  Std dev: {data.std_return:.2f}%")
    lines.append(
        f"  Percentiles: "
        f"5th={data.percentile_5:+.2f}%, "
        f"25th={data.percentile_25:+.2f}%, "
        f"75th={data.percentile_75:+.2f}%, "
        f"95th={data.percentile_95:+.2f}%"
    )

    has_recent = (
        data.recent_return_5d is not None
        or data.recent_return_1m is not None
        or data.recent_return_3m is not None
        or data.volatility_30d is not None
    )
    if has_recent:
        lines.append("")
        lines.append("RECENT CONTEXT:")
        if data.recent_return_5d is not None:
            pctile = (
                f" ({_ordinal(data.recent_return_5d_percentile)} percentile historically)"
                if data.recent_return_5d_percentile is not None
                else ""
            )
            lines.append(f"  5-day trailing return: {data.recent_return_5d:+.2f}%{pctile}")
        if data.recent_return_1m is not None:
            pctile = (
                f" ({_ordinal(data.recent_return_1m_percentile)} percentile historically)"
                if data.recent_return_1m_percentile is not None
                else ""
            )
            lines.append(f"  1-month trailing return: {data.recent_return_1m:+.2f}%{pctile}")
        if data.recent_return_3m is not None:
            pctile = (
                f" ({_ordinal(data.recent_return_3m_percentile)} percentile historically)"
                if data.recent_return_3m_percentile is not None
                else ""
            )
            lines.append(f"  3-month trailing return: {data.recent_return_3m:+.2f}%{pctile}")
        if data.volatility_30d is not None:
            lines.append(f"  30-day realized volatility: {data.volatility_30d:.1f}% (annualized)")

    if data.conditional_rates:
        lines.append("")
        lines.append(
            "CONDITIONAL BASE RATES (same historical data, filtered by current conditions):"
        )
        lines.append(
            f"  {'Unconditional:':<40s} "
            f"P(up) = {data.positive_return_rate:.1%} (N={data.sample_size})"
        )
        for cr in data.conditional_rates:
            label = f"{cr['label']}:"
            delta_sign = "+" if cr["delta"] >= 0 else ""
            flag = " <- CURRENTLY APPLICABLE" if cr["applicable"] else ""
            lines.append(
                f"  {label:<40s} "
                f"P(up) = {cr['probability']:.1%} "
                f"(N={cr['sample_size']}, "
                f"\u0394={delta_sign}{cr['delta']:.1f}pp){flag}"
            )

    lines.append("")
    lines.append(
        "This is a PROGRAMMATIC computation from actual historical price data. "
        "Use the historical base rate as an anchor and adjust for current conditions."
    )
    lines.append("=== END STOCK RETURN DISTRIBUTION ===")

    return "\n".join(lines)


def stock_return_data_to_dict(data: StockReturnData) -> dict:
    """Convert StockReturnData to a JSON-serializable dict for artifact storage."""
    return asdict(data)

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
from datetime import datetime, timezone

import numpy as np

logger = logging.getLogger(__name__)


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
    recent_return_1m: float | None  # Last ~21 trading days return (%)
    recent_return_3m: float | None  # Last ~63 trading days return (%)
    volatility_30d: float | None  # 30-day realized volatility, annualized (%)


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
        today = datetime.now(tz=timezone.utc)
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
        recent_return_1m = None
        recent_return_3m = None
        if len(closes) > 21:
            recent_return_1m = round((closes[-1] - closes[-22]) / closes[-22] * 100, 2)
        if len(closes) > 63:
            recent_return_3m = round((closes[-1] - closes[-64]) / closes[-64] * 100, 2)

        # 30-day realized volatility (annualized)
        volatility_30d = None
        if len(closes) > 30:
            daily_returns = np.diff(closes[-31:]) / closes[-31:-1]
            volatility_30d = round(float(np.std(daily_returns) * np.sqrt(252) * 100), 1)

        return StockReturnData(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            trading_days=trading_days,
            current_price=round(current_price, 2),
            reference_price=round(reference_price, 2) if reference_price else None,
            return_so_far=return_so_far,
            sample_size=len(returns),
            positive_return_rate=round(float(np.mean(returns > 0)), 4),
            mean_return=round(float(np.mean(returns_pct)), 2),
            median_return=round(float(np.median(returns_pct)), 2),
            std_return=round(float(np.std(returns_pct)), 2),
            percentile_5=round(float(np.percentile(returns_pct, 5)), 2),
            percentile_25=round(float(np.percentile(returns_pct, 25)), 2),
            percentile_75=round(float(np.percentile(returns_pct, 75)), 2),
            percentile_95=round(float(np.percentile(returns_pct, 95)), 2),
            recent_return_1m=recent_return_1m,
            recent_return_3m=recent_return_3m,
            volatility_30d=volatility_30d,
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

    if (
        data.recent_return_1m is not None
        or data.recent_return_3m is not None
        or data.volatility_30d is not None
    ):
        lines.append("")
        lines.append("RECENT CONTEXT:")
        if data.recent_return_1m is not None:
            lines.append(f"  1-month trailing return: {data.recent_return_1m:+.2f}%")
        if data.recent_return_3m is not None:
            lines.append(f"  3-month trailing return: {data.recent_return_3m:+.2f}%")
        if data.volatility_30d is not None:
            lines.append(f"  30-day realized volatility: {data.volatility_30d:.1f}% (annualized)")

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

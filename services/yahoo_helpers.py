"""
Reliable Yahoo Finance snapshots using yfinance.

`ticker.info` is a large scraped JSON blob that often omits or zeroes
`regularMarketPrice` / `currentPrice`. We prefer `fast_info` and recent
`history()` closes so symbols like AAPL return real prices.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import yfinance as yf


def _safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if x <= 0:
        return None
    return x


def get_reliable_price(ticker: yf.Ticker) -> Optional[float]:
    """Best-effort last traded / regular-session price."""
    try:
        fi = getattr(ticker, "fast_info", None)
        if fi is None and callable(getattr(ticker, "get_fast_info", None)):
            fi = ticker.get_fast_info()
        for key in ("last_price", "regular_market_price", "previous_close"):
            v = getattr(fi, key, None) if fi is not None else None
            p = _safe_float(v)
            if p is not None:
                return p
    except Exception:
        pass

    try:
        hist = ticker.history(period="5d", interval="1d", auto_adjust=True)
        if hist is not None and not hist.empty and "Close" in hist.columns:
            p = _safe_float(float(hist["Close"].iloc[-1]))
            if p is not None:
                return p
    except Exception:
        pass

    try:
        info = ticker.info or {}
        for key in (
            "currentPrice",
            "regularMarketPrice",
            "postMarketPrice",
            "preMarketPrice",
            "previousClose",
            "bid",
            "ask",
        ):
            p = _safe_float(info.get(key))
            if p is not None:
                return p
    except Exception:
        pass

    return None


def build_price_payload(symbol: str, ticker: yf.Ticker) -> Dict[str, Any]:
    """Fields expected by the frontend `/price/{symbol}` response."""
    price = get_reliable_price(ticker)
    if price is None:
        raise ValueError(f"No usable price for {symbol}")

    info: Dict[str, Any] = {}
    try:
        info = ticker.info or {}
    except Exception:
        info = {}

    def num(*keys: str) -> Optional[float]:
        for k in keys:
            v = info.get(k)
            p = _safe_float(v)
            if p is not None:
                return p
        return None

    prev = num("previousClose", "regularMarketPreviousClose")
    day_high = num("dayHigh", "regularMarketDayHigh")
    day_low = num("dayLow", "regularMarketDayLow")
    vol = info.get("volume") or info.get("regularMarketVolume")
    try:
        volume = int(vol) if vol is not None else None
    except (TypeError, ValueError):
        volume = None

    change = None
    change_pct = None
    if prev:
        change = round(price - prev, 4)
        change_pct = round((change / prev) * 100, 4)

    return {
        "symbol": symbol.upper(),
        "price": price,
        "previous_close": prev,
        "change": change if change is not None else info.get("regularMarketChange"),
        "change_percent": change_pct
        if change_pct is not None
        else info.get("regularMarketChangePercent"),
        "day_high": day_high,
        "day_low": day_low,
        "volume": volume,
        "market_cap": info.get("marketCap"),
        "currency": info.get("currency") or "USD",
    }

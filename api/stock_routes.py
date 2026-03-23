from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import Optional

import yfinance as yf
from services.alphavantage_service import AlphaVantageService
from services.openai_service import OpenAIService
from services.yahoo_helpers import build_price_payload
from services.history_cache import store_bars, latest_bars
from config import settings

router = APIRouter()

# UI time ranges → (yfinance period, interval)
UI_RANGE_MAP = {
    "1D": ("1d", "5m"),
    "1W": ("5d", "1h"),
    "1M": ("1mo", "1d"),
    "1Y": ("1y", "1d"),
    "MAX": ("max", "1wk"),
}

@router.get("/price/{symbol}")
async def get_stock_price(symbol: str):
    """Get current stock price for a symbol (Yahoo via yfinance; avoids broken .info-only prices)."""
    try:
        ticker = yf.Ticker(symbol)
        payload = build_price_payload(symbol, ticker)
        payload["timestamp"] = datetime.now().isoformat()
        return payload
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{symbol}")
async def get_price_history(
    symbol: str,
    time_range: Optional[str] = Query(
        default=None,
        alias="range",
        regex="^(1D|1W|1M|1Y|MAX)$",
        description="Preset: 1D, 1W, 1M, 1Y, MAX (overrides period/interval when set)",
    ),
    period: str = Query(default="1mo", regex="^(1d|5d|1mo|3mo|6mo|1y|2y|5y|10y|ytd|max)$"),
    interval: str = Query(default="1d", regex="^(1m|2m|5m|15m|30m|60m|90m|1h|1d|5d|1wk|1mo|3mo)$"),
):
    """Get historical OHLCV; persists each successful fetch to local SQLite."""
    if time_range:
        period, interval = UI_RANGE_MAP[time_range]

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval, auto_adjust=True)

        history_data = []
        if hist is not None and not hist.empty:
            for date, row in hist.iterrows():
                try:
                    o, h, l, c = float(row["Open"]), float(row["High"]), float(row["Low"]), float(row["Close"])
                    v = int(float(row["Volume"])) if row["Volume"] == row["Volume"] else 0
                except (TypeError, ValueError):
                    continue
                if not all(x == x for x in (o, h, l, c)):  # skip NaN
                    continue
                history_data.append({
                    "date": date.strftime("%Y-%m-%d %H:%M:%S"),
                    "open": o,
                    "high": h,
                    "low": l,
                    "close": c,
                    "volume": v,
                })

        if not history_data:
            cached = latest_bars(symbol)
            if not cached:
                raise HTTPException(
                    status_code=404,
                    detail=f"Historical data not found for {symbol}",
                )
            history_data = cached

        store_bars(symbol, history_data)

        return {
            "symbol": symbol.upper(),
            "period": period,
            "interval": interval,
            "ui_range": time_range,
            "data_points": len(history_data),
            "data": history_data,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alpha-history/{symbol}")
async def get_alpha_price_history(
    symbol: str,
    interval: str = Query(default="daily", regex="^(intraday|daily|weekly|monthly)$"),
    output_size: str = Query(default="compact", regex="^(compact|full)$"),
    intraday_interval: str = Query(default="60min", regex="^(1min|5min|15min|30min|60min)$")
):
    """Get price history from AlphaVantage."""
    if not settings.alphavantage_api_key:
        raise HTTPException(status_code=503, detail="AlphaVantage API key not configured")

    try:
        av_service = AlphaVantageService(settings.alphavantage_api_key)
        history = await av_service.get_price_history(
            symbol=symbol,
            interval=interval,
            output_size=output_size,
            intraday_interval=intraday_interval,
        )
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/info/{symbol}")
async def get_company_info(symbol: str):
    """Get company information for a symbol"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        if not info or 'symbol' not in info:
            raise HTTPException(status_code=404, detail=f"Company info not found for {symbol}")
        
        # Extract key information
        company_info = {
            "symbol": info.get('symbol', symbol.upper()),
            "name": info.get('longName') or info.get('shortName'),
            "sector": info.get('sector'),
            "industry": info.get('industry'),
            "website": info.get('website'),
            "description": info.get('longBusinessSummary'),
            "market_cap": info.get('marketCap'),
            "pe_ratio": info.get('trailingPE'),
            "dividend_yield": info.get('dividendYield'),
            "52_week_high": info.get('fiftyTwoWeekHigh'),
            "52_week_low": info.get('fiftyTwoWeekLow'),
            "currency": info.get('currency', 'USD')
        }
        
        return company_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/news/{symbol}")
async def get_stock_news(symbol: str, limit: int = Query(default=10, ge=1, le=50)):
    """Get news articles for a symbol"""
    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news[:limit] if ticker.news else []
        
        if not news:
            raise HTTPException(status_code=404, detail=f"News not found for {symbol}")
        
        news_list = []
        for article in news:
            news_list.append({
                "title": article.get('title'),
                "publisher": article.get('publisher'),
                "link": article.get('link'),
                "published_date": datetime.fromtimestamp(article.get('providerPublishTime', 0)).isoformat() if article.get('providerPublishTime') else None
            })
        
        return {
            "symbol": symbol.upper(),
            "count": len(news_list),
            "news": news_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trends/{symbol}")
async def get_trend_analysis(
    symbol: str,
    period: str = Query(default="1mo", regex="^(1d|5d|1mo|3mo|6mo|1y|2y|5y|10y|ytd|max)$")
):
    """Get AI-powered trend analysis for a symbol"""
    try:
        # Fetch market data
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"Historical data not found for {symbol}")
        
        # Calculate basic statistics
        current_price = float(hist['Close'].iloc[-1])
        previous_price = float(hist['Close'].iloc[0])
        change_percent = ((current_price - previous_price) / previous_price) * 100
        avg_volume = int(hist['Volume'].mean())
        volatility = float(hist['Close'].pct_change().std() * 100)
        
        # Get company info
        info = ticker.info
        company_name = info.get('longName') or info.get('shortName', symbol)
        
        # Prepare data for OpenAI
        market_data_summary = {
            "symbol": symbol.upper(),
            "company_name": company_name,
            "current_price": current_price,
            "previous_price": previous_price,
            "change_percent": round(change_percent, 2),
            "average_volume": avg_volume,
            "volatility": round(volatility, 2),
            "period": period,
            "data_points": len(hist)
        }
        
        # Use OpenAI to summarize trends
        if settings.openai_api_key:
            openai_service = OpenAIService(settings.openai_api_key)
            trend_summary = await openai_service.summarize_trends(market_data_summary)
            market_data_summary["ai_analysis"] = trend_summary
        else:
            market_data_summary["ai_analysis"] = "OpenAI API key not configured. Please set OPENAI_API_KEY in .env file."
        
        return market_data_summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/indicators/{symbol}")
async def get_technical_indicators(
    symbol: str,
    function: str = Query(default="TIME_SERIES_DAILY", regex="^(TIME_SERIES_DAILY|TIME_SERIES_WEEKLY|TIME_SERIES_MONTHLY|RSI|MACD|BBANDS|STOCH)$")
):
    """Get technical indicators from AlphaVantage API"""
    if not settings.alphavantage_api_key:
        raise HTTPException(status_code=503, detail="AlphaVantage API key not configured")
    
    try:
        av_service = AlphaVantageService(settings.alphavantage_api_key)
        indicators = await av_service.get_indicators(symbol, function)
        return indicators
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/categories/most-active")
async def get_most_active_stocks():
    """Get most actively traded stocks"""
    try:
        # Popular high-volume stocks
        symbols = ["AAPL", "TSLA", "NVDA", "AMD", "NIO", "PLTR", "AMC", "GME", "SPY", "QQQ", 
                   "MSFT", "GOOGL", "AMZN", "META", "BABA", "INTC", "PYPL", "SQ", "ROKU", "ZM"]
        
        stocks = []
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                payload = build_price_payload(symbol, ticker)
                info = {}
                try:
                    info = ticker.info or {}
                except Exception:
                    pass
                volume = info.get("volume") or info.get("regularMarketVolume", 0)
                if payload["price"] and volume:
                    stocks.append({
                        "symbol": symbol,
                        "name": info.get("longName") or info.get("shortName", symbol),
                        "price": payload["price"],
                        "volume": volume,
                        "change_percent": payload.get("change_percent")
                        or info.get("regularMarketChangePercent", 0),
                    })
            except Exception:
                continue
        
        # Sort by volume descending
        stocks.sort(key=lambda x: x['volume'], reverse=True)
        return {"category": "most_active", "stocks": stocks[:15]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/categories/high-growth")
async def get_high_growth_stocks():
    """Get high growth stocks (based on 1-year performance)"""
    try:
        # Growth-oriented stocks
        symbols = ["NVDA", "AMD", "TSLA", "MRNA", "ZM", "ROKU", "PTON", "PLTR", "SNOW", "DDOG",
                   "NET", "CRWD", "ZS", "DOCN", "UPST", "AFRM", "HOOD", "SOFI", "RBLX", "U"]
        
        stocks = []
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1y")
                if not hist.empty:
                    current_price = float(hist['Close'].iloc[-1])
                    year_ago_price = float(hist['Close'].iloc[0])
                    growth_percent = ((current_price - year_ago_price) / year_ago_price) * 100
                    
                    info = ticker.info
                    stocks.append({
                        "symbol": symbol,
                        "name": info.get('longName') or info.get('shortName', symbol),
                        "price": current_price,
                        "growth_1y": round(growth_percent, 2),
                        "market_cap": info.get('marketCap')
                    })
            except:
                continue
        
        # Sort by growth descending
        stocks.sort(key=lambda x: x['growth_1y'], reverse=True)
        return {"category": "high_growth", "stocks": stocks[:15]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/categories/dividend")
async def get_dividend_stocks():
    """Get dividend-paying stocks"""
    try:
        # Dividend stocks
        symbols = ["AAPL", "MSFT", "JPM", "JNJ", "PG", "KO", "PEP", "VZ", "T", "XOM",
                   "CVX", "WMT", "HD", "MCD", "NKE", "DIS", "BAC", "C", "GS", "IBM"]
        
        stocks = []
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info or {}
                dividend_yield = info.get("dividendYield")
                payload = build_price_payload(symbol, ticker)
                if dividend_yield and dividend_yield > 0 and payload["price"]:
                    stocks.append({
                        "symbol": symbol,
                        "name": info.get("longName") or info.get("shortName", symbol),
                        "price": payload["price"],
                        "dividend_yield": round(dividend_yield * 100, 2),
                        "dividend_rate": info.get("dividendRate"),
                        "payout_ratio": info.get("payoutRatio"),
                    })
            except Exception:
                continue
        
        # Sort by dividend yield descending
        stocks.sort(key=lambda x: x['dividend_yield'], reverse=True)
        return {"category": "dividend", "stocks": stocks[:15]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/categories/outperform-sp500")
async def get_outperform_sp500_stocks():
    """Get stocks that outperform S&P 500"""
    try:
        # Get S&P 500 performance
        sp500 = yf.Ticker("^GSPC")
        sp500_hist = sp500.history(period="1y")
        sp500_current = float(sp500_hist['Close'].iloc[-1])
        sp500_year_ago = float(sp500_hist['Close'].iloc[0])
        sp500_growth = ((sp500_current - sp500_year_ago) / sp500_year_ago) * 100
        
        # Popular stocks to compare
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "NFLX", "AMD", "INTC",
                   "PYPL", "ADBE", "CRM", "ORCL", "AVGO", "QCOM", "TXN", "AMAT", "LRCX", "MU"]
        
        stocks = []
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1y")
                if not hist.empty:
                    current_price = float(hist['Close'].iloc[-1])
                    year_ago_price = float(hist['Close'].iloc[0])
                    growth_percent = ((current_price - year_ago_price) / year_ago_price) * 100
                    
                    if growth_percent > sp500_growth:
                        info = ticker.info
                        stocks.append({
                            "symbol": symbol,
                            "name": info.get('longName') or info.get('shortName', symbol),
                            "price": current_price,
                            "growth_1y": round(growth_percent, 2),
                            "sp500_growth": round(sp500_growth, 2),
                            "outperformance": round(growth_percent - sp500_growth, 2)
                        })
            except:
                continue
        
        # Sort by outperformance descending
        stocks.sort(key=lambda x: x['outperformance'], reverse=True)
        return {
            "category": "outperform_sp500",
            "sp500_growth": round(sp500_growth, 2),
            "stocks": stocks[:15]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


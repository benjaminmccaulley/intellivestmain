from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime
import yfinance as yf
from services.massive_service import MassiveService
from config import settings

router = APIRouter()

@router.get("/price/{symbol}")
async def get_crypto_price(symbol: str):
    """Get current crypto price"""
    try:
        # Format symbol for yfinance (e.g., BTC-USD)
        if "-" not in symbol.upper():
            ticker_symbol = f"{symbol.upper()}-USD"
        else:
            ticker_symbol = symbol.upper()
        
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        
        if not current_price:
            raise HTTPException(status_code=404, detail=f"Price data not found for {symbol}")
        
        return {
            "symbol": symbol.upper(),
            "price": current_price,
            "currency": "USD",
            "market_cap": info.get('marketCap'),
            "volume_24h": info.get('volume24Hr'),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{symbol}")
async def get_crypto_history(
    symbol: str,
    period: str = Query(default="1mo", regex="^(1d|5d|1mo|3mo|6mo|1y|2y|5y|10y|ytd|max)$"),
    interval: str = Query(default="1d", regex="^(1m|2m|5m|15m|30m|60m|90m|1h|1d|5d|1wk|1mo|3mo)$")
):
    """Get historical crypto price data"""
    try:
        # Format symbol for yfinance
        if "-" not in symbol.upper():
            ticker_symbol = f"{symbol.upper()}-USD"
        else:
            ticker_symbol = symbol.upper()
        
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period=period, interval=interval)
        
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"Historical data not found for {symbol}")
        
        history_data = []
        for date, row in hist.iterrows():
            history_data.append({
                "date": date.strftime("%Y-%m-%d %H:%M:%S"),
                "open": float(row['Open']),
                "high": float(row['High']),
                "low": float(row['Low']),
                "close": float(row['Close']),
                "volume": int(row['Volume'])
            })
        
        return {
            "symbol": symbol.upper(),
            "period": period,
            "interval": interval,
            "data_points": len(history_data),
            "data": history_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trends")
async def get_crypto_trends():
    """Get crypto market trends from Massive API"""
    if not settings.massive_api_key:
        raise HTTPException(status_code=503, detail="Massive API key not configured")
    
    try:
        massive_service = MassiveService(settings.massive_api_key)
        trends = await massive_service.get_market_trends()
        return trends
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market-overview")
async def get_crypto_market_overview():
    """Get overall crypto market overview"""
    try:
        # Use yfinance to get multiple crypto prices
        cryptos = ["BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD"]
        market_data = []
        
        for symbol in cryptos:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                price = info.get('currentPrice') or info.get('regularMarketPrice')
                if price:
                    market_data.append({
                        "symbol": symbol.replace("-USD", ""),
                        "price": price,
                        "market_cap": info.get('marketCap'),
                        "change_24h": info.get('regularMarketChangePercent')
                    })
            except:
                continue
        
        return {
            "timestamp": datetime.now().isoformat(),
            "cryptocurrencies": market_data,
            "count": len(market_data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



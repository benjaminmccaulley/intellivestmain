from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime
import yfinance as yf

router = APIRouter()

@router.get("/{symbol}")
async def get_news(symbol: str, limit: int = Query(default=10, ge=1, le=50)):
    """Get news articles for a stock symbol"""
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
                "published_date": datetime.fromtimestamp(article.get('providerPublishTime', 0)).isoformat() if article.get('providerPublishTime') else None,
                "related_symbols": article.get('relatedTickers', [])
            })
        
        return {
            "symbol": symbol.upper(),
            "count": len(news_list),
            "news": news_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_general_news():
    """Get general market news"""
    try:
        # Use a popular ticker to get general news
        ticker = yf.Ticker("SPY")  # S&P 500 ETF
        news = ticker.news[:20] if ticker.news else []
        
        news_list = []
        for article in news:
            news_list.append({
                "title": article.get('title'),
                "publisher": article.get('publisher'),
                "link": article.get('link'),
                "published_date": datetime.fromtimestamp(article.get('providerPublishTime', 0)).isoformat() if article.get('providerPublishTime') else None,
                "related_symbols": article.get('relatedTickers', [])
            })
        
        return {
            "category": "general_market",
            "count": len(news_list),
            "news": news_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



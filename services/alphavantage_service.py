import httpx
from typing import Dict, Any

class AlphaVantageService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
    
    async def get_indicators(self, symbol: str, function: str) -> Dict[str, Any]:
        """Fetch technical indicators from AlphaVantage API"""
        params = {
            "function": function,
            "symbol": symbol.upper(),
            "apikey": self.api_key
        }
        
        # Add function-specific parameters
        if function == "RSI":
            params.update({"interval": "daily", "time_period": 14, "series_type": "close"})
        elif function == "MACD":
            params.update({"interval": "daily", "series_type": "close"})
        elif function == "BBANDS":
            params.update({"interval": "daily", "time_period": 20, "series_type": "close"})
        elif function == "STOCH":
            params.update({"interval": "daily"})
        else:
            params.update({"outputsize": "compact"})
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Check for API errors
            if "Error Message" in data:
                raise Exception(data["Error Message"])
            if "Note" in data:
                raise Exception("API rate limit exceeded. Please try again later.")
            
            return {
                "symbol": symbol.upper(),
                "function": function,
                "data": data
            }
    
    async def get_price_history(
        self,
        symbol: str,
        interval: str = "daily",
        output_size: str = "compact",
        intraday_interval: str = "60min",
    ) -> Dict[str, Any]:
        """Fetch price history (time series) from AlphaVantage."""
        function_map = {
            "intraday": "TIME_SERIES_INTRADAY",
            "daily": "TIME_SERIES_DAILY",
            "weekly": "TIME_SERIES_WEEKLY",
            "monthly": "TIME_SERIES_MONTHLY",
        }
        function = function_map.get(interval, "TIME_SERIES_DAILY")

        params = {
            "function": function,
            "symbol": symbol.upper(),
            "apikey": self.api_key,
            "outputsize": output_size,
        }

        if interval == "intraday":
            params["interval"] = intraday_interval

        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

        if "Error Message" in data:
            raise Exception(data["Error Message"])
        if "Note" in data:
            raise Exception("API rate limit exceeded. Please try again later.")

        time_series_key = next(
            (key for key in data.keys() if "Time Series" in key),
            None,
        )
        if not time_series_key:
            raise Exception("Unexpected response from AlphaVantage")

        time_series = data[time_series_key]
        parsed_series = [
            {
                "date": timestamp,
                "open": float(values.get("1. open", 0)),
                "high": float(values.get("2. high", 0)),
                "low": float(values.get("3. low", 0)),
                "close": float(values.get("4. close", 0)),
                "volume": float(values.get("5. volume", 0)),
            }
            for timestamp, values in time_series.items()
        ]

        return {
            "symbol": symbol.upper(),
            "function": function,
            "interval": interval,
            "output_size": output_size,
            "data_points": len(parsed_series),
            "data": parsed_series,
            "raw": data.get("Meta Data", {}),
        }


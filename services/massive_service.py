import httpx
from typing import Dict, Any, Optional

class MassiveService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.massive.io/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def get_market_trends(self) -> Dict[str, Any]:
        """Fetch crypto market trends from Massive API"""
        try:
            async with httpx.AsyncClient() as client:
                # Try common endpoints for crypto trends
                endpoints = [
                    "/market/trends",
                    "/trends",
                    "/crypto/trends",
                    "/market/overview"
                ]
                
                for endpoint in endpoints:
                    try:
                        response = await client.get(
                            f"{self.base_url}{endpoint}",
                            headers=self.headers,
                            timeout=10.0
                        )
                        if response.status_code == 200:
                            return response.json()
                    except:
                        continue
                
                # If no endpoint works, return a structured response
                # Note: Massive API endpoints may vary, this is a placeholder structure
                raise Exception("Could not connect to Massive API. Please check your API key and endpoint configuration.")
        except httpx.HTTPError as e:
            raise Exception(f"HTTP error connecting to Massive API: {str(e)}")
        except Exception as e:
            raise Exception(f"Error fetching crypto trends: {str(e)}")
    
    async def get_crypto_price(self, symbol: str) -> Dict[str, Any]:
        """Get crypto price from Massive API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/crypto/{symbol.upper()}",
                    headers=self.headers,
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"HTTP error: {str(e)}")
        except Exception as e:
            raise Exception(f"Error fetching crypto price: {str(e)}")



import asyncio
from typing import Any, Dict
from openai import OpenAI

class OpenAIService:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    async def summarize_trends(self, market_data: Dict[str, Any]) -> str:
        """Summarize market trends using OpenAI"""
        try:
            prompt = f"""
            Analyze the following stock market data and provide a brief trend summary (2-3 sentences):
            
            Symbol: {market_data.get('symbol')}
            Company: {market_data.get('company_name')}
            Current Price: ${market_data.get('current_price'):.2f}
            Previous Price: ${market_data.get('previous_price'):.2f}
            Change: {market_data.get('change_percent'):.2f}%
            Average Volume: {market_data.get('average_volume'):,}
            Volatility: {market_data.get('volatility'):.2f}%
            Period: {market_data.get('period')}
            
            Provide a concise analysis of the stock's performance, including whether it's trending up or down, 
            volatility assessment, and any notable observations.
            """
            
            return await asyncio.to_thread(self._send_completion, prompt)
        except Exception as e:
            return f"Error generating analysis: {str(e)}"

    def _send_completion(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial analyst providing concise stock market analysis.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=200,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()


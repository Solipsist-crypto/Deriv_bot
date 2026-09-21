import json
import asyncio

class MarketManager:
    def __init__(self, account_manager):
        self.account_manager = account_manager

    async def get_candles(self, ws, symbol: str, count: int = 100, timeframe: int = 300) -> list:
        """Отримує свічки через єдине існуюче WebSocket-з'єднання."""
        try:
            request = {
                "ticks_history": symbol,
                "adjust_start_time": 1,
                "count": count,
                "end": "latest",
                "style": "candles",
                "granularity": timeframe
            }
            await ws.send(json.dumps(request))
            
            response = await asyncio.wait_for(ws.recv(), timeout=10)
            data = json.loads(response)

            if "candles" in data:
                return data["candles"]
            else:
                print(f"⚠️ [MarketManager] Помилка свічок ({symbol}): {data.get('error', data)}")
        except Exception as e:
            print(f"❌ [MarketManager] Помилка WebSocket ({symbol}): {e}")
            
        return []
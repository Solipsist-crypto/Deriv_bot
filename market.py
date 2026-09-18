import json
import websockets

class MarketManager:
    def __init__(self, account_manager):
        self.account_manager = account_manager

    async def get_candles(self, symbol: str, count: int = 100, timeframe: int = 300) -> list:
        """
        Отримує історичні свічки для будь-якого активу.
        timeframe: 300 = 5 хвилин.
        """
        ws_url = self.account_manager.get_otp_url()
        if not ws_url:
            print(f"❌ [MarketManager] Не вдалося отримати WebSocket URL для {symbol}.")
            return []

        try:
            async with websockets.connect(ws_url) as ws:
                request = {
                    "ticks_history": symbol,
                    "adjust_start_time": 1,
                    "count": count,
                    "end": "latest",
                    "style": "candles",
                    "granularity": timeframe
                }
                await ws.send(json.dumps(request))
                response = await ws.recv()
                data = json.loads(response)

                if "candles" in data:
                    return data["candles"]
                else:
                    print(f"⚠️ [MarketManager] Помилка свічок ({symbol}): {data}")
        except Exception as e:
            print(f"❌ [MarketManager] Помилка WebSocket ({symbol}): {e}")
            
        return []
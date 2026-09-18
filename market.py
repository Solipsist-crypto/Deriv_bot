import json
import websockets
from config import APP_ID

class MarketManager:
    def __init__(self, account_manager):
        self.account_manager = account_manager
        # Використовуємо публічний WebSocket Deriv! 
        # Більше жодних OTP та таймаутів при отриманні свічок.
        self.public_ws_url = f"wss://ws.derivws.com/websockets/v3?app_id={APP_ID}"

    async def get_candles(self, symbol: str, count: int = 100, timeframe: int = 300) -> list:
        try:
            async with websockets.connect(self.public_ws_url) as ws:
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
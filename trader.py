# trader.py

import asyncio
import json
import websockets

class TraderManager:
    def __init__(self, account_manager):
        self.account_manager = account_manager

    async def execute_trade(self, symbol: str, signal: str, amount: float = 1.0, duration: int = 15, duration_unit: str = "m") -> dict:
        """
        Запитує proposal, купує контракт CALL/PUT та чекає на його закриття.
        """
        if signal not in ["BUY", "SELL"]:
            print(f"⚠️ [TraderManager] Некоректний сигнал для {symbol}: {signal}")
            return None

        _, ws_url = self.account_manager.get_ws_url() if hasattr(self.account_manager, 'get_ws_url') else (None, self.account_manager.get_otp_url())
        
        if not ws_url:
            print("❌ [TraderManager] Не вдалося отримати WebSocket URL.")
            return None

        contract_type = "CALL" if signal == "BUY" else "PUT"

        try:
            async with websockets.connect(ws_url) as ws:
                # 1. Запитуємо proposal
                proposal_req = {
                    "proposal": 1,
                    "amount": amount,
                    "basis": "stake",
                    "contract_type": contract_type,
                    "currency": self.account_manager.currency or "USD",
                    "duration": duration,
                    "duration_unit": duration_unit,
                    "underlying_symbol": symbol
                }

                print(f"📩 [TraderManager] Запитуємо proposal: {contract_type} по {symbol} (${amount}, {duration}{duration_unit})...")
                await ws.send(json.dumps(proposal_req))
                
                proposal_id = None
                ask_price = None

                while True:
                    resp = json.loads(await ws.recv())
                    if "error" in resp:
                        print(f"❌ [TraderManager] Помилка proposal ({symbol}): {resp['error']['message']}")
                        return None

                    if resp.get("msg_type") == "proposal":
                        proposal_data = resp.get("proposal", {})
                        proposal_id = proposal_data.get("id")
                        ask_price = proposal_data.get("ask_price")
                        print(f"✅ [TraderManager] Proposal отримано! ID: {proposal_id} | Ціна: {ask_price} USD")
                        break

                # 2. Купуємо контракт
                buy_req = {
                    "buy": proposal_id,
                    "price": ask_price
                }

                print(f"🎰 [TraderManager] Відправляємо ордер на купівлю {symbol}...")
                await ws.send(json.dumps(buy_req))

                contract_id = None
                while True:
                    buy_resp = json.loads(await ws.recv())
                    if "error" in buy_resp:
                        print(f"❌ [TraderManager] Помилка купівлі ({symbol}): {buy_resp['error']['message']}")
                        return None

                    if buy_resp.get("msg_type") == "buy":
                        buy_info = buy_resp.get("buy", {})
                        contract_id = buy_info.get("contract_id")
                        print(f"🎉 [TraderManager] УГОДУ ВІДКРИТО! Contract ID: {contract_id}")
                        break

                # 3. Чекаємо на закриття
                await ws.send(json.dumps({"proposal_open_contract": 1, "contract_id": contract_id}))
                print(f"⏳ [TraderManager] Очікуємо завершення угоди по {symbol}...")

                while True:
                    msg = await ws.recv()
                    res_data = json.loads(msg)
                    contract_data = res_data.get("proposal_open_contract", {})

                    if contract_data.get("is_expired") or contract_data.get("is_sold"):
                        profit = float(contract_data.get("profit", 0.0))
                        status = contract_data.get("status")
                        is_win = 1 if status == "won" or profit > 0 else 0
                        
                        print(f"\n🏁 [TraderManager] УГОДУ ЗАКРИТО по {symbol}!")
                        print(f"📊 Результат: {status.upper()} | Профіт: {profit} USD")
                        
                        return {
                            "contract_id": contract_id,
                            "symbol": symbol,
                            "signal": signal,
                            "status": status,
                            "profit": profit,
                            "win": is_win
                        }
                    
                    await asyncio.sleep(2)

        except Exception as e:
            print(f"❌ [TraderManager] Помилка торгівлі ({symbol}): {e}")

        return None
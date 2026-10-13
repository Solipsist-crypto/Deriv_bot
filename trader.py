import asyncio
import json
import websockets

class TraderManager:
    def __init__(self, account_manager):
        self.account_manager = account_manager
        # Створюємо чергу, щоб угоди відкривалися по черзі (захист API Deriv від спаму)
        self.trade_lock = asyncio.Lock()

    async def execute_trade(self, symbol: str, signal: str, amount: float = 1.0, duration: int = 15, duration_unit: str = "m") -> dict:
        if signal not in ["BUY", "SELL"]:
            return None

        contract_type = "CALL" if signal == "BUY" else "PUT"
        contract_id = None

        # 1. ВІДКРИТТЯ УГОДИ (У черзі, щоб брокер не плутав паралельні proposal_id)
        async with self.trade_lock:
            for attempt in range(1, 4):
                ws_url = await self.account_manager.get_otp_url()
                if not ws_url:
                    print(f"❌ [TraderManager] Не вдалося отримати WebSocket URL (спроба {attempt}).")
                    await asyncio.sleep(1)
                    continue

                try:
                    async with websockets.connect(ws_url, open_timeout=10) as ws:
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

                        print(f"📩 [TraderManager] Запитуємо proposal (спроба {attempt}): {contract_type} по {symbol} (${amount}, {duration}{duration_unit})...")
                        await ws.send(json.dumps(proposal_req))
                        
                        # Читаємо відповідь (ігноруємо системні повідомлення брокера)
                        proposal_id = None
                        ask_price = None
                        for _ in range(3):
                            resp_str = await asyncio.wait_for(ws.recv(), timeout=10)
                            resp = json.loads(resp_str)
                            
                            if "error" in resp:
                                print(f"❌ [TraderManager] Помилка API ({symbol}): {resp['error']['message']}")
                                break
                            
                            if resp.get("msg_type") == "proposal":
                                proposal_data = resp.get("proposal", {})
                                proposal_id = proposal_data.get("id")
                                ask_price = proposal_data.get("ask_price")
                                break
                        
                        if not proposal_id:
                            await asyncio.sleep(0.5)
                            continue

                        print(f"✅ [TraderManager] Proposal отримано! ID: {proposal_id} | Ціна: {ask_price} USD")

                        # Відправляємо ордер
                        buy_req = {
                            "buy": proposal_id,
                            "price": ask_price
                        }

                        print(f"🎰 [TraderManager] Відправляємо ордер на купівлю {symbol}...")
                        await ws.send(json.dumps(buy_req))

                        # Читаємо результат купівлі
                        for _ in range(3):
                            buy_resp_str = await asyncio.wait_for(ws.recv(), timeout=10)
                            buy_resp = json.loads(buy_resp_str)
                            
                            if "error" in buy_resp:
                                err_msg = buy_resp['error']['message']
                                print(f"❌ [TraderManager] Помилка купівлі ({symbol}): {err_msg}")
                                break
                            
                            if buy_resp.get("msg_type") == "buy":
                                contract_id = buy_resp.get("buy", {}).get("contract_id")
                                break

                        if contract_id:
                            print(f"🎉 [TraderManager] УГОДУ ВІДКРИТО! Contract ID: {contract_id}")
                            break  # Успішно! Виходимо з циклу спроб
                        else:
                            print("🔄 Збій при купівлі, робимо повторний запит...")
                            await asyncio.sleep(0.5)
                            continue

                except Exception as e:
                    print(f"❌ [TraderManager] Помилка підключення/відкриття ({symbol}): {e}")
                    await asyncio.sleep(1)

        # 2. ПОЗА ЧЕРГОЮ (чекаємо 15 хвилин на результат паралельно з іншими монетами)
        if not contract_id:
            print(f"❌ [TraderManager] Не вдалося відкрити угоду по {symbol} після 3 спроб.")
            return None

        wait_seconds = (duration * 60 if duration_unit == "m" else duration) + 5
        print(f"⏳ [TraderManager] Чекаємо {wait_seconds} сек. до закінчення експірації по {symbol}...")
        await asyncio.sleep(wait_seconds)

        # 3. ПЕРЕВІРКА РЕЗУЛЬТАТУ УГОДИ
        print(f"🔍 [TraderManager] Запитуємо результат закриття угоди {contract_id} ({symbol})...")
        check_ws_url = await self.account_manager.get_otp_url()
        if not check_ws_url:
            print(f"⚠️ [TraderManager] Не вдалося отримати URL для перевірки результату ({symbol}).")
            return None

        try:
            async with websockets.connect(check_ws_url, open_timeout=10) as ws:
                await ws.send(json.dumps({"proposal_open_contract": 1, "contract_id": contract_id}))
                
                for _ in range(5):
                    msg = await asyncio.wait_for(ws.recv(), timeout=10)
                    res_data = json.loads(msg)
                    contract_data = res_data.get("proposal_open_contract", {})

                    if contract_data:
                        profit = float(contract_data.get("profit", 0.0))
                        status = contract_data.get("status", "unknown")
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
            print(f"❌ [TraderManager] Помилка отримання результату ({symbol}): {e}")

        return None
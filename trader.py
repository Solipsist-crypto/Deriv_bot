import asyncio
import json
import websockets

class TraderManager:
    def __init__(self, account_manager):
        self.account_manager = account_manager
        # Черга для уникнення мережевих конфліктів при одночасних сигналах
        self.trade_lock = asyncio.Lock()

    async def execute_trade(self, symbol: str, signal: str, amount: float = 1.0, duration: int = 15, duration_unit: str = "m") -> dict:
        if signal not in ["BUY", "SELL"]:
            return None

        contract_type = "CALL" if signal == "BUY" else "PUT"
        contract_id = None

        async with self.trade_lock:
            for attempt in range(1, 4):
                ws_url = await self.account_manager.get_otp_url()
                if not ws_url:
                    print(f"❌ [TraderManager] Не вдалося отримати WebSocket URL (спроба {attempt}).")
                    await asyncio.sleep(1)
                    continue

                try:
                    # Відкриваємо нове з'єднання на кожну спробу, щоб ізолювати підписки (subscribe: 1)
                    async with websockets.connect(ws_url, open_timeout=10) as ws:
                        print(f"📩 [TraderManager] Запитуємо proposal (спроба {attempt}): {contract_type} по {symbol} (${amount}, {duration}{duration_unit})...")
                        
                        proposal_req = {
                            "proposal": 1,
                            "subscribe": 1,
                            "amount": amount,
                            "basis": "stake",
                            "contract_type": contract_type,
                            "currency": self.account_manager.currency or "USD",
                            "duration": duration,
                            "duration_unit": duration_unit,
                            "underlying_symbol": symbol
                        }
                        await ws.send(json.dumps(proposal_req))

                        proposal_id = None
                        ask_price = None

                        # Ловимо саме повідомлення з msg_type == "proposal"
                        while True:
                            try:
                                resp_str = await asyncio.wait_for(ws.recv(), timeout=5)
                                resp = json.loads(resp_str)
                                
                                if "error" in resp:
                                    print(f"❌ [TraderManager] Помилка proposal ({symbol}): {resp['error']['message']}")
                                    break

                                if resp.get("msg_type") == "proposal":
                                    proposal_data = resp.get("proposal", {})
                                    proposal_id = proposal_data.get("id")
                                    ask_price = proposal_data.get("ask_price")
                                    break
                            except asyncio.TimeoutError:
                                break

                        if not proposal_id:
                            await asyncio.sleep(0.5)
                            continue

                        print(f"✅ [TraderManager] Proposal отримано! ID: {proposal_id} | Ціна: {ask_price} USD")

                        # Надсилаємо ордер на купівлю
                        buy_req = {
                            "buy": proposal_id,
                            "price": ask_price
                        }
                        print(f"🎰 [TraderManager] Відправляємо ордер на купівлю {symbol}...")
                        await ws.send(json.dumps(buy_req))

                        # Фільтруємо стрім повідомлень (ігноруємо тіки/оновлення proposal і чекаємо "buy")
                        is_bought = False
                        for _ in range(20):
                            try:
                                buy_resp_str = await asyncio.wait_for(ws.recv(), timeout=10)
                                buy_resp = json.loads(buy_resp_str)

                                if "error" in buy_resp:
                                    print(f"❌ [TraderManager] Помилка купівлі ({symbol}): {buy_resp['error']['message']}")
                                    break

                                if buy_resp.get("msg_type") == "buy":
                                    contract_id = buy_resp.get("buy", {}).get("contract_id")
                                    is_bought = True
                                    break
                            except asyncio.TimeoutError:
                                break

                        if is_bought and contract_id:
                            print(f"🎉 [TraderManager] УГОДУ ВІДКРИТО! Contract ID: {contract_id}")
                            break
                        else:
                            print("🔄 Повторна спроба відправки proposal...")
                            await asyncio.sleep(0.5)

                except Exception as e:
                    print(f"❌ [TraderManager] Помилка з'єднання ({symbol}): {e}")
                    await asyncio.sleep(1)

        if not contract_id:
            print(f"❌ [TraderManager] Не вдалося відкрити угоду по {symbol} після 3 спроб.")
            return None

        # 2. ОЧІКУВАННЯ ЕКСПІРАЦІЇ (15 хвилин)
        wait_seconds = (duration * 60 if duration_unit == "m" else duration) + 5
        print(f"⏳ [TraderManager] Чекаємо {wait_seconds} сек. до закінчення експірації по {symbol}...")
        await asyncio.sleep(wait_seconds)

        # 3. ПЕРЕВІРКА РЕЗУЛЬТАТУ ЗАКРИТТЯ (З очікуванням is_sold)
        print(f"🔍 [TraderManager] Запитуємо результат закриття угоди {contract_id} ({symbol})...")
        check_ws_url = await self.account_manager.get_otp_url()
        if not check_ws_url:
            print(f"⚠️ [TraderManager] Не вдалося отримати URL для перевірки результату ({symbol}).")
            return None

        try:
            async with websockets.connect(check_ws_url, open_timeout=10) as ws:
                await ws.send(json.dumps({
                    "proposal_open_contract": 1,
                    "contract_id": contract_id,
                    "subscribe": 1
                }))
                
                # Чекаємо, поки брокер підтвердить факт продажу (is_sold)
                for _ in range(120):
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=15)
                        res_data = json.loads(msg)
                        contract_data = res_data.get("proposal_open_contract", {})

                        if contract_data and contract_data.get("is_sold"):
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
                    except asyncio.TimeoutError:
                        # Якщо timeout спрацював, просто чекаємо наступного повідомлення
                        continue

        except Exception as e:
            print(f"❌ [TraderManager] Помилка отримання результату ({symbol}): {e}")

        return None
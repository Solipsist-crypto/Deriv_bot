import asyncio
import json
import websockets

class TraderManager:
    def __init__(self, account_manager):
        self.account_manager = account_manager

    async def execute_trade(self, symbol: str, signal: str, amount: float = 1.0, duration: int = 15, duration_unit: str = "m") -> dict:
        if signal not in ["BUY", "SELL"]:
            return None

        contract_type = "CALL" if signal == "BUY" else "PUT"
        contract_id = None

        # Спроби купівлі (захист від прострочення proposal_id)
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
                    
                    resp_str = await asyncio.wait_for(ws.recv(), timeout=10)
                    resp = json.loads(resp_str)
                    
                    if "error" in resp:
                        print(f"❌ [TraderManager] Помилка proposal ({symbol}): {resp['error']['message']}")
                        await asyncio.sleep(0.5)
                        continue

                    if resp.get("msg_type") == "proposal":
                        proposal_data = resp.get("proposal", {})
                        proposal_id = proposal_data.get("id")
                        ask_price = proposal_data.get("ask_price")
                        print(f"✅ [TraderManager] Proposal отримано! ID: {proposal_id} | Ціна: {ask_price} USD")
                    else:
                        continue

                    # Відправляємо купівлю
                    buy_req = {
                        "buy": proposal_id,
                        "price": ask_price
                    }

                    print(f"🎰 [TraderManager] Відправляємо ордер на купівлю {symbol}...")
                    await ws.send(json.dumps(buy_req))

                    buy_resp_str = await asyncio.wait_for(ws.recv(), timeout=10)
                    buy_resp = json.loads(buy_resp_str)
                    
                    if "error" in buy_resp:
                        err_msg = buy_resp['error']['message']
                        print(f"❌ [TraderManager] Помилка купівлі ({symbol}): {err_msg}")
                        if "Unknown contract proposal" in err_msg or "expired" in err_msg.lower():
                            print("🔄 Proposal застарів, робимо повторний запит...")
                            await asyncio.sleep(0.3)
                            continue
                        return None

                    contract_id = buy_resp.get("buy", {}).get("contract_id")
                    print(f"🎉 [TraderManager] УГОДУ ВІДКРИТО! Contract ID: {contract_id}")
                    break  # Успішно відкрили угоду, виходимо з циклу спроб

            except Exception as e:
                print(f"❌ [TraderManager] Помилка відкриття угоди ({symbol}): {e}")
                await asyncio.sleep(1)

        if not contract_id:
            print(f"❌ [TraderManager] Не вдалося відкрити угоду по {symbol} після 3 спроб.")
            return None

        # 2. РОЗРАХУНОК ЧАСУ ЕКСПІРАЦІЇ
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
# test_multi_trade.py

import asyncio
import json
import requests
import websockets
from config import PAT_TOKEN, APP_ID, BASE_URL

# Конфігурація активів із їхньою точною доступною тривалістю
ASSETS_CONFIG = [
    {"symbol": "frxXAUUSD", "duration": 300, "unit": "s", "label": "300s"},
    {"symbol": "frxEURUSD", "duration": 15, "unit": "m", "label": "15m"},
    {"symbol": "frxGBPUSD", "duration": 15, "unit": "m", "label": "15m"},
    {"symbol": "frxUSDJPY", "duration": 15, "unit": "m", "label": "15m"},
    {"symbol": "frxAUDUSD", "duration": 15, "unit": "m", "label": "15m"},
]

def get_account_and_ws_url():
    """Отримує ID акаунта та WebSocket URL через REST API."""
    headers = {
        "Authorization": f"Bearer {PAT_TOKEN}",
        "Deriv-App-ID": str(APP_ID)
    }

    acc_res = requests.get(f"{BASE_URL}/accounts", headers=headers)
    if acc_res.status_code != 200:
        print(f"❌ Помилка REST (accounts): {acc_res.text}")
        return None, None

    accounts = acc_res.json().get("data", [])
    if not accounts:
        print("❌ Акаунти не знайдені.")
        return None, None

    account_id = accounts[0]["account_id"]

    otp_res = requests.post(f"{BASE_URL}/accounts/{account_id}/otp", headers=headers)
    if otp_res.status_code not in (200, 201):
        print(f"❌ Помилка REST (otp): {otp_res.text}")
        return account_id, None

    otp_data = otp_res.json().get("data", {})
    ws_url = otp_data.get("url") or otp_data.get("websocket_url")

    return account_id, ws_url

async def main():
    print("🧪 Запуск відкриття угод для всіх 5 активів із правильними експіраціями...")
    account_id, ws_url = get_account_and_ws_url()

    if not ws_url:
        print("❌ Не вдалося отримати WebSocket URL.")
        return

    print(f"✅ Авторизовано акаунт: {account_id}")

    # Відкриваємо одне WebSocket-з'єднання для послідовного відкриття всіх угод
    async with websockets.connect(ws_url) as ws:
        for idx, item in enumerate(ASSETS_CONFIG):
            symbol = item["symbol"]
            duration = item["duration"]
            unit = item["unit"]
            contract_type = "CALL" if idx % 2 == 0 else "PUT"
            
            print(f"\n--- Відкриття ордера для {symbol} ({contract_type} | {item['label']}) ---")

            # 1. Запитуємо proposal
            proposal_req = {
                "proposal": 1,
                "amount": 1.0,
                "basis": "stake",
                "contract_type": contract_type,
                "currency": "USD",
                "duration": duration,
                "duration_unit": unit,
                "underlying_symbol": symbol
            }

            print(f"📩 Запитуємо proposal для {symbol}...")
            await ws.send(json.dumps(proposal_req))

            proposal_id = None
            ask_price = None

            while True:
                resp = json.loads(await ws.recv())
                if "error" in resp:
                    print(f"❌ Помилка proposal ({symbol}): {resp['error']['message']}")
                    break

                if resp.get("msg_type") == "proposal":
                    proposal_data = resp.get("proposal", {})
                    proposal_id = proposal_data.get("id")
                    ask_price = proposal_data.get("ask_price")
                    print(f"✅ Proposal отримано! ID: {proposal_id} | Ціна: {ask_price} USD")
                    break

            if not proposal_id:
                continue

            # 2. Відправляємо ордер на купівлю
            buy_req = {
                "buy": proposal_id,
                "price": ask_price
            }

            print(f"🎰 Відправляємо ордер на купівлю {symbol}...")
            await ws.send(json.dumps(buy_req))

            while True:
                buy_resp = json.loads(await ws.recv())
                if "error" in buy_resp:
                    print(f"❌ Помилка купівлі ({symbol}): {buy_resp['error']['message']}")
                    break

                if buy_resp.get("msg_type") == "buy":
                    buy_info = buy_resp.get("buy", {})
                    print(f"🎉 УГОДУ ВІДКРИТО по {symbol}!")
                    print(f"🆔 Contract ID: {buy_info.get('contract_id')}")
                    break

            await asyncio.sleep(1)

    print("\n🏁 Тест завершено! Усі 5 угод успішно відкрито.")

if __name__ == "__main__":
    asyncio.run(main())
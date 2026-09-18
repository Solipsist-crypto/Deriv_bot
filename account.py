# account.py

import requests
from config import PAT_TOKEN, APP_ID, BASE_URL

class AccountManager:
    def __init__(self):
        self.account_id = None
        self.balance = 0.0
        self.currency = ""
        self.headers = {
            "Authorization": f"Bearer {PAT_TOKEN}",
            "Deriv-App-ID": APP_ID
        }

    def connect(self) -> bool:
        """Авторизується та завантажує дані про акаунт."""
        try:
            response = requests.get(f"{BASE_URL}/accounts", headers=self.headers, timeout=10)
            if response.status_code == 200:
                accounts = response.json().get("data", [])
                if accounts:
                    demo_acc = accounts[0]
                    self.account_id = demo_acc["account_id"]
                    self.balance = float(demo_acc["balance"])
                    self.currency = demo_acc["currency"]
                    
                    print(f"✅ [AccountManager] Авторизовано: {self.account_id}")
                    print(f"💰 [AccountManager] Баланс: {self.balance} {self.currency}")
                    return True
            print(f"❌ [AccountManager] Помилка запиту: {response.status_code}")
        except Exception as e:
            print(f"❌ [AccountManager] Помилка підключення: {e}")
        return False

    def get_otp_url(self) -> str:
        """Отримує WebSocket URL для подальших дій."""
        if not self.account_id:
            return None
        try:
            res = requests.post(f"{BASE_URL}/accounts/{self.account_id}/otp", headers=self.headers, timeout=10)
            if res.status_code in (200, 201):
                data = res.json().get("data", {})
                return data.get("websocket_url") or data.get("url")
        except Exception as e:
            print(f"❌ [AccountManager] Помилка отримання OTP: {e}")
        return None
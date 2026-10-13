import os
import joblib
import pandas as pd
from datetime import datetime, timezone

class MLFilter:
    def __init__(self, model_path="xgb_model.pkl", features_path="model_features.pkl", min_win_probability=0.55):
        self.min_win_probability = min_win_probability
        self.model = None
        self.feature_cols = []
        
        if os.path.exists(model_path) and os.path.exists(features_path):
            try:
                self.model = joblib.load(model_path)
                self.feature_cols = joblib.load(features_path)
                print(f"🤖 [MLFilter] Модель XGBoost успішно завантажена (Поріг: {self.min_win_probability * 100}%).")
            except Exception as e:
                print(f"⚠️ [MLFilter] Помилка завантаження моделі: {e}. Працюємо без ML.")
        else:
            print("⚠️ [MLFilter] Файли моделі не знайдені. ML-фільтрація вимкнена.")

    def should_trade(self, analysis: dict) -> tuple[bool, float]:
        """
        Приймає dict аналізу, розраховує фічі та повертає:
        (bool_pass, probability)
        """
        if not self.model or not self.feature_cols:
            return True, 1.0  # Якщо моделі немає, пропускаємо за замовчуванням

        try:
            now = datetime.now(timezone.utc)
            
            # Базовий словник для вибірки
            row_data = {
                'close_price': float(analysis.get('close_price', 0.0)),
                'rsi': float(analysis.get('rsi', 0.0) or 0.0),
                'buy_votes': int(analysis.get('buy_votes', 0)),
                'sell_votes': int(analysis.get('sell_votes', 0)),
                'hour': now.hour,
                'dayofweek': now.weekday(),
                'is_rsi_extreme': 1 if (float(analysis.get('rsi', 50)) < 30 or float(analysis.get('rsi', 50)) > 70) else 0,
            }

            # Значення для categorical one-hot
            symbol = analysis.get('symbol', '')
            rsi_signal = analysis.get('rsi_signal', 'NEUTRAL')
            ema_signal = analysis.get('ema_signal', 'NEUTRAL')
            bb_signal = analysis.get('bb_signal', 'NEUTRAL')
            signal = analysis.get('signal', 'WAIT')

            # Заповнюємо всі потрібні фічі колонок моделі
            feature_dict = {}
            for col in self.feature_cols:
                if col in row_data:
                    feature_dict[col] = row_data[col]
                elif col == f"symbol_{symbol}":
                    feature_dict[col] = 1
                elif col == f"rsi_signal_{rsi_signal}":
                    feature_dict[col] = 1
                elif col == f"ema_signal_{ema_signal}":
                    feature_dict[col] = 1
                elif col == f"bb_signal_{bb_signal}":
                    feature_dict[col] = 1
                elif col == f"signal_{signal}":
                    feature_dict[col] = 1
                else:
                    feature_dict[col] = 0

            X_single = pd.DataFrame([feature_dict])[self.feature_cols]

            # Отримуємо ймовірність перемоги (клас 1)
            prob_win = float(self.model.predict_proba(X_single)[0][1])

            is_approved = prob_win >= self.min_win_probability
            print(f"🤖 [MLFilter] {symbol} ({signal}) | Прогноз перемоги: {prob_win:.1%} | Схвалено: {is_approved}")

            return is_approved, prob_win

        except Exception as e:
            print(f"❌ [MLFilter] Помилка прогнозування: {e}")
            return True, 0.5
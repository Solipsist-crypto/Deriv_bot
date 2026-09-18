import pandas as pd
import ta.momentum
import ta.trend
import ta.volatility

class MultiIndicatorStrategy:
    def __init__(self, rsi_period=14, ema_fast=20, ema_slow=50, bb_length=20, bb_std=2.0):
        self.rsi_period = rsi_period
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.bb_length = bb_length
        self.bb_std = bb_std

    def analyze(self, candles: list) -> dict:
        if len(candles) < self.ema_slow + 1:
            print("⚠️ [Strategy] Занадто мало свічок для розрахунку")
            return {"signal": "WAIT", "rsi": None, "ema_signal": None, "bb_signal": None}

        # Конвертуємо у датафрейм
        df = pd.DataFrame(candles)
        
        # 1. RSI
        df['rsi'] = ta.momentum.rsi(df['close'], window=self.rsi_period)
        
        # 2. EMA Cross (20 і 50)
        df['ema_fast'] = ta.trend.ema_indicator(df['close'], window=self.ema_fast)
        df['ema_slow'] = ta.trend.ema_indicator(df['close'], window=self.ema_slow)
        
        # 3. Bollinger Bands
        bb_indicator = ta.volatility.BollingerBands(df['close'], window=self.bb_length, window_dev=self.bb_std)
        df['bb_lower'] = bb_indicator.bollinger_lband()
        df['bb_upper'] = bb_indicator.bollinger_hband()

        # Останні значення
        last = df.iloc[-1]

        # Сигнали індикаторів
        rsi_sig = "BUY" if last['rsi'] <= 35 else ("SELL" if last['rsi'] >= 65 else "NEUTRAL")
        ema_sig = "BUY" if last['ema_fast'] > last['ema_slow'] else "SELL"
        bb_sig = "BUY" if last['close'] <= last['bb_lower'] else ("SELL" if last['close'] >= last['bb_upper'] else "NEUTRAL")

        # Підрахунок голосів
        buy_votes = [rsi_sig, ema_sig, bb_sig].count("BUY")
        sell_votes = [rsi_sig, ema_sig, bb_sig].count("SELL")

        final_signal = "WAIT"
        if buy_votes >= 2:
            final_signal = "BUY"
        elif sell_votes >= 2:
            final_signal = "SELL"

        return {
            "signal": final_signal,
            "rsi": round(last['rsi'], 2),
            "rsi_signal": rsi_sig,
            "ema_signal": ema_sig,
            "bb_signal": bb_sig,
            "buy_votes": buy_votes,
            "sell_votes": sell_votes,
            "close_price": last['close']
        }
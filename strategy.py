import pandas as pd
import numpy as np
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
            return {"signal": "WAIT", "rsi": None, "ema_signal": None, "bb_signal": None, "macd_signal": None}

        df = pd.DataFrame(candles)

        # 1. RSI
        df['rsi'] = ta.momentum.rsi(df['close'], window=self.rsi_period)
        
        # 2. EMA
        df['ema_fast'] = ta.trend.ema_indicator(df['close'], window=self.ema_fast)
        df['ema_slow'] = ta.trend.ema_indicator(df['close'], window=self.ema_slow)
        
        # 3. Bollinger Bands
        bb_indicator = ta.volatility.BollingerBands(df['close'], window=self.bb_length, window_dev=self.bb_std)
        df['bb_upper'] = bb_indicator.bollinger_hband()
        df['bb_lower'] = bb_indicator.bollinger_lband()
        
        # 4. MACD
        macd_indicator = ta.trend.MACD(df['close'])
        df['macd_line'] = macd_indicator.macd()
        df['macd_signal_line'] = macd_indicator.macd_signal()
        df['macd_hist'] = macd_indicator.macd_diff()

        # 5. ATR (Волатильність)
        df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
        
        # 6. ADX (Сила тренду - захист від флєту)
        df['adx'] = ta.trend.adx(df['high'], df['low'], df['close'], window=14)

        last = df.iloc[-1]

        # --- Дискретні сигнали ---
        rsi_sig = "BUY" if last['rsi'] <= 35 else ("SELL" if last['rsi'] >= 65 else "NEUTRAL")
        ema_sig = "BUY" if last['ema_fast'] > last['ema_slow'] else "SELL"
        macd_sig = "BUY" if last['macd_line'] > last['macd_signal_line'] else "SELL"
        bb_sig = "BUY" if last['close'] <= last['bb_lower'] else ("SELL" if last['close'] >= last['bb_upper'] else "NEUTRAL")

        # --- Підрахунок голосів ---
        buy_votes = [rsi_sig, ema_sig, macd_sig, bb_sig].count("BUY")
        sell_votes = [rsi_sig, ema_sig, macd_sig, bb_sig].count("SELL")

        final_signal = "WAIT"
        if buy_votes >= 2:
            final_signal = "BUY"
        elif sell_votes >= 2:
            final_signal = "SELL"

        # --- Нові фічі для ML ---
        ema_slow_val = last['ema_slow'] if pd.notna(last['ema_slow']) else last['close']
        bb_upper_val = last['bb_upper'] if pd.notna(last['bb_upper']) else last['close']
        bb_lower_val = last['bb_lower'] if pd.notna(last['bb_lower']) else last['close']
        
        ema_distance_pct = abs(last['close'] - ema_slow_val) / last['close'] if last['close'] > 0 else 0.0
        bb_width = (bb_upper_val - bb_lower_val) / last['close'] if last['close'] > 0 else 0.0
        
        bb_range = bb_upper_val - bb_lower_val
        bb_position = (last['close'] - bb_lower_val) / bb_range if bb_range > 0 else 0.5
        
        rsi_slope = last['rsi'] - df['rsi'].iloc[-4] if len(df) >= 4 and pd.notna(df['rsi'].iloc[-4]) else 0.0
        
        # ATR Percentile (відносно останніх 100 свічок)
        recent_atr = df['atr'].dropna().tail(100)
        atr_percentile = (recent_atr < last['atr']).mean() if len(recent_atr) > 0 and pd.notna(last['atr']) else 0.5
        
        current_adx = float(last['adx']) if pd.notna(last['adx']) else 0.0

        # 🔴 ФІЛЬТР 1: ANTI-CHASE (не входимо, якщо ціна вже далеко від EMA50)
        if final_signal == "BUY" and ema_distance_pct > 0.005:
            final_signal = "WAIT"
        if final_signal == "SELL" and ema_distance_pct > 0.005:
            final_signal = "WAIT"
            
        # 🔴 ФІЛЬТР 2: ADX (не торгуємо у флєті)
        if current_adx < 20.0:
            final_signal = "WAIT"

        return {
            "signal": final_signal,
            "close_price": float(last['close']),
            "rsi": float(last['rsi']) if pd.notna(last['rsi']) else 50.0,
            "ema_fast": float(last['ema_fast']) if pd.notna(last['ema_fast']) else 0.0,
            "ema_slow": float(last['ema_slow']) if pd.notna(last['ema_slow']) else 0.0,
            "macd_line": float(last['macd_line']) if pd.notna(last['macd_line']) else 0.0,
            "macd_signal_line": float(last['macd_signal_line']) if pd.notna(last['macd_signal_line']) else 0.0,
            "macd_hist": float(last['macd_hist']) if pd.notna(last['macd_hist']) else 0.0,
            "bb_upper": float(last['bb_upper']) if pd.notna(last['bb_upper']) else 0.0,
            "bb_lower": float(last['bb_lower']) if pd.notna(last['bb_lower']) else 0.0,
            "atr": float(last['atr']) if pd.notna(last['atr']) else 0.0,
            "adx": current_adx,
            
            # Нові фічі
            "ema_distance_pct": float(ema_distance_pct),
            "bb_width": float(bb_width),
            "bb_position": float(bb_position),
            "rsi_slope": float(rsi_slope),
            "atr_percentile": float(atr_percentile),
            
            # Дискретні сигнали
            "rsi_signal": rsi_sig,
            "ema_signal": ema_sig,
            "macd_signal": macd_sig,
            "bb_signal": bb_sig,
            "buy_votes": buy_votes,
            "sell_votes": sell_votes,
        }
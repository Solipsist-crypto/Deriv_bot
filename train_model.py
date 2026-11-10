import pandas as pd
import numpy as np
import joblib
from xgboost import XGBClassifier
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import roc_auc_score

def train_and_save():
    df = pd.read_csv("trades_dataset.csv")
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    df['hour'] = df['timestamp'].dt.hour
    df['dayofweek'] = df['timestamp'].dt.dayofweek
    df['is_rsi_extreme'] = ((df['rsi'] < 30) | (df['rsi'] > 70)).astype(int)

    # One-hot encoding (БЕЗ signal, щоб не було leakage)
    categorical_cols = ['symbol', 'rsi_signal', 'ema_signal', 'macd_signal', 'bb_signal']
    df_encoded = pd.get_dummies(df, columns=categorical_cols, drop_first=False)

    ignore_cols = ['id', 'timestamp', 'contract_id', 'stake', 'profit', 'win', 'signal', 'macd', 'rsi_signal', 'ema_signal', 'bb_signal', 'macd_signal']
    feature_cols = [c for c in df_encoded.columns if c not in ignore_cols]

    X = df_encoded[feature_cols]
    y = df_encoded['win']

    # Часовий спліт (80/20)
    split_idx = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    # Балансування ваг
    weights = compute_class_weight('balanced', classes=np.unique(y_train), y=y_train)
    spw = weights[1] / weights[0]

    model = XGBClassifier(
        n_estimators=500, max_depth=3, learning_rate=0.03, subsample=0.8,
        colsample_bytree=0.8, scale_pos_weight=spw, early_stopping_rounds=40,
        eval_metric='auc', random_state=42
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    y_prob = model.predict_proba(X_test)[:, 1]
    print(f"ROC-AUC: {roc_auc_score(y_test, y_prob):.3f}")

    # Підбір порогу за EV (Очікуваний Прибуток)
    stake, win_payout = 5.0, 3.5
    best_thresh, best_ev = 0.5, -999
    for t in np.arange(0.40, 0.90, 0.02):
        approved = y_prob >= t
        if approved.sum() < 10: continue
        wr = y_test[approved].mean()
        ev = wr * win_payout - (1 - wr) * stake
        if ev > best_ev:
            best_ev, best_thresh = ev, t
            
    print(f"Оптимальний поріг: {best_thresh:.2f} (EV={best_ev:.2f})")

    joblib.dump(model, "xgb_model.pkl")
    joblib.dump(feature_cols, "model_features.pkl")
    joblib.dump(best_thresh, "best_threshold.pkl")

if __name__ == "__main__":
    train_and_save()
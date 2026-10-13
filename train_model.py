import pandas as pd
import numpy as np
import joblib
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, classification_report

def train_and_save():
    print("📊 Завантажуємо датасет угод...")
    df = pd.read_csv("trades_dataset.csv")

    # 1. Feature Engineering
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp'].dt.hour
    df['dayofweek'] = df['timestamp'].dt.dayofweek
    df['is_rsi_extreme'] = ((df['rsi'] < 30) | (df['rsi'] > 70)).astype(int)

    # One-hot encoding для категоріальних фічей
    categorical_cols = ['symbol', 'rsi_signal', 'ema_signal', 'bb_signal', 'signal']
    df_encoded = pd.get_dummies(df, columns=categorical_cols, drop_first=False)

    # Виключаємо службові колонки
    ignore_cols = ['id', 'timestamp', 'contract_id', 'stake', 'profit', 'win']
    feature_cols = [c for c in df_encoded.columns if c not in ignore_cols]

    X = df_encoded[feature_cols]
    y = df_encoded['win']

    # Поділ даних 80/20
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # 2. Навчання XGBoost
    print("🧠 Навчаємо XGBoostClassifier...")
    model = XGBClassifier(
        n_estimators=70,
        max_depth=3,
        learning_rate=0.04,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42
    )
    model.fit(X_train, y_train)

    # 3. Оцінка точності
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)

    print(f"✅ Модель навчено!")
    print(f"📈 Accuracy на тесті: {acc:.2%}")
    print(f"🎯 Precision (Win Rate прогнозів): {prec:.2%}")

    # 4. Збереження моделі та списку колонкок
    joblib.dump(model, "xgb_model.pkl")
    joblib.dump(feature_cols, "model_features.pkl")
    print("💾 Файли 'xgb_model.pkl' та 'model_features.pkl' успішно збережено!")

if __name__ == "__main__":
    train_and_save()
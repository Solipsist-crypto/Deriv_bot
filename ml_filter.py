class MLFilter:
    def __init__(self, model_path="xgb_model.pkl", features_path="model_features.pkl", min_win_probability=0.55):
        # Конструктор залишено порожнім, щоб main.py міг створити об'єкт без помилок.
        # Стара ML-модель v2 не завантажується.
        print("🧠 [MLFilter] ТИМЧАСОВО ВИМКНЕНО. Працюємо в режимі збору даних для ML v3.")

    def should_trade(self, analysis: dict) -> tuple[bool, float]:
        # Завжди повертаємо True (дозволяємо вхід) та 1.0 (100% умовна ймовірність).
        # Це дозволяє main.py безперешкодно відкривати угоди за стратегією.
        return True, 1.0
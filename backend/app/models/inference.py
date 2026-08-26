import json
from functools import lru_cache
from pathlib import Path

import pandas as pd
from xgboost import XGBClassifier

# 이 파일 위치: backend/app/models/inference.py
# ml_artifacts 위치: backend/ml_artifacts
ARTIFACTS_DIR = Path(__file__).resolve().parent.parent.parent / "ml_artifacts"


@lru_cache(maxsize=None)
def load_region_artifacts(region_en: str):
    """지역별 모델/클래스/피처 컬럼을 최초 1회만 로드하고 캐시합니다."""
    region_dir = ARTIFACTS_DIR / region_en
    model_path = region_dir / "model.json"
    classes_path = region_dir / "classes.json"
    columns_path = region_dir / "train_columns.json"

    if not model_path.exists():
        raise FileNotFoundError(f"모델 파일 없음: {model_path}")

    model = XGBClassifier()
    model.load_model(str(model_path))
    classes = json.loads(classes_path.read_text(encoding="utf-8"))
    train_columns = json.loads(columns_path.read_text(encoding="utf-8"))
    return model, classes, train_columns


def build_input_row(weather_features: dict, user_inputs: dict, train_columns: list) -> pd.DataFrame:
    """기상 데이터와 사용자 입력을 모델 입력 형식(원-핫 인코딩된 컬럼)으로 변환합니다."""
    row = {col: 0 for col in train_columns}

    for key, value in weather_features.items():
        if key in row:
            row[key] = value

    for feature_name, selected_value in user_inputs.items():
        matched_col = f"{feature_name}_{selected_value}"
        if matched_col in row:
            row[matched_col] = 1

    return pd.DataFrame([row])[train_columns]


def predict(region_en: str, weather_features: dict, user_inputs: dict) -> tuple[str, float]:
    model, classes, train_columns = load_region_artifacts(region_en)
    input_df = build_input_row(weather_features, user_inputs, train_columns)

    pred_idx = int(model.predict(input_df)[0])
    proba = model.predict_proba(input_df)[0]
    confidence = float(proba[pred_idx])
    predicted_type = classes[pred_idx]

    return predicted_type, confidence

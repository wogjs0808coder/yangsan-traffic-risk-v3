import json
from functools import lru_cache
from pathlib import Path

import pandas as pd
from xgboost import XGBClassifier

# 이 파일 위치: backend/app/models/inference.py
# ml_artifacts 위치: backend/ml_artifacts
ARTIFACTS_DIR = Path(__file__).resolve().parent.parent.parent / "ml_artifacts"

# V2 to_model_features()가 생성하는 수치형 컬럼명 (밑줄 포함된 것도 있어
# 단순히 "_ 유무"로는 범주형과 구분할 수 없어 화이트리스트로 명시)
KNOWN_NUMERIC_COLUMNS = {
    "평균기온(°C)",
    "일강수량_클립(mm)",
    "평균 풍속(m/s)",
    "평균 상대습도(%)",
    "폭우_여부_플래그",
}

# train_region_model.py의 CATEGORICAL_FEATURES와 동일 — 2단어 프리픽스(road_condition 등)를
# 첫 "_"에서 잘못 자르지 않도록 전체 프리픽스로 매칭한다
CATEGORICAL_FEATURE_NAMES = ["주야", "weather", "road_condition", "vehicle_type", "age_group", "season"]


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


def get_region_schema(region_en: str) -> dict:
    """
    train_columns를 파싱해 프론트엔드가 입력 폼을 자동 생성할 수 있게 해줍니다.

    - KNOWN_NUMERIC_COLUMNS에 있으면 수치형 (밑줄 포함 여부와 무관)
    - CATEGORICAL_FEATURE_NAMES와 전체 프리픽스로 일치하면 그 이름으로 그룹핑
      (예: 'road_condition_건조' -> {"road_condition": ["건조", ...]})
    - 그 외 '_'가 있으면 첫 '_' 기준 fallback 그룹핑
    - 그 외 수치형으로 취급 (미지의 수치형 컬럼 대비 fallback)
    """
    _, _, train_columns = load_region_artifacts(region_en)

    categorical_options: dict[str, list[str]] = {}
    numeric_features: list[str] = []

    for col in train_columns:
        if col in KNOWN_NUMERIC_COLUMNS:
            numeric_features.append(col)
            continue

        matched_feature = next((f for f in CATEGORICAL_FEATURE_NAMES if col.startswith(f + "_")), None)
        if matched_feature:
            value = col[len(matched_feature) + 1:]
            categorical_options.setdefault(matched_feature, []).append(value)
        elif "_" in col:
            prefix, _, value = col.partition("_")
            categorical_options.setdefault(prefix, []).append(value)
        else:
            numeric_features.append(col)

    return {
        "numeric_features": numeric_features,
        "categorical_options": categorical_options,
    }

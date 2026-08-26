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
    - 그 외 '_'가 있으면 원-핫 인코딩된 범주형으로 간주 (예: '가해운전자 차종_이륜차')
      -> {"가해운전자 차종": ["이륜차", "승용차", ...]} 형태로 그룹핑
    - 그 외 '_' 없으면 수치형으로 취급 (미지의 수치형 컬럼 대비 fallback)
    """
    _, _, train_columns = load_region_artifacts(region_en)

    categorical_options: dict[str, list[str]] = {}
    numeric_features: list[str] = []

    for col in train_columns:
        if col in KNOWN_NUMERIC_COLUMNS:
            numeric_features.append(col)
        elif "_" in col:
            prefix, _, value = col.partition("_")
            categorical_options.setdefault(prefix, []).append(value)
        else:
            numeric_features.append(col)

    return {
        "numeric_features": numeric_features,
        "categorical_options": categorical_options,
    }

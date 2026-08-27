"""
실제 사고 데이터(215,220건) + 월별 집계 기상 데이터로 지역별 XGBoost 모델을 재학습합니다.
V2와 동일한 방식(지역별 개별 모델, 사고유형 분류)을 따르되, 이번엔 mock이 아닌 실데이터를 사용합니다.

사전 조건:
    - db/scripts/combine_real_accidents.py 실행 완료 (ml/data/real/accidents_real.parquet)
    - db/scripts/aggregate_weather_monthly.py 실행 완료 (ml/data/real/weather_monthly.parquet)

출력 (지역별로 backend/ml_artifacts/{region}/ 에 저장 — 기존 V2 이관 모델을 대체):
    - model.json
    - classes.json
    - train_columns.json
그리고 전체 지역 성능 요약: docs/performance/retrain-real-data-summary.csv
"""

import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

ACCIDENTS_PATH = Path("ml/data/real/accidents_real.parquet")
WEATHER_PATH = Path("ml/data/real/weather_monthly.parquet")
ARTIFACTS_DIR = Path("backend/ml_artifacts")
SUMMARY_PATH = Path("docs/performance/retrain-real-data-summary.csv")

REGION_TO_EN = {
    "서울특별시": "seoul",
    "부산광역시": "busan",
    "대구광역시": "daegu",
    "인천광역시": "incheon",
    "대전광역시": "daejeon",
    "경상남도 양산시": "yangsan",
}

CATEGORICAL_FEATURES = ["주야", "weather", "road_condition", "vehicle_type", "age_group", "season"]
TARGET_COLUMN = "accident_type"
MIN_CLASS_SAMPLES = 5  # V2와 동일: 이보다 적은 샘플의 사고유형은 학습에서 제외


def month_to_season(month: int) -> str:
    if month in (3, 4, 5):
        return "봄"
    if month in (6, 7, 8):
        return "여름"
    if month in (9, 10, 11):
        return "가을"
    return "겨울"


def train_one_region(region_kr: str, region_en: str, merged: pd.DataFrame) -> dict:
    df = merged[merged["region"] == region_kr].copy()

    # 희귀 클래스 필터링 (K-Fold 붕괴 방지 — V2에서 겪었던 이슈와 동일한 이유)
    class_counts = df[TARGET_COLUMN].value_counts()
    valid_classes = class_counts[class_counts >= MIN_CLASS_SAMPLES].index
    dropped = len(df) - df[TARGET_COLUMN].isin(valid_classes).sum()
    df = df[df[TARGET_COLUMN].isin(valid_classes)].reset_index(drop=True)

    # 타겟 인코딩
    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(df[TARGET_COLUMN])
    classes = label_encoder.classes_.tolist()

    # 피처 구성: 범주형 원-핫 + 수치형 기상
    categorical_encoded = pd.get_dummies(df[CATEGORICAL_FEATURES], prefix_sep="_")
    numeric_cols = ["평균기온(°C)", "일강수량_클립(mm)", "평균 풍속(m/s)", "평균 상대습도(%)", "폭우_여부_플래그"]
    X = pd.concat([categorical_encoded, df[numeric_cols].reset_index(drop=True)], axis=1)
    train_columns = X.columns.tolist()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.1,
        eval_metric="mlogloss",
        random_state=42,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    weighted_f1 = f1_score(y_test, y_pred, average="weighted")

    # 저장 (backend/ml_artifacts/{region_en}/ — 기존 V2 이관 모델을 대체)
    region_dir = ARTIFACTS_DIR / region_en
    region_dir.mkdir(parents=True, exist_ok=True)

    model.save_model(str(region_dir / "model.json"))
    (region_dir / "classes.json").write_text(
        json.dumps(classes, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (region_dir / "train_columns.json").write_text(
        json.dumps(train_columns, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(
        f"✅ {region_kr} ({region_en}): 학습 {len(X_train):,} / 테스트 {len(X_test):,} "
        f"(희귀 클래스 제외 {dropped}건) -> accuracy={accuracy:.4f}, weighted_f1={weighted_f1:.4f}"
    )

    return {
        "region": region_kr,
        "region_en": region_en,
        "n_samples": len(df),
        "n_classes": len(classes),
        "n_features": len(train_columns),
        "accuracy": round(accuracy, 4),
        "weighted_f1": round(weighted_f1, 4),
    }


def main() -> None:
    accidents = pd.read_parquet(ACCIDENTS_PATH)
    weather = pd.read_parquet(WEATHER_PATH)

    accidents["accident_dt"] = pd.to_datetime(accidents["accident_dt"])
    accidents["year"] = accidents["accident_dt"].dt.year
    accidents["month"] = accidents["accident_dt"].dt.month
    accidents["season"] = accidents["month"].apply(month_to_season)

    merged = accidents.merge(weather, on=["region", "year", "month"], how="left")

    results = []
    for region_kr, region_en in REGION_TO_EN.items():
        result = train_one_region(region_kr, region_en, merged)
        results.append(result)

    summary = pd.DataFrame(results)
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(SUMMARY_PATH, index=False, encoding="utf-8-sig")

    print()
    print("📊 전체 요약")
    print(summary.to_string(index=False))
    print(f"\n✅ 요약 저장: {SUMMARY_PATH}")


if __name__ == "__main__":
    main()

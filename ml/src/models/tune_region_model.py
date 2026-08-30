import argparse
import json
from pathlib import Path

import optuna
import pandas as pd
from optuna.pruners import MedianPruner
from optuna.samplers import TPESampler
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

optuna.logging.set_verbosity(optuna.logging.WARNING)

ACCIDENTS_PATH = Path("ml/data/real/accidents_real.parquet")
WEATHER_PATH = Path("ml/data/real/weather_monthly.parquet")
TUNED_ARTIFACTS_DIR = Path("backend/ml_artifacts_tuned")
SUMMARY_PATH = Path("docs/performance/optuna-tuning-summary.csv")

REGION_TO_EN = {
    "서울특별시": "seoul",
    "부산광역시": "busan",
    "대구광역시": "daegu",
    "인천광역시": "incheon",
    "대전광역시": "daejeon",
    "경상남도 양산시": "yangsan",
}

CATEGORICAL_FEATURES = ["주야", "weather", "road_condition", "vehicle_type", "age_group", "season"]
NUMERIC_COLUMNS = ["평균기온(°C)", "일강수량_클립(mm)", "평균 풍속(m/s)", "평균 상대습도(%)", "폭우_여부_플래그"]
TARGET_COLUMN = "accident_type"
MIN_CLASS_SAMPLES = 5


def month_to_season(month: int) -> str:
    if month in (3, 4, 5):
        return "봄"
    if month in (6, 7, 8):
        return "여름"
    if month in (9, 10, 11):
        return "가을"
    return "겨울"


def build_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    categorical_encoded = pd.get_dummies(df[CATEGORICAL_FEATURES], prefix_sep="_")
    X = pd.concat([categorical_encoded, df[NUMERIC_COLUMNS].reset_index(drop=True)], axis=1)
    return X, X.columns.tolist()


def safe_n_splits(y, max_splits: int) -> int:
    # 0이면 CV 대신 holdout 사용
    min_class_count = int(pd.Series(y).value_counts().min())
    if min_class_count < 2:
        return 0
    return max(2, min(max_splits, min_class_count))


def make_objective(X_train: pd.DataFrame, y_train, cv_folds: int):
    def objective(trial: optuna.Trial) -> float:
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 100, 800),
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
            "gamma": trial.suggest_float("gamma", 1e-8, 5.0, log=True),
        }

        n_splits = safe_n_splits(y_train, cv_folds)

        if n_splits == 0:
            X_fit, X_val, y_fit, y_val = train_test_split(
                X_train, y_train, test_size=0.2, random_state=42
            )
            model = XGBClassifier(**params, eval_metric="mlogloss", random_state=42)
            model.fit(X_fit, y_fit)
            pred = model.predict(X_val)
            return f1_score(y_val, pred, average="weighted")

        skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
        fold_scores = []

        for fold_idx, (tr_idx, val_idx) in enumerate(skf.split(X_train, y_train)):
            model = XGBClassifier(**params, eval_metric="mlogloss", random_state=42)
            model.fit(X_train.iloc[tr_idx], y_train[tr_idx])
            pred = model.predict(X_train.iloc[val_idx])
            fold_scores.append(f1_score(y_train[val_idx], pred, average="weighted"))

            trial.report(sum(fold_scores) / len(fold_scores), step=fold_idx)
            if trial.should_prune():
                raise optuna.TrialPruned()

        return sum(fold_scores) / len(fold_scores)

    return objective


def tune_one_region(
    region_kr: str, region_en: str, merged: pd.DataFrame, n_trials: int, timeout: int, cv_folds: int
) -> dict:
    df = merged[merged["region"] == region_kr].copy()

    class_counts = df[TARGET_COLUMN].value_counts()
    valid_classes = class_counts[class_counts >= MIN_CLASS_SAMPLES].index
    df = df[df[TARGET_COLUMN].isin(valid_classes)].reset_index(drop=True)

    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(df[TARGET_COLUMN])
    classes = label_encoder.classes_.tolist()

    X, train_columns = build_features(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    baseline_model = XGBClassifier(
        n_estimators=300, max_depth=6, learning_rate=0.1,
        eval_metric="mlogloss", random_state=42,
    )
    baseline_model.fit(X_train, y_train)
    baseline_pred = baseline_model.predict(X_test)
    baseline_accuracy = accuracy_score(y_test, baseline_pred)
    baseline_weighted_f1 = f1_score(y_test, baseline_pred, average="weighted")

    study = optuna.create_study(
        direction="maximize",
        sampler=TPESampler(seed=42),
        pruner=MedianPruner(n_warmup_steps=1),
    )
    study.optimize(
        make_objective(X_train, y_train, cv_folds),
        n_trials=n_trials,
        timeout=timeout,
        show_progress_bar=False,
    )

    best_params = study.best_params
    tuned_model = XGBClassifier(**best_params, eval_metric="mlogloss", random_state=42)
    tuned_model.fit(X_train, y_train)
    tuned_pred = tuned_model.predict(X_test)
    tuned_accuracy = accuracy_score(y_test, tuned_pred)
    tuned_weighted_f1 = f1_score(y_test, tuned_pred, average="weighted")

    region_dir = TUNED_ARTIFACTS_DIR / region_en
    region_dir.mkdir(parents=True, exist_ok=True)
    tuned_model.save_model(str(region_dir / "model.json"))
    (region_dir / "classes.json").write_text(
        json.dumps(classes, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (region_dir / "train_columns.json").write_text(
        json.dumps(train_columns, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (region_dir / "best_params.json").write_text(
        json.dumps(best_params, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    delta_f1 = tuned_weighted_f1 - baseline_weighted_f1
    verdict = "개선" if delta_f1 > 0 else "동일/악화"

    print(
        f"{'✅' if delta_f1 > 0 else '⚠️'} {region_kr} ({region_en}): trial {len(study.trials)}회 -> "
        f"baseline weighted_f1={baseline_weighted_f1:.4f} / tuned weighted_f1={tuned_weighted_f1:.4f} "
        f"(Δ{delta_f1:+.4f}, {verdict})"
    )

    return {
        "region": region_kr,
        "region_en": region_en,
        "n_samples": len(df),
        "n_trials_run": len(study.trials),
        "baseline_accuracy": round(baseline_accuracy, 4),
        "baseline_weighted_f1": round(baseline_weighted_f1, 4),
        "tuned_accuracy": round(tuned_accuracy, 4),
        "tuned_weighted_f1": round(tuned_weighted_f1, 4),
        "delta_weighted_f1": round(delta_f1, 4),
        "best_params": json.dumps(best_params, ensure_ascii=False),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--regions", default="all", help="쉼표구분 영문 지역명 또는 all")
    parser.add_argument("--trials", type=int, default=60)
    parser.add_argument("--timeout", type=int, default=900, help="지역별 타임아웃(초)")
    parser.add_argument("--cv-folds", type=int, default=3)
    args = parser.parse_args()

    accidents = pd.read_parquet(ACCIDENTS_PATH)
    weather = pd.read_parquet(WEATHER_PATH)

    accidents["accident_dt"] = pd.to_datetime(accidents["accident_dt"])
    accidents["year"] = accidents["accident_dt"].dt.year
    accidents["month"] = accidents["accident_dt"].dt.month
    accidents["season"] = accidents["month"].apply(month_to_season)

    merged = accidents.merge(weather, on=["region", "year", "month"], how="left")

    if args.regions == "all":
        target_regions = list(REGION_TO_EN.items())
    else:
        requested = set(args.regions.split(","))
        target_regions = [(kr, en) for kr, en in REGION_TO_EN.items() if en in requested]

    results = []
    for region_kr, region_en in target_regions:
        result = tune_one_region(region_kr, region_en, merged, args.trials, args.timeout, args.cv_folds)
        results.append(result)

    summary = pd.DataFrame(results)
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)

    if SUMMARY_PATH.exists():
        existing = pd.read_csv(SUMMARY_PATH)
        existing = existing[~existing["region_en"].isin(summary["region_en"])]
        summary = pd.concat([existing, summary], ignore_index=True)

    summary.to_csv(SUMMARY_PATH, index=False, encoding="utf-8-sig")

    print()
    print("📊 튜닝 결과 요약")
    print(summary[["region", "baseline_weighted_f1", "tuned_weighted_f1", "delta_weighted_f1"]].to_string(index=False))
    print(f"\n✅ 요약 저장: {SUMMARY_PATH}")
    print(f"✅ 튜닝 모델 저장 위치: {TUNED_ARTIFACTS_DIR} (프로덕션 미반영 — 검토 후 별도 반영)")


if __name__ == "__main__":
    main()

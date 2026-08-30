import argparse
import json
import os
import shutil

import pandas as pd

REGIONS = ["seoul", "busan", "daegu", "incheon", "daejeon", "yangsan"]


def migrate(v2_path: str, v3_backend_path: str) -> None:
    for region in REGIONS:
        src_dir = os.path.join(v2_path, "data_processed", region)
        dst_dir = os.path.join(v3_backend_path, "ml_artifacts", region)

        if not os.path.isdir(src_dir):
            print(f"⚠️  건너뜀: {src_dir} 없음")
            continue

        os.makedirs(dst_dir, exist_ok=True)

        model_src = os.path.join(src_dir, "xgboost_tuned_model.json")
        shutil.copy(model_src, os.path.join(dst_dir, "model.json"))

        classes = pd.read_csv(os.path.join(src_dir, "classes.csv"))["class_name"].tolist()
        with open(os.path.join(dst_dir, "classes.json"), "w", encoding="utf-8") as f:
            json.dump(classes, f, ensure_ascii=False, indent=2)

        train_columns = pd.read_csv(os.path.join(src_dir, "X_train.csv"), nrows=0).columns.tolist()
        with open(os.path.join(dst_dir, "train_columns.json"), "w", encoding="utf-8") as f:
            json.dump(train_columns, f, ensure_ascii=False, indent=2)

        print(f"✅ {region} 이관 완료 (클래스 {len(classes)}개, 피처 {len(train_columns)}개)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--v2-path", required=True, help="V2 레포 루트 경로")
    parser.add_argument("--v3-backend-path", default="backend", help="V3 backend 폴더 경로 (기본: backend)")
    args = parser.parse_args()
    migrate(args.v2_path, args.v3_backend_path)

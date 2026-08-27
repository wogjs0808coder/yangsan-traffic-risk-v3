"""
6개 지역 실제 사고 원본 CSV를 하나로 통합해
DB 적재 및 향후 모델 재학습에 쓸 수 있는 형태로 저장합니다.

입력 파일 (ml/data/real/raw/ 안에 위치해야 함):
    accident.csv    -> 경상남도 양산시
    accident3.csv   -> 대전광역시
    accident4.csv   -> 대구광역시
    accident5.csv   -> 인천광역시
    accidentBU.csv  -> 부산광역시
    accidentSU.csv  -> 서울특별시

출력:
    ml/data/real/accidents_real.parquet
"""

import re
from pathlib import Path

import pandas as pd

RAW_DIR = Path("ml/data/real/raw")
OUTPUT_PATH = Path("ml/data/real/accidents_real.parquet")

ACCIDENT_FILES = [
    "accident.csv",
    "accident3.csv",
    "accident4.csv",
    "accident5.csv",
    "accidentBU.csv",
    "accidentSU.csv",
]

# accidents 테이블(production.sql) 컬럼과 매핑
COLUMN_RENAME = {
    "사고유형": "accident_type",
    "가해운전자 차종": "vehicle_type",
    "가해운전자 연령대": "age_group",
    "기상상태": "weather",
    "법규위반": "violation",
    "노면상태": "road_condition",
}


def normalize_region(raw: str) -> str | None:
    """'서울특별시 중구' -> '서울특별시', '경상남도 양산시 ...' -> '경상남도 양산시'"""
    raw = str(raw).strip()
    if raw.startswith("경상남도"):
        return "경상남도 양산시" if "양산시" in raw else None
    m = re.match(r"^(\S+?(?:특별시|광역시))", raw)
    return m.group(1) if m else None


def parse_year_month(raw: str) -> pd.Timestamp | None:
    """'2022년 1월' -> Timestamp('2022-01-01') (일자 정보가 없어 1일로 고정)"""
    m = re.match(r"(\d{4})년\s*(\d{1,2})월", str(raw))
    if not m:
        return None
    year, month = int(m.group(1)), int(m.group(2))
    return pd.Timestamp(year=year, month=month, day=1)


def main() -> None:
    all_dfs = []

    for fname in ACCIDENT_FILES:
        path = RAW_DIR / fname
        if not path.exists():
            print(f"⚠️  건너뜀: {path} 없음")
            continue

        df = pd.read_csv(path, encoding="utf-8-sig")
        df["region"] = df["시군구"].apply(normalize_region)
        df["accident_dt"] = df["발생년월"].apply(parse_year_month)

        before = len(df)
        df = df.dropna(subset=["region", "accident_dt"])
        dropped = before - len(df)
        if dropped:
            print(f"  ⚠️  {fname}: 지역/날짜 파싱 실패 {dropped}건 제외")

        df = df.rename(columns=COLUMN_RENAME)
        keep_cols = ["accident_dt", "region", "accident_type", "vehicle_type",
                     "age_group", "weather", "violation", "road_condition", "주야"]
        df = df[keep_cols]

        print(f"✅ {fname}: {len(df):,}건 ({df['region'].iloc[0]})")
        all_dfs.append(df)

    combined = pd.concat(all_dfs, ignore_index=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(OUTPUT_PATH, index=False)

    print()
    print(f"🔍 전체 결합: {len(combined):,}건")
    print(combined["region"].value_counts())
    print(f"✅ 저장 완료: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

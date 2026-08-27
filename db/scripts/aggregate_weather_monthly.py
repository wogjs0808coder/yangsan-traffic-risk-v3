"""
weather1/2/3.csv (2022~2024년 시간별, 전국 관측소)를 지역 x 연월 단위로 집계합니다.
사고 데이터(accidents_real.parquet)의 accident_dt(연-월 단위)와 조인하기 위한 사전 작업입니다.

출력: ml/data/real/weather_monthly.parquet
컬럼: region, year, month, 평균기온(°C), 일강수량_클립(mm), 평균 풍속(m/s), 평균 상대습도(%), 폭우_여부_플래그
"""

from pathlib import Path

import pandas as pd

RAW_DIR = Path("ml/data/real/raw")
OUTPUT_PATH = Path("ml/data/real/weather_monthly.parquet")

WEATHER_FILES = ["weather1.csv", "weather2.csv", "weather3.csv"]

# 관측소 지점명(약칭) -> accidents 테이블과 동일한 지역명
STATION_TO_REGION = {
    "서울": "서울특별시",
    "부산": "부산광역시",
    "대구": "대구광역시",
    "인천": "인천광역시",
    "대전": "대전광역시",
    "양산시": "경상남도 양산시",
}

RAIN_CLIP_MAX = 100.0
HEAVY_RAIN_THRESHOLD = 100.0  # 월 누적 강수량이 이 값을 넘으면 폭우_여부_플래그 = 1


def main() -> None:
    dfs = []
    for fname in WEATHER_FILES:
        path = RAW_DIR / fname
        if not path.exists():
            print(f"⚠️  건너뜀: {path} 없음")
            continue
        df = pd.read_csv(path, encoding="cp949")
        dfs.append(df)

    raw = pd.concat(dfs, ignore_index=True)
    raw["region"] = raw["지점명"].map(STATION_TO_REGION)
    raw = raw.dropna(subset=["region"])

    raw["강수량(mm)"] = raw["강수량(mm)"].fillna(0.0)
    raw["일시"] = pd.to_datetime(raw["일시"])
    raw["year"] = raw["일시"].dt.year
    raw["month"] = raw["일시"].dt.month

    monthly = raw.groupby(["region", "year", "month"]).agg(
        temp_mean=("기온(°C)", "mean"),
        rain_sum=("강수량(mm)", "sum"),
        wind_mean=("풍속(m/s)", "mean"),
        humidity_mean=("습도(%)", "mean"),
    ).reset_index()

    monthly["평균기온(°C)"] = monthly["temp_mean"].round(1)
    monthly["일강수량_클립(mm)"] = monthly["rain_sum"].clip(upper=RAIN_CLIP_MAX).round(1)
    monthly["평균 풍속(m/s)"] = monthly["wind_mean"].round(1)
    monthly["평균 상대습도(%)"] = monthly["humidity_mean"].round(1)
    monthly["폭우_여부_플래그"] = (monthly["rain_sum"] > HEAVY_RAIN_THRESHOLD).astype(int)

    result = monthly[[
        "region", "year", "month",
        "평균기온(°C)", "일강수량_클립(mm)", "평균 풍속(m/s)", "평균 상대습도(%)", "폭우_여부_플래그",
    ]]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(OUTPUT_PATH, index=False)

    print(f"✅ 저장 완료: {OUTPUT_PATH}")
    print(f"   지역x연월 조합 수: {len(result):,}")
    print(result.groupby("region").size())


if __name__ == "__main__":
    main()

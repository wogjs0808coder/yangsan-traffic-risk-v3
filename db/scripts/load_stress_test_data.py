"""
mock_accident_20M.parquet 를 PostgreSQL의 stress_test_accidents 테이블에 적재합니다.

방식: psycopg2 COPY (일반 INSERT보다 수십 배 빠름)
사전 조건: db/schema/stress_test.sql 로 테이블이 생성되어 있어야 합니다.

사용법:
    python db\\scripts\\load_stress_test_data.py
"""

import io
import time

import pandas as pd
import psycopg2

PARQUET_PATH = "ml/data/stress_test/mock_accident_20M.parquet"

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "traffic_risk_v3",
    "user": "postgres",
    "password": None,  # 아래에서 입력받음
}

COLUMN_MAP = {
    "사고일시": "accident_dt",
    "시군구": "region",
    "사고유형": "accident_type",
    "가해운전자 차종": "vehicle_type",
    "가해운전자 연령대": "age_group",
    "기상상태": "weather",
    "법규위반": "violation",
    "노면상태": "road_condition",
}


def load_data() -> None:
    print(f"📦 parquet 로드 중: {PARQUET_PATH}")
    df = pd.read_parquet(PARQUET_PATH)
    df = df.rename(columns=COLUMN_MAP)
    df = df[list(COLUMN_MAP.values())]
    print(f"  총 {len(df):,} 행 로드 완료")

    password = DB_CONFIG["password"] or input("PostgreSQL 'postgres' 비밀번호: ")

    conn = psycopg2.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        dbname=DB_CONFIG["dbname"],
        user=DB_CONFIG["user"],
        password=password,
    )
    cur = conn.cursor()

    print("🚀 COPY로 적재 시작...")
    start = time.time()

    buffer = io.StringIO()
    df.to_csv(buffer, index=False, header=False, sep="\t", na_rep="\\N")
    buffer.seek(0)

    cur.copy_expert(
        "COPY stress_test_accidents (accident_dt, region, accident_type, "
        "vehicle_type, age_group, weather, violation, road_condition) "
        "FROM STDIN WITH (FORMAT csv, DELIMITER E'\\t', NULL '\\N')",
        buffer,
    )
    conn.commit()

    elapsed = time.time() - start
    print(f"✅ 적재 완료: {len(df):,}행, {elapsed:.1f}초")

    cur.execute("SELECT count(*) FROM stress_test_accidents;")
    total = cur.fetchone()[0]
    print(f"🔍 테이블 확인: 현재 stress_test_accidents 총 {total:,}행")

    cur.close()
    conn.close()


if __name__ == "__main__":
    load_data()

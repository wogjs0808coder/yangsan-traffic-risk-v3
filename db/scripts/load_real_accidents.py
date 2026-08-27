"""
ml/data/real/accidents_real.parquet 를 PostgreSQL의 accidents 테이블(production)에 적재합니다.

사전 조건: db/schema/production.sql 로 테이블이 생성되어 있어야 합니다.

사용법:
    python db\\scripts\\load_real_accidents.py
"""

import io
import time

import pandas as pd
import psycopg2

PARQUET_PATH = "ml/data/real/accidents_real.parquet"

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "traffic_risk_v3",
    "user": "postgres",
    "password": None,  # 아래에서 입력받음
}

TABLE_COLUMNS = [
    "accident_dt", "region", "accident_type", "vehicle_type",
    "age_group", "weather", "violation", "road_condition",
]


def load_data() -> None:
    print(f"📦 parquet 로드 중: {PARQUET_PATH}")
    df = pd.read_parquet(PARQUET_PATH)
    df = df[TABLE_COLUMNS]
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
        f"COPY accidents ({', '.join(TABLE_COLUMNS)}) "
        "FROM STDIN WITH (FORMAT csv, DELIMITER E'\\t', NULL '\\N')",
        buffer,
    )
    conn.commit()

    elapsed = time.time() - start
    print(f"✅ 적재 완료: {len(df):,}행, {elapsed:.1f}초")

    cur.execute("SELECT region, count(*) FROM accidents GROUP BY region ORDER BY count(*) DESC;")
    print("🔍 테이블 확인 (지역별 건수):")
    for region, cnt in cur.fetchall():
        print(f"   {region}: {cnt:,}건")

    cur.close()
    conn.close()


if __name__ == "__main__":
    load_data()

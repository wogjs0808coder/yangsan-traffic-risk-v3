"""
DB 성능 테스트(스트레스 테스트) 전용 mock 데이터 생성 스크립트.

⚠️ 이 데이터는 실제 사고/기상 패턴을 반영하지 않는 완전 랜덤 데이터입니다.
   모델 학습에 사용하지 마세요. PostgreSQL 적재 및 쿼리 성능 검증 전용입니다.

출력: ml/data/stress_test/mock_accident_20M.parquet
"""

import time

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

N_TOTAL = 20_000_000
CHUNK_SIZE = 2_000_000
OUTPUT_PATH = "ml/data/stress_test/mock_accident_20M.parquet"

REGIONS = ['서울특별시', '부산광역시', '대구광역시', '인천광역시', '대전광역시', '경상남도 양산시']
ACCIDENT_TYPES = [f'유형{i}' for i in range(1, 13)]
VEHICLE_TYPES = ['승용차', '승합차', '화물차', '이륜차', '자전거', '기타']
AGE_GROUPS = ['20대', '30대', '40대', '50대', '60대 이상']
WEATHER_CONDITIONS = ['맑음', '흐림', '비', '눈']
VIOLATIONS = ['안전운전불이행', '신호위반', '중앙선침범', '과속']
ROAD_CONDITIONS = ['건조', '젖음/습기', '결빙']

START_U = pd.to_datetime('2022-01-01').value // 10**9
END_U = pd.to_datetime('2024-12-31').value // 10**9


def generate_chunk(size: int) -> pd.DataFrame:
    df = pd.DataFrame({
        '시군구': pd.Categorical(np.random.choice(REGIONS, size)),
        '사고유형': pd.Categorical(np.random.choice(ACCIDENT_TYPES, size)),
        '가해운전자 차종': pd.Categorical(np.random.choice(VEHICLE_TYPES, size)),
        '가해운전자 연령대': pd.Categorical(np.random.choice(AGE_GROUPS, size)),
        '기상상태': pd.Categorical(np.random.choice(WEATHER_CONDITIONS, size)),
        '법규위반': pd.Categorical(np.random.choice(VIOLATIONS, size)),
        '노면상태': pd.Categorical(np.random.choice(ROAD_CONDITIONS, size)),
    })
    random_u = np.random.randint(START_U, END_U, size)
    df['사고일시'] = pd.to_datetime(random_u, unit='s').strftime('%Y-%m-%d %H:00')
    return df[[
        '사고일시', '시군구', '사고유형', '가해운전자 차종',
        '가해운전자 연령대', '기상상태', '법규위반', '노면상태',
    ]]


def main() -> None:
    print(f"🚀 {N_TOTAL:,}건 생성 시작 (청크당 {CHUNK_SIZE:,}건)")
    start_time = time.time()
    writer = None
    generated = 0

    while generated < N_TOTAL:
        size = min(CHUNK_SIZE, N_TOTAL - generated)
        chunk_df = generate_chunk(size)
        table = pa.Table.from_pandas(chunk_df, preserve_index=False)

        if writer is None:
            writer = pq.ParquetWriter(OUTPUT_PATH, table.schema, compression='snappy')
        writer.write_table(table)

        generated += size
        elapsed = time.time() - start_time
        print(f"  진행: {generated:,} / {N_TOTAL:,} ({generated / N_TOTAL * 100:.1f}%) - {elapsed:.1f}초 경과")

    writer.close()
    total_elapsed = time.time() - start_time
    print(f"✅ 완료: {OUTPUT_PATH} (총 소요 시간: {total_elapsed:.1f}초)")


if __name__ == "__main__":
    main()

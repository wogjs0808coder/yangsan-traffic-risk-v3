# PostgreSQL 인덱스 성능 벤치마크 — stress_test_accidents (2,000만 건)

## 테스트 환경

- 테이블: `stress_test_accidents`
- 데이터: mock 2,000만 건 (`generate_mock_data.py`로 생성, `COPY` 방식 72.1초 적재)
- PostgreSQL 18, Windows 로컬 환경
- 측정 방식: `EXPLAIN ANALYZE`

## 결과 요약

| # | 쿼리 조건 | 인덱스 상태 | Scan 방식 | Execution Time |
|---|---|---|---|---|
| 1 | `region = '서울특별시'` (전체의 ~17%) | 없음 | Parallel Seq Scan | 520.164 ms |
| 2 | `region = '서울특별시'` (동일) | 단일 인덱스 (`region`) | Parallel Bitmap Heap Scan | 724.129 ms |
| 3 | `region + accident_type + vehicle_type` (전체의 ~0.2%) | 단일 인덱스 (`region`) | Parallel Seq Scan | 529.743 ms |
| 4 | `region + accident_type + vehicle_type` (동일) | 복합 인덱스 (`region, accident_type, vehicle_type`) | Bitmap Heap Scan | **165.956 ms** |

## 핵심 인사이트

### 1. 인덱스가 항상 빠른 게 아니다 (#1 vs #2)
`region` 조건 하나만으로는 전체 2,000만 건 중 약 333만 건(17%)이 걸립니다. 이렇게 **선택도가 낮은(대량을 골라내는) 쿼리**에서는 인덱스를 통해 흩어진 디스크 블록을 랜덤 접근하는 비용이, 처음부터 순서대로 훑는 Seq Scan보다 오히려 더 큽니다. 실제로 인덱스 적용 후 오히려 39% 느려졌습니다(520ms → 724ms).

실행 계획에도 `lossy` 힙 블록(재확인이 필요한 블록)이 다수 발생한 게 보이는데, 이는 비트맵 생성에 필요한 작업 메모리(`work_mem`)가 대량의 매칭 행을 감당하지 못해 정밀도를 낮춘 결과입니다.

### 2. 캐시는 테이블 규모에 따라 한계가 있다 (#2 재실행)
같은 쿼리를 캐시가 데워진 상태에서 다시 실행해도 속도 개선이 거의 없었습니다(724ms → 728ms). `shared_buffers` 기본값(128MB)이 2,000만 건 테이블 크기보다 훨씬 작아, 매 쿼리마다 대부분 디스크에서 새로 읽어오기 때문입니다. 대용량 테이블에서는 캐시 크기 튜닝이 별도로 필요함을 확인했습니다.

### 3. 단일 컬럼 인덱스는 다중 조건 쿼리에 무용하다 (#3)
3개 컬럼을 동시에 필터링하는 쿼리에서, `region` 단일 인덱스는 옵티마이저에게 선택되지 않았습니다(Seq Scan 유지). 인덱스를 타도 어차피 나머지 조건을 다시 걸러야 해서 이득이 없다고 판단한 것입니다.

### 4. 쿼리 패턴에 맞춘 복합 인덱스가 정답 (#4)
실제 쿼리가 사용하는 컬럼 조합(`region, accident_type, vehicle_type`) 그대로 복합 인덱스를 만들자, 선택도가 낮은(0.2%) 쿼리에서 **Execution Time이 529.7ms → 165.956ms로 3.2배 개선**되었고, Scan 방식도 `Seq Scan` → `Bitmap Index Scan`으로 바뀌었습니다. 병렬 워커 없이도 처리될 만큼 비용이 낮아졌습니다.

## 결론 및 실서비스 적용 방향

- 인덱스는 "걸면 무조건 빠르다"가 아니라 **쿼리의 선택도와 컬럼 조합에 맞춰 설계**해야 효과가 있다.
- V3 백엔드(`/predict`, `/regions` API)가 실제로 어떤 조건으로 `accidents` 테이블을 조회할지 먼저 정의한 뒤, 그 조합에 맞는 복합 인덱스를 `production.sql`에도 반영할 것.
- 대용량 조회가 잦다면 `shared_buffers` 등 PostgreSQL 설정 튜닝도 함께 고려.

## 관련 파일

- `db/scripts/generate_mock_data.py` — mock 데이터 생성
- `db/scripts/load_stress_test_data.py` — parquet → PostgreSQL 적재
- `db/scripts/benchmark_query.sql` — 케이스 #1
- `db/scripts/benchmark_query_warm.sql` — 케이스 #2 (캐시 웜업)
- `db/scripts/benchmark_query_narrow.sql` — 케이스 #3
- `db/scripts/benchmark_query_composite.sql` — 케이스 #4 (복합 인덱스 생성 포함)

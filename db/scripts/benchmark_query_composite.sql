-- region + accident_type + vehicle_type 복합 인덱스 생성 후 좁은 쿼리 재측정
CREATE INDEX IF NOT EXISTS idx_stress_composite
    ON stress_test_accidents (region, accident_type, vehicle_type);

EXPLAIN ANALYZE
SELECT * FROM stress_test_accidents
WHERE region = '서울특별시'
  AND accident_type = '유형1'
  AND vehicle_type = '이륜차';

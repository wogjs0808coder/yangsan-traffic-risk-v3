-- 캐시가 이미 데워진 상태에서 같은 쿼리 재측정 (인덱스 있음)
EXPLAIN ANALYZE
SELECT * FROM stress_test_accidents
WHERE region = '서울특별시';

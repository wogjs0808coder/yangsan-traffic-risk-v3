-- 선택도가 훨씬 낮은(좁게 골라내는) 쿼리 — 인덱스 효과가 뚜렷하게 나오는지 확인
-- 지역(1/6) x 사고유형(1/12) x 차종(1/6) 교차 조건 -> 이론상 전체의 약 0.23%
EXPLAIN ANALYZE
SELECT * FROM stress_test_accidents
WHERE region = '서울특별시'
  AND accident_type = '유형1'
  AND vehicle_type = '이륜차';

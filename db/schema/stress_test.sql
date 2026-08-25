-- ============================================
-- Stress Test 스키마 (DB 성능 검증 전용)
-- ⚠️ mock 데이터만 적재합니다. 모델 학습/서비스 로직에서 사용 금지.
-- ============================================

CREATE TABLE IF NOT EXISTS stress_test_accidents (
    id              BIGSERIAL PRIMARY KEY,
    accident_dt     TIMESTAMP NOT NULL,
    region          VARCHAR(30) NOT NULL,
    accident_type   VARCHAR(30) NOT NULL,
    vehicle_type    VARCHAR(20),
    age_group       VARCHAR(20),
    weather         VARCHAR(20),
    violation       VARCHAR(30),
    road_condition  VARCHAR(20)
);

-- 인덱스는 일부러 바로 안 걸어둡니다.
-- "인덱스 없이 2000만 건 조회" vs "인덱스 건 후 조회" 속도 비교가
-- 성능 벤치마크 기록(docs/performance/db-stress-test.md)의 핵심 포인트입니다.
-- 벤치마크 진행 시 아래 인덱스를 그때 가서 생성합니다:
--
-- CREATE INDEX idx_stress_region ON stress_test_accidents (region);
-- CREATE INDEX idx_stress_dt ON stress_test_accidents (accident_dt);

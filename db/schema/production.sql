-- ============================================
-- Production 스키마 (실서비스용)
-- 실제 공공데이터(ml/data/real/) 기반으로 채워지며,
-- FastAPI 백엔드가 조회/기록하는 테이블입니다.
-- ============================================

CREATE TABLE IF NOT EXISTS accidents (
    id              BIGSERIAL PRIMARY KEY,
    accident_dt     TIMESTAMP NOT NULL,
    region          VARCHAR(30) NOT NULL,
    accident_type   VARCHAR(30) NOT NULL,
    vehicle_type    VARCHAR(20),
    age_group       VARCHAR(20),
    weather         VARCHAR(20),
    violation       VARCHAR(30),
    road_condition  VARCHAR(20),
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_accidents_region ON accidents (region);
CREATE INDEX IF NOT EXISTS idx_accidents_dt ON accidents (accident_dt);

CREATE TABLE IF NOT EXISTS model_metadata (
    id              BIGSERIAL PRIMARY KEY,
    region          VARCHAR(30) NOT NULL,
    model_version   VARCHAR(20) NOT NULL,
    algorithm       VARCHAR(30) NOT NULL,       -- 예: RandomForest, XGBoost
    weighted_f1     NUMERIC(5,4),
    trained_at      TIMESTAMP NOT NULL DEFAULT now(),
    artifact_path   VARCHAR(255) NOT NULL       -- backend/ml_artifacts/ 내 경로
);

CREATE TABLE IF NOT EXISTS prediction_logs (
    id              BIGSERIAL PRIMARY KEY,
    region          VARCHAR(30) NOT NULL,
    request_payload JSONB NOT NULL,
    predicted_type  VARCHAR(30),
    confidence      NUMERIC(5,4),
    requested_at    TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_prediction_logs_region ON prediction_logs (region);
CREATE INDEX IF NOT EXISTS idx_prediction_logs_dt ON prediction_logs (requested_at);

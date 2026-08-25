# 양산시 교통사고 예측 — V3

V2(모놀리식 Streamlit)에서 3-Tier 아키텍처(PostgreSQL + FastAPI + Streamlit)로 전환하는 버전입니다.

## 구조

```
backend/    FastAPI + PostgreSQL 연동 — 모델 추론 전담
frontend/   Streamlit — API 호출 및 렌더링만 담당
ml/         학습 파이프라인 (V2 계승) + 데이터
  data/real/          실제 공공데이터 (모델 학습용)
  data/stress_test/   mock 대량 데이터 (DB 성능 테스트 전용, 모델 학습에 사용 금지)
db/         PostgreSQL 스키마 및 데이터 적재 스크립트
docs/       설계 문서, 성능 벤치마크 기록
```

## 로컬 실행

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

(백엔드/프론트/DB 실행 방법은 각 단계 진행하며 추가 예정)

## 데이터 출처 구분

- `ml/data/real/` : TAAS 교통사고분석시스템, 기상자료개방포털 등 실제 공공데이터
- `ml/data/stress_test/` : `db/scripts/generate_mock_data.py`로 생성한 가짜 대량 데이터. **모델 학습에 절대 사용하지 않음** — PostgreSQL 적재·쿼리 성능 테스트 전용.

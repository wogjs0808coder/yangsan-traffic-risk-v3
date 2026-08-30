# 양산시 교통사고 예측 — V3

V2(모놀리식 Streamlit)에서 3-Tier 아키텍처(PostgreSQL + FastAPI + Streamlit)로 전환한 버전임.

마이그레이션 상세 기록: [노션 - V3 마이그레이션](https://app.notion.com/p/V3-3c9294bdb6c580b7a8b3c2a5124359ec?source=copy_link)

## 구조

```
backend/    FastAPI + PostgreSQL 연동 — 모델 추론 전담
frontend/   Streamlit — API 호출 및 렌더링만 담당
ml/         학습 파이프라인 (V2 계승) + 데이터
  data/real/          실제 공공데이터 (모델 학습용)
  data/stress_test/   mock 대량 데이터 (DB 성능 테스트 전용, 모델 학습에 사용 금지)
db/         PostgreSQL 스키마 및 데이터 적재 스크립트
docs/       설계 문서, 성능 벤치마크, 트러블슈팅 기록
```

## 로컬 실행

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

`.env.example`을 복사해 `.env`로 만들고 DB 비밀번호, OpenWeatherMap API 키를 채워 넣음.

```bash
# 터미널 1 — 백엔드
python -m uvicorn app.main:app --reload --app-dir backend

# 터미널 2 — 프론트엔드
streamlit run frontend/app.py
```

## 데이터 파이프라인

```bash
python combine_real_accidents.py              # 6개 지역 사고 원본 통합
python db/scripts/aggregate_weather_monthly.py # 기상 데이터 지역x연월 집계
python ml/src/models/train_region_model.py     # 지역별 XGBoost 재학습
python db/scripts/load_real_accidents.py       # accidents 테이블 적재
```

## 데이터 출처 구분

- `ml/data/real/` : TAAS 교통사고분석시스템, 기상자료개방포털 등 실제 공공데이터
- `ml/data/stress_test/` : `db/scripts/generate_mock_data.py`로 생성한 가짜 대량 데이터. 모델 학습에 사용하지 않음. PostgreSQL 적재·쿼리 성능 테스트 전용

## 문서

- `docs/performance/db-stress-test.md` — 인덱스 성능 벤치마크
- `docs/performance/retrain-real-data-summary.csv` — 지역별 재학습 성능
- `docs/performance/real-vs-mock-comparison.md` — 실데이터 vs mock 데이터 학습 성능 비교
- `docs/troubleshooting-v3.md` — 트러블슈팅 로그

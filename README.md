# 주요도시 교통사고 예측 V3

경상남도 양산시 대상으로 만들었던 [V1](https://github.com/wogjs0808coder/yangsan-traffic-risk)을 서울·부산·대구·인천·대전·경남(양산) 6개 광역시도로 확장한 [V2](https://github.com/wogjs0808coder/yangsan-traffic-risk-v2)를, PostgreSQL + FastAPI + Streamlit 3-tier 아키텍처로 다시 설계한 프로젝트다.

V1 노션: https://fragrant-dewberry-0a3.notion.site/3c0294bdb6c580c394e1dfc48ae705a6

V1 서비스: https://yangsan-traffic-risk-gheuv599appgwkiqv4mxbn6.streamlit.app/

V2 노션: https://fragrant-dewberry-0a3.notion.site/V2-3c2294bdb6c5802590bed7b7dcf79ea4

V2 서비스: https://yangsan-traffic-risk-v2-xvqo3ouenhkpuczsapdxsi.streamlit.app/

V3 노션: https://fragrant-dewberry-0a3.notion.site/V3-3c9294bdb6c580b7a8b3c2a5124359ec?pvs=74

V3 서비스: https://yangsan-traffic-risk-v3-x5lhgvbdv7h2rzvawxdpzp.streamlit.app/

## V2와의 차이

| | V2 | V3 |
|---|---|---|
| 구조 | Streamlit 단일 앱 | PostgreSQL + FastAPI + Streamlit 3-tier |
| 데이터 | mock 데이터 | 실제 사고 데이터 215,220건(2022~2024, 6개 지역) |
| 모델 관리 | 코드 내 정적 로드 | 지역별 아티팩트 분리(`ml_artifacts/{region}/`), API로 서빙 |
| 예측 이력 | 없음 | DB 기록 + 통계 차트 + 페이지네이션 조회 |
| 지도 시각화 | 시군구별 사고다발지역(정적) | 지역별 실사고/예측 분포, 선택 지역 확대·강조(FastAPI 연동) |
| 배포 | Streamlit Cloud 단일 앱 | Neon(DB) + Render(API) + Streamlit Cloud(프론트) 분리 배포 |

## 지역별로 모델을 따로 둔 이유

지역별 데이터 규모 차이가 커서(서울 약 10만 건, 양산 약 3,700건) 하나의 모델로 합치면 서울 패턴이 다른 지역을 압도하는 문제가 있었다. 클래스 균형 조정(class weighting)을 적용해본 결과 weighted-F1 기준으로는 오히려 성능이 떨어지는 경우가 많아, 최종적으로 지역별 개별 모델과 가중치 없는 학습 방식을 채택했다. V3에서 Optuna 튜닝을 재적용한 결과도 같은 맥락으로, 데이터 규모가 큰 4개 지역(서울·부산·대구·인천)은 성능이 개선되어 반영했지만 소규모 2개 지역(대전·양산)은 CV 목적함수가 표본 부족으로 불안정해져 베이스라인을 유지했다.

## 구현 내용

### 객체지향 프로그래밍 언어 및 애플리케이션 설계

**프로그래밍 언어 활용**
Python 3 기반. 백엔드는 FastAPI(비동기 웹 프레임워크) + SQLAlchemy(ORM), 프론트엔드는 Streamlit. Pydantic 모델로 요청/응답 스키마를 클래스 단위로 정의(`PredictRequest`, `PredictResponse`, `PredictionLogItem` 등). SQLAlchemy `PredictionLog`, `Accident` 등 ORM 클래스가 DB 테이블과 매핑되는 객체지향 구조. XGBoost(`XGBClassifier`)로 지역별 분류 모델 학습, scikit-learn 전처리(LabelEncoder, get_dummies) 적용.

**요구사항 확인**
목적은 6개 지역(서울·부산·대구·인천·대전·양산)의 실제 사고 데이터(215,220건, 2022~2024)로 사고유형을 예측하는 것. 기능 요구사항은 지역별 예측, 실시간 기상 연동, 예측 이력 조회(통계+상세), 지역별 사고/예측 분포 지도 시각화. 비기능 요구사항은 지역별 모델 성능(weighted-F1) 최적화와 외부 배포를 통한 접근성 확보.

**화면 설계**
Streamlit 탭 구조는 예측 / 예측 이력 / 지도로 구성. 디자인 시스템 적용(Pretendard 폰트, `#3182F6` 브랜드 컬러, 라이트 모드 고정). 사이드바에 백엔드 상태, 지역 선택, 기상 연동 상태 표시. 예측 결과는 그라디언트 카드 + 신뢰도 바로 시각화.

**애플리케이션 설계**
3-tier 아키텍처: PostgreSQL(Neon) — FastAPI(Render) — Streamlit(Streamlit Cloud). 백엔드 모듈 구조는 `api/`(라우터), `models/`(추론 로직), `schemas/`(Pydantic), `db/`(세션, ORM), `core/`(설정)로 분리. 지역별 모델 아티팩트를 `backend/ml_artifacts/{region}/`에 분리 저장(model.json, classes.json, train_columns.json). 환경변수 기반 설정(`DATABASE_URL`)으로 로컬/배포 환경 분리.

### 관계형 데이터베이스 구축

**SQL 활용**
`GROUP BY` 기반 집계 쿼리로 지역별/유형별/일별 통계 산출(`/history/stats`, `/accidents/stats`). 날짜 필터링에 `func.date()` 활용, 페이지네이션에 `OFFSET`/`LIMIT` 적용. `pg_dump` / `psql`로 로컬 DB에서 Neon 클라우드 DB로 마이그레이션 수행.

**데이터베이스 구현**
테이블은 `accidents`(실사고 데이터), `prediction_logs`(예측 이력), `model_metadata`, `stress_test_accidents`(mock 벤치마크용). `prediction_logs`에 `region`, `requested_at` 인덱스 설계. 로컬 PostgreSQL에서 Neon(서버리스 PostgreSQL, 무료 티어)으로 이전, 21만 건 데이터 무손실 이관 확인.

### 웹 애플리케이션 통합 구현

**서버프로그램 구현**
FastAPI 라우터: `/predict`, `/history`, `/history/stats`, `/accidents/stats`, `/regions`, `/model-info`, `/weather`, `/health`. 지역별 XGBoost 모델을 `lru_cache`로 최초 1회만 로드해 추론 성능 확보. Optuna 하이퍼파라미터 튜닝 파이프라인 구축(StratifiedKFold CV, weighted-F1 objective) — 데이터 규모가 큰 4개 지역은 프로덕션 반영, 소규모 2개 지역은 베이스라인 유지.

**네트워크 프로그래밍 구현**
프론트엔드 `api_client.py`가 `requests`로 백엔드 REST API 호출(서버 간 통신이라 CORS 이슈 없음). OpenWeatherMap 외부 API 연동(실시간 기상 데이터, 캐시/기본값 폴백 체인). 배포 환경에서 콜드스타트 대응을 위해 타임아웃/캐싱 전략 조정(`st.cache_data` TTL 적용).

**화면 구현**
`frontend/app.py`에서 탭 기반 UI(예측/이력/지도), 지역 선택에 따른 동적 폼 생성. Folium 기반 인터랙티브 지도(`streamlit-folium`)로 지역별 사고/예측 분포, 선택 지역 확대+강조 표시. 커스텀 로딩 스피너로 네트워크 호출 상태를 브랜드 스타일로 표시.

**인터페이스 구현**
백엔드 `get_region_schema()`가 학습 컬럼을 파싱해 프론트엔드 입력 폼을 자동 생성하는 스키마 인터페이스 제공. Pydantic 스키마로 요청/응답 데이터 계약을 명시적으로 정의. `build_input_row()`가 사용자 입력을 모델의 원-핫 인코딩 피처 형식으로 변환하는 어댑터 역할 수행.

**통합 구현**
로컬 개발(Postgres+uvicorn+streamlit)에서 클라우드 배포(Neon+Render+Streamlit Cloud)까지 전 과정에서 발생한 통합 이슈 해결:
- 환경변수 미반영으로 인한 DB 연결 실패 디버깅(`config.py`의 `DATABASE_URL` 우선순위 수정)
- Streamlit 마크다운 렌더링 시 들여쓰기로 인한 HTML 파싱 오류 수정
- 백엔드 스키마 파싱 로직의 다중 프리픽스(`road_condition` 등) 처리 버그 수정

### 애플리케이션 테스트 수행 및 배포

**애플리케이션 테스트 수행**
지역별 베이스라인 vs Optuna 튜닝 모델을 동일 held-out test set으로 비교 검증(`docs/performance/optuna-tuning-summary.csv`). `/health` 엔드포인트로 DB 연결 상태 상시 확인. 배포 환경에서 콜드스타트/타임아웃으로 인한 간헐적 장애를 로그 기반으로 재현·수정.

**애플리케이션 배포**
DB는 Neon(서버리스 PostgreSQL, 무료). 백엔드는 Render 무료 웹서비스(`uvicorn`, 환경변수로 DB 연결). 프론트엔드는 Streamlit Community Cloud(Secrets로 백엔드 URL 주입). GitHub push 기반 자동 재배포 파이프라인 구성.

## 기술 스택

Python, FastAPI, SQLAlchemy, PostgreSQL(Neon), Streamlit, streamlit-folium, XGBoost, Optuna, scikit-learn, pandas, requests, OpenWeatherMap API

## 실행 방법

```bash
git clone https://github.com/wogjs0808coder/yangsan-traffic-risk-v3.git
cd yangsan-traffic-risk-v3
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

백엔드(FastAPI):

```bash
uvicorn app.main:app --reload --app-dir backend
```

프론트엔드(Streamlit, 새 터미널):

```bash
streamlit run frontend\app.py
```

백엔드가 먼저 떠 있어야 정상 동작한다. `.env`에 `DATABASE_URL`(또는 `DB_HOST`/`DB_NAME`/`DB_USER`/`DB_PASSWORD`), `OPENWEATHER_API_KEY`가 필요하다.

## 폴더 구조

```
backend/
├── app/
│   ├── api/            라우터 (predict, history, accidents, regions, model-info, weather, health)
│   ├── core/            설정 (config.py)
│   ├── db/              세션, ORM 모델
│   ├── models/           추론 로직 (inference.py)
│   └── schemas/          Pydantic 스키마
└── ml_artifacts/         지역별 학습된 모델 (model.json, classes.json, train_columns.json)
frontend/
├── app.py                Streamlit 메인 (예측 / 예측 이력 / 지도 탭)
├── api_client.py          백엔드 API 클라이언트
└── style.css              Toss 스타일 커스텀 CSS
ml/
├── src/models/            학습 스크립트 (train_region_model.py, tune_region_model.py)
└── data/real/             실사고·기상 데이터 (parquet)
docs/
├── performance/           모델 성능 비교 리포트
├── deployment-guide.md     배포 가이드
└── project-documentation.md  프로젝트 문서
```

## 트러블슈팅

### 1. 위젯이 안 뜨고 에러남
**문제**: selectbox 등에서 `Failed to fetch dynamically imported module` 에러 발생.
**원인**: 서버 재시작으로 정적 JS 번들 해시가 바뀌었는데 브라우저 탭은 이전 번들을 참조.
**해결**: 서버 완전 재시작 + 브라우저 탭 새로 열기(또는 Ctrl+Shift+R로 캐시 무시).

### 2. `</div>`가 화면에 텍스트로 노출됨
**문제**: caption 없이 섹션 헤더를 렌더링하면 `</div>` 줄이 HTML로 안 먹히고 그대로 텍스트로 출력됨.
**원인**: `<h3>`와 `</div>` 사이에 공백만 있는 줄이 생기고, Streamlit의 CommonMark 파서가 "빈 줄 다음 4칸 이상 들여쓰기 줄"을 코드블록으로 해석.
**해결**: HTML을 여러 줄로 들여쓰지 않고 한 줄로 합쳐서 작성.

### 3. 범주형 입력 옵션에 `condition_`, `type_`, `group_` 같은 접두어가 남음
**문제**: `road_condition_건조` 같은 2단어 프리픽스 컬럼이 `road`/`condition_건조`로 잘못 분리됨.
**원인**: `col.partition("_")`가 첫 번째 `_`에서만 자르는데, 프리픽스 자체에 `_`가 포함된 컬럼명을 고려하지 않음.
**해결**: 알려진 카테고리 이름 목록(`CATEGORICAL_FEATURE_NAMES`)으로 전체 프리픽스를 정확히 매칭하도록 파싱 로직 수정.

### 4. 배포 후 `db_connected: false`
**문제**: Render에 `DATABASE_URL` 환경변수를 넣었는데도 DB 연결 실패.
**원인**: `config.py`가 `DATABASE_URL`을 읽지 않고 `DB_HOST`/`DB_NAME`/`DB_USER`/`DB_PASSWORD` 개별 변수만 조합해 URL을 생성 — 미설정 시 `localhost`로 폴백.
**해결**: `DATABASE_URL`이 있으면 우선 사용하고, 없으면 기존 방식으로 폴백하도록 `config.py` 수정.

### 5. 로컬 DB → Neon 이관 시 스키마 혼동
**문제**: `production.accidents` 테이블이 없다는 에러.
**원인**: `production`/`stress_test`가 별도 PostgreSQL 스키마가 아니라, `public` 스키마 안에 `accidents`/`stress_test_accidents`로 테이블명만 분리된 구조였음.
**해결**: `pg_dump -t public.accidents -t public.model_metadata -t public.prediction_logs`로 실제 테이블명 지정해 덤프.

### 6. 실시간 기상 연동 실패(401 Unauthorized)
**문제**: 배포 환경에서 기상 상태가 항상 "기본값 사용"으로 표시됨.
**원인**: Render에 `OPENWEATHER_API_KEY` 환경변수가 없어 빈 키로 API 호출.
**해결**: Render Environment 탭에 `OPENWEATHER_API_KEY` 추가.

### 7. 지역 변경 시 예측 결과가 곧바로 사라짐
**문제**: 예측 버튼을 눌러 결과가 떴다가 다른 상호작용만 해도 결과가 사라짐.
**원인**: Streamlit은 상호작용마다 스크립트를 처음부터 재실행하는데, `st.button`의 True 상태는 클릭된 그 순간에만 유지되고 다음 재실행에서 초기화됨. 결과를 어디에도 저장하지 않았음.
**해결**: `st.session_state`에 마지막 예측 결과를 저장하고, 저장된 결과의 지역이 현재 선택된 지역과 같을 때만 표시.

### 8. 지역을 여러 번 바꾸면 앱 전체가 멈춤
**문제**: "백엔드 서버에 연결할 수 없습니다" 에러로 앱이 완전히 멈춰서 아무것도 못 함.
**원인**: 헬스체크(`check_health`)가 캐싱 없이 모든 재실행마다 호출됐고, 실패 시 `st.stop()`으로 앱 전체를 중단시킴. Render 무료 인스턴스가 짧은 시간에 연속 요청을 받으면 5초 타임아웃 안에 응답을 못 주는 경우가 있었음.
**해결**: 헬스체크에 캐싱(TTL 15초) 적용, 실패해도 `st.stop()` 대신 경고만 표시하고 앱은 계속 사용 가능하도록 완화. 전체 API 타임아웃도 5~10초에서 15초로 상향.


## 데이터 출처

- 교통사고 데이터: 도로교통공단 TAAS 교통사고분석시스템 (공공데이터포털)
- 기상 데이터: 기상청 기상자료개방포털, OpenWeatherMap

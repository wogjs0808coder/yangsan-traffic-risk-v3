# V3 트러블슈팅 로그

V2와 동일하게, 한 번에 해결되지 않고 원인 파악 → 수정까지 거친 이슈들을 기록합니다.

---

## 이슈 1: `.gitignore` 압축 과정에서 실수로 누락

**문제 상황**: 초기 프로젝트 골격을 zip으로 전달하는 과정에서, `.git` 관련 파일을 압축 제외 목록에 넣었는데 이 필터가 파일명에 `.git`이 포함된 `.gitignore` 자체까지 걸러버렸습니다. 결과적으로 로컬에 `.gitignore`가 없는 상태로 `git init` → `git commit`이 진행됐습니다.

**원인**: zip 압축 시 `-x "*.git*"` 같은 와일드카드 필터가 의도한 대상(`.git/` 폴더) 외에 `.gitignore` 파일명까지 매칭시킴.

**해결**: `.gitignore` 내용을 다시 만들어 별도로 추가. 이후 압축 시 제외 패턴을 `.git/*`처럼 더 명확하게 지정하도록 개선.

---

## 이슈 2: PowerShell + PostgreSQL 한글 인코딩 충돌

**문제 상황**: `psql -c "SELECT ... WHERE region = '서울특별시'"`처럼 한글이 포함된 쿼리를 커맨드라인 인자로 직접 넘기면 `EXPLAIN ANALYZE` 결과에 지역명이 깨져서 출력되고(`?쒖슱?밸퀎??`), 심한 경우 `psql -f`로 파일 실행 시 UHC/CP949 인코딩 문자를 UTF-8로 해석하지 못해 SQL 파일 일부가 아예 실행되지 않는 오류(`CREATE TABLE model_metadata` 누락)까지 발생했습니다.

**원인**: Windows PowerShell 콘솔의 기본 코드페이지(CP949)와, psql이 파일을 읽을 때 기대하는 UTF-8 인코딩이 불일치.

**해결**:
- 한글이 포함된 쿼리는 `-c` 커맨드라인 인자 대신 `.sql` 파일로 작성 후 `-f`로 실행
- 파일 실행 시 `$env:PGCLIENTENCODING="UTF8"`을 세션에 설정해 인코딩 강제 지정
- 콘솔 출력 자체가 깨져 보이는 건 표시 문제일 뿐 DB에 저장된 실제 데이터는 정상임을 `SELECT current_database()` 등으로 별도 검증

---

## 이슈 3: 인덱스가 오히려 쿼리를 느리게 만든 케이스

**문제 상황**: `stress_test_accidents`(2,000만 건) 테이블에 `region` 단일 인덱스를 걸고 `region = '서울특별시'` 조건으로 조회했더니, 인덱스 적용 전(520ms)보다 적용 후(724ms)가 오히려 39% 더 느려짐.

**원인**: `region` 조건은 전체의 약 17%(333만 건)를 골라내는, 선택도가 낮은(대량 반환) 쿼리. 이런 경우 인덱스를 통한 랜덤 디스크 접근 비용이 순차 스캔보다 커짐. 게다가 다중 컬럼(`region + accident_type + vehicle_type`)을 동시에 필터링하는 쿼리에서는 단일 컬럼 인덱스가 아예 선택되지 않고 Seq Scan으로 처리됨.

**해결**: 실제 쿼리 패턴(`region, accident_type, vehicle_type` 동시 필터링)에 맞춘 **복합 인덱스**를 생성. 선택도가 낮은(0.2%) 쿼리에서 529.7ms → 165.956ms로 3.2배 개선 확인. 전체 벤치마크는 `docs/performance/db-stress-test.md` 참고.

---

## 이슈 4: V2 강수량 컬럼명 불일치로 예측 왜곡

**문제 상황**: V3 `/predict`에 `weather_features`로 `"일강수량(mm)": 20.0`을 넘겼는데, 실제 V2가 학습에 사용한 컬럼명은 `일강수량_클립(mm)`이었음. 키가 일치하지 않아 강수량 값이 조용히 무시되고(기본값 0 처리) 예측이 진행되고 있었음.

**추가로 발견된 연쇄 문제**: 프론트엔드 자동 폼 생성 로직(`get_region_schema`)이 "컬럼명에 `_`가 있으면 무조건 범주형"으로 분류하고 있어, `일강수량_클립(mm)`과 `폭우_여부_플래그`처럼 밑줄이 포함된 수치형 컬럼까지 범주형으로 잘못 인식하고 있었음.

**원인**: V2의 `to_model_features()`가 생성하는 실제 컬럼명을 확인하지 않고 임의로 `"일강수량(mm)"`이라는 이름을 가정해서 사용함. 컬럼 분류 로직도 "밑줄 유무"라는 단순한 휴리스틱에 의존함.

**해결**:
- `KNOWN_NUMERIC_COLUMNS` 화이트리스트로 수치형 컬럼을 명시적으로 지정해 분류 정확도 개선
- 실시간 기상 API 연동 시, 컬럼명을 하드코딩하지 않고 `train_columns.json`에서 가져온 실제 컬럼에 키워드 매칭(`기온`, `강수`, `풍속`, `습도`, `폭우`)으로 값을 채우는 방식(`map_weather_to_features`)으로 변경해 향후 동일한 문제 재발 방지

**영향**: 이 버그 수정 이후 일부 지역(예: 대전)에서 예측 신뢰도가 눈에 띄게 낮아짐(34% 수준). 이는 회귀가 아니라, 그동안 반영되지 않던 강수량 값이 처음으로 제대로 반영되면서 원래 모델 성능(대전 XGBoost weighted-F1 0.289)이 있는 그대로 드러난 것으로 확인함 — `model_comparison_result.csv` 대조로 검증.

---

## 관련 파일

- `backend/app/models/inference.py` — `KNOWN_NUMERIC_COLUMNS`, `get_region_schema`
- `backend/app/services/weather_service.py` — `map_weather_to_features`
- `docs/performance/db-stress-test.md` — 이슈 3 관련 전체 벤치마크

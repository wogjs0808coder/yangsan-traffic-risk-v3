import streamlit as st

from api_client import check_health, get_model_info, get_regions, get_weather, predict

st.set_page_config(page_title="교통사고 위험 예측 (V3)", page_icon="🚦", layout="centered")

st.title("🚦 주요시 교통사고 예측")
st.caption("V3 — PostgreSQL + FastAPI 백엔드 연동 (프론트엔드는 UI 렌더링만 담당)")

# --- 백엔드 연결 상태 확인 ---
with st.sidebar:
    st.subheader("백엔드 상태")
    try:
        health = check_health()
        if health.get("db_connected"):
            st.success("API 서버 및 DB 연결 정상")
        else:
            st.warning("API 서버는 응답하지만 DB 연결 실패")
    except Exception:
        st.error("백엔드(FastAPI) 서버에 연결할 수 없습니다. uvicorn 실행 여부를 확인하세요.")
        st.stop()

# --- 지역 선택 ---
try:
    regions = get_regions()
except Exception as e:
    st.error(f"지역 목록을 불러오지 못했습니다: {e}")
    st.stop()

region = st.selectbox("지역 선택", regions)

# --- 선택한 지역의 모델 입력 스키마 로드 ---
try:
    schema = get_model_info(region)
except Exception as e:
    st.error(f"{region} 모델 정보를 불러오지 못했습니다: {e}")
    st.stop()

numeric_features: list[str] = schema["numeric_features"]
categorical_options: dict[str, list[str]] = schema["categorical_options"]

# --- 실시간 기상 데이터 조회 (폼 기본값으로 사용) ---
try:
    weather_resp = get_weather(region)
    weather_raw = weather_resp["weather"]
    model_features_default = weather_resp["model_features"]

    source = weather_raw.get("_source", "unknown")
    if source == "live":
        st.sidebar.success(f"실시간 기상 연동 ({weather_raw['temperature']:.1f}°C)")
    elif source == "cache":
        st.sidebar.warning("기상 API 응답 지연 — 캐시 데이터 사용")
    else:
        st.sidebar.error("기상 데이터 수신 실패 — 기본값 사용")
except Exception:
    model_features_default = {}
    st.sidebar.error("기상 API 호출 실패 — 기본값 0으로 시작합니다")

st.divider()
st.subheader("기상 조건 입력")
st.caption("실시간 기상 데이터로 자동 채워집니다. 직접 값을 바꿔서 시나리오를 테스트할 수도 있습니다.")

weather_features = {}
cols = st.columns(2)
for i, feature_name in enumerate(numeric_features):
    default_value = float(model_features_default.get(feature_name, 0.0))
    with cols[i % 2]:
        weather_features[feature_name] = st.number_input(
            feature_name, value=default_value, step=0.1
        )

st.divider()
st.subheader("사고 조건 입력")

user_inputs = {}
for feature_name, options in categorical_options.items():
    selected = st.selectbox(feature_name, sorted(set(options)))
    user_inputs[feature_name] = selected

st.divider()

if st.button("예측하기", type="primary", use_container_width=True):
    try:
        result = predict(region, weather_features, user_inputs)
    except Exception as e:
        st.error(f"예측 요청 실패: {e}")
    else:
        st.success(f"예측된 사고 유형: **{result['predicted_type']}**")
        st.metric("신뢰도(Confidence)", f"{result['confidence'] * 100:.1f}%")

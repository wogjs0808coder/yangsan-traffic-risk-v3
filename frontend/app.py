from pathlib import Path

import streamlit as st

from api_client import check_health, get_model_info, get_regions, get_weather, predict

st.set_page_config(page_title="교통사고 위험 예측 (V3)", page_icon="🚦", layout="centered")


def inject_css():
    css_path = Path(__file__).parent / "style.css"
    st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def section_header(title: str, caption: str = ""):
    st.markdown(
        f"""<div class="section-card">
            <h3>{title}</h3>
            {f'<p class="section-caption">{caption}</p>' if caption else ''}
        </div>""",
        unsafe_allow_html=True,
    )


inject_css()

st.markdown(
    """<div class="app-header">
        <h1>🚦 주요시 교통사고 예측</h1>
        <p>PostgreSQL + FastAPI + Streamlit — V3</p>
    </div>""",
    unsafe_allow_html=True,
)

# --- 백엔드 연결 상태 확인 ---
with st.sidebar:
    st.markdown("**백엔드 상태**")
    try:
        health = check_health()
        if health.get("db_connected"):
            st.markdown('<span class="status-badge live">● API·DB 연결 정상</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-badge cache">● DB 연결 실패</span>', unsafe_allow_html=True)
    except Exception:
        st.error("백엔드(FastAPI) 서버에 연결할 수 없습니다. uvicorn 실행 여부를 확인하세요.")
        st.stop()

# --- 지역 선택 ---
try:
    regions = get_regions()
except Exception as e:
    st.error(f"지역 목록을 불러오지 못했습니다: {e}")
    st.stop()

with st.sidebar:
    st.markdown("**지역 선택**")
    region = st.selectbox("지역", regions, label_visibility="collapsed")

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
    with st.sidebar:
        st.markdown("**기상 연동 상태**")
        if source == "live":
            st.markdown(
                f'<span class="status-badge live">● 실시간 연동 ({weather_raw["temperature"]:.1f}°C)</span>',
                unsafe_allow_html=True,
            )
        elif source == "cache":
            st.markdown('<span class="status-badge cache">● 캐시 데이터 사용</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-badge default">● 기본값 사용</span>', unsafe_allow_html=True)
except Exception:
    model_features_default = {}
    with st.sidebar:
        st.markdown('<span class="status-badge default">● 기상 API 호출 실패</span>', unsafe_allow_html=True)

# --- 기상 조건 입력 ---
section_header("기상 조건", "실시간 데이터로 자동 채워집니다. 직접 조정해 시나리오를 테스트할 수 있습니다.")

weather_features = {}
cols = st.columns(2)
for i, feature_name in enumerate(numeric_features):
    default_value = float(model_features_default.get(feature_name, 0.0))
    with cols[i % 2]:
        weather_features[feature_name] = st.number_input(
            feature_name, value=default_value, step=0.1
        )

# --- 사고 조건 입력 ---
section_header("사고 조건")

user_inputs = {}
for feature_name, options in categorical_options.items():
    selected = st.selectbox(feature_name, sorted(set(options)))
    user_inputs[feature_name] = selected

st.write("")

if st.button("예측하기", type="primary", use_container_width=True):
    try:
        result = predict(region, weather_features, user_inputs)
    except Exception as e:
        st.error(f"예측 요청 실패: {e}")
    else:
        confidence_pct = result["confidence"] * 100
        st.markdown(
            f"""<div class="result-card">
                <div class="result-label">{result['region']} · 예측된 사고 유형</div>
                <div class="result-type">{result['predicted_type']}</div>
                <div class="confidence-track">
                    <div class="confidence-fill" style="width: {confidence_pct:.1f}%;"></div>
                </div>
                <div class="confidence-value">신뢰도 {confidence_pct:.1f}%</div>
            </div>""",
            unsafe_allow_html=True,
        )

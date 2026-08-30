from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from api_client import (
    check_health,
    get_model_info,
    get_prediction_history,
    get_prediction_stats,
    get_regions,
    get_weather,
    predict,
)

st.set_page_config(page_title="교통사고 위험 예측 (V3)", page_icon="🚦", layout="centered")


def inject_css():
    css_path = Path(__file__).parent / "style.css"
    st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def section_header(title: str, caption: str = ""):
    # caption이 있을 때만 p 태그 생성
    caption_html = f'<p class="section-caption">{caption}</p>' if caption else ""
    html_content = f'<div class="section-card"><h3>{title}</h3>{caption_html}</div>'
    st.markdown(html_content, unsafe_allow_html=True)


inject_css()

st.markdown(
    """<div class="app-header">
        <h1>🚦 주요시 교통사고 예측</h1>
        <p>PostgreSQL + FastAPI + Streamlit — V3</p>
    </div>""",
    unsafe_allow_html=True,
)

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

try:
    regions = get_regions()
except Exception as e:
    st.error(f"지역 목록을 불러오지 못했습니다: {e}")
    st.stop()

with st.sidebar:
    st.markdown("**지역 선택**")
    region = st.selectbox("지역", regions, label_visibility="collapsed")

tab_predict, tab_history = st.tabs(["예측", "예측 이력"])

with tab_predict:
    try:
        schema = get_model_info(region)
    except Exception as e:
        st.error(f"{region} 모델 정보를 불러오지 못했습니다: {e}")
        st.stop()

    numeric_features: list[str] = schema["numeric_features"]
    categorical_options: dict[str, list[str]] = schema["categorical_options"]

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

    section_header("기상 조건", "실시간 데이터로 자동 채워집니다. 직접 조정해 시나리오를 테스트할 수 있습니다.")

    weather_features = {}
    cols = st.columns(2)
    for i, feature_name in enumerate(numeric_features):
        default_value = float(model_features_default.get(feature_name, 0.0))
        with cols[i % 2]:
            weather_features[feature_name] = st.number_input(
                feature_name, value=default_value, step=0.1
            )

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

with tab_history:
    section_header("예측 이력", "지역별/기간별 예측 통계와 상세 이력을 확인합니다.")

    filter_cols = st.columns(3)
    with filter_cols[0]:
        hist_region = st.selectbox("지역 필터", ["전체"] + regions, key="hist_region")
    with filter_cols[1]:
        date_from = st.date_input("시작일", value=date.today() - timedelta(days=30), key="hist_date_from")
    with filter_cols[2]:
        date_to = st.date_input("종료일", value=date.today(), key="hist_date_to")

    region_param = None if hist_region == "전체" else hist_region

    try:
        stats = get_prediction_stats(region_param, date_from, date_to)
    except Exception as e:
        st.error(f"통계를 불러오지 못했습니다: {e}")
        stats = None

    if stats:
        metric_cols = st.columns(2)
        metric_cols[0].metric("총 예측 건수", f"{stats['total_predictions']:,}")
        avg_conf = stats["avg_confidence"]
        metric_cols[1].metric("평균 신뢰도", f"{avg_conf * 100:.1f}%" if avg_conf is not None else "—")

        chart_cols = st.columns(2)
        with chart_cols[0]:
            st.markdown("**지역별 예측 건수**")
            if stats["by_region"]:
                df_region = pd.DataFrame(stats["by_region"]).set_index("region")
                st.bar_chart(df_region["count"])
            else:
                st.caption("데이터 없음")
        with chart_cols[1]:
            st.markdown("**사고유형별 예측 건수**")
            if stats["by_type"]:
                df_type = pd.DataFrame(stats["by_type"]).set_index("predicted_type")
                st.bar_chart(df_type["count"])
            else:
                st.caption("데이터 없음")

        st.markdown("**일별 예측 추이**")
        if stats["daily_counts"]:
            df_daily = pd.DataFrame(stats["daily_counts"]).set_index("day")
            st.line_chart(df_daily["count"])
        else:
            st.caption("데이터 없음")

    st.write("")
    st.markdown("**상세 이력**")

    if "hist_page" not in st.session_state:
        st.session_state.hist_page = 1

    page_cols = st.columns([1, 1, 4])
    with page_cols[0]:
        if st.button("이전", disabled=st.session_state.hist_page <= 1):
            st.session_state.hist_page -= 1
    with page_cols[1]:
        if st.button("다음"):
            st.session_state.hist_page += 1

    try:
        history = get_prediction_history(
            region_param, date_from, date_to, page=st.session_state.hist_page, page_size=20
        )
    except Exception as e:
        st.error(f"이력을 불러오지 못했습니다: {e}")
        history = None

    if history:
        st.caption(f"{history['total']:,}건 중 {len(history['items'])}건 표시 (페이지 {history['page']})")
        if history["items"]:
            df_items = pd.DataFrame(history["items"])
            df_items = df_items[["requested_at", "region", "predicted_type", "confidence"]]
            df_items["confidence"] = (df_items["confidence"] * 100).round(1)
            df_items.columns = ["요청 시각", "지역", "예측 유형", "신뢰도(%)"]
            st.dataframe(df_items, use_container_width=True, hide_index=True)
        else:
            st.caption("조건에 맞는 이력이 없습니다.")

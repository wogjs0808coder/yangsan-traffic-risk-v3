"""
V2의 src/realtime/weather_api.py 를 FastAPI 백엔드용으로 이관.

변경점:
- Streamlit 파일 캐시(data_processed/{region}/weather_cache.json) 대신
  프로세스 메모리 내 dict 캐시 사용 (서버가 켜져있는 동안 유지)
- to_model_features()는 하드코딩된 컬럼명 대신, 실제 train_columns.json에서
  가져온 numeric_features 리스트에 키워드 매칭으로 값을 채워 넣는 방식으로 변경
  (지역별로 컬럼명이 정확히 일치하는지 신경 쓸 필요 없이 안전하게 매핑됨)
"""

import time

import requests

from app.core.config import get_settings

BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

REGION_COORDS = {
    "seoul": (37.5665, 126.9780),
    "busan": (35.1796, 129.0756),
    "daegu": (35.8714, 128.6014),
    "incheon": (37.4563, 126.7052),
    "daejeon": (36.3504, 127.3845),
    "yangsan": (35.3350, 129.0378),
}

CACHE_TTL_SEC = 60 * 10
RAIN_CLIP_MAX = 100.0

_MEMORY_CACHE: dict[str, dict] = {}


def _read_cache(region_en: str) -> dict | None:
    cached = _MEMORY_CACHE.get(region_en)
    if cached is None:
        return None
    if time.time() - cached.get("_cached_at", 0) > CACHE_TTL_SEC:
        return None
    return cached


def _write_cache(region_en: str, data: dict) -> None:
    data = dict(data)
    data["_cached_at"] = time.time()
    _MEMORY_CACHE[region_en] = data


def parse_openweather_response(raw: dict) -> dict:
    rainfall = raw.get("rain", {}).get("1h", 0.0)
    return {
        "temperature": raw["main"]["temp"],
        "rainfall": rainfall,
        "humidity": raw["main"]["humidity"],
        "wind_speed": raw["wind"]["speed"],
        "weather_description": raw["weather"][0]["description"],
    }


def fetch_current_weather(region_en: str) -> dict:
    if region_en not in REGION_COORDS:
        raise ValueError(f"지원하지 않는 지역: {region_en} (가능한 값: {list(REGION_COORDS)})")

    settings = get_settings()
    lat, lon = REGION_COORDS[region_en]
    params = {
        "lat": lat,
        "lon": lon,
        "appid": settings.OPENWEATHER_API_KEY,
        "units": "metric",
        "lang": "kr",
    }
    response = requests.get(BASE_URL, params=params, timeout=5)
    response.raise_for_status()
    return parse_openweather_response(response.json())


def get_current_weather(region_en: str) -> dict:
    """실시간 기상 데이터를 반환한다. 실패 시 캐시, 그마저 없으면 기본값을 반환한다."""
    try:
        weather = fetch_current_weather(region_en)
        _write_cache(region_en, weather)
        weather["_source"] = "live"
        return weather
    except Exception as e:
        print(f"[경고] {region_en} 실시간 기상 API 호출 실패: {e}")
        cached = _read_cache(region_en)
        if cached:
            cached["_source"] = "cache"
            return cached
        return {
            "temperature": 15.0,
            "rainfall": 0.0,
            "humidity": 50.0,
            "wind_speed": 1.0,
            "weather_description": "정보없음",
            "_source": "default",
        }


def map_weather_to_features(weather: dict, numeric_feature_names: list[str]) -> dict:
    """
    기상 데이터를 실제 학습 컬럼명(numeric_feature_names)에 키워드 매칭으로 채워 넣는다.
    지역마다 컬럼명이 정확히 동일한지 몰라도 안전하게 동작하도록 키워드 기반으로 매핑한다.
    """
    rainfall = weather["rainfall"]
    features = {}

    for col in numeric_feature_names:
        if "기온" in col:
            features[col] = weather["temperature"]
        elif "강수" in col:
            features[col] = min(rainfall, RAIN_CLIP_MAX)
        elif "풍속" in col:
            features[col] = weather["wind_speed"]
        elif "습도" in col:
            features[col] = weather["humidity"]
        elif "폭우" in col or "플래그" in col:
            features[col] = 1 if rainfall > RAIN_CLIP_MAX else 0
        else:
            features[col] = 0.0

    return features

import os
from datetime import date

import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


@st.cache_data(ttl=3600)
def get_regions() -> list[str]:
    resp = requests.get(f"{API_BASE_URL}/regions", timeout=5)
    resp.raise_for_status()
    return resp.json()["regions"]


@st.cache_data(ttl=3600)
def get_model_info(region: str) -> dict:
    resp = requests.get(f"{API_BASE_URL}/model-info/{region}", timeout=5)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=300)
def get_weather(region: str) -> dict:
    resp = requests.get(f"{API_BASE_URL}/weather/{region}", timeout=10)
    resp.raise_for_status()
    return resp.json()


def predict(region: str, weather_features: dict, user_inputs: dict) -> dict:
    payload = {
        "region": region,
        "weather_features": weather_features,
        "user_inputs": user_inputs,
    }
    resp = requests.post(f"{API_BASE_URL}/predict", json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=15)
def check_health() -> dict:
    resp = requests.get(f"{API_BASE_URL}/health", timeout=10)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=30)
def get_prediction_history(
    region: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    params = {"page": page, "page_size": page_size}
    if region:
        params["region"] = region
    if date_from:
        params["date_from"] = date_from.isoformat()
    if date_to:
        params["date_to"] = date_to.isoformat()
    resp = requests.get(f"{API_BASE_URL}/history", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=30)
def get_accident_stats() -> dict:
    resp = requests.get(f"{API_BASE_URL}/accidents/stats", timeout=10)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=30)
def get_prediction_stats(
    region: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    params = {}
    if region:
        params["region"] = region
    if date_from:
        params["date_from"] = date_from.isoformat()
    if date_to:
        params["date_to"] = date_to.isoformat()
    resp = requests.get(f"{API_BASE_URL}/history/stats", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

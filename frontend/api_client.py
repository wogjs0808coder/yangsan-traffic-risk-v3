import os

import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def get_regions() -> list[str]:
    resp = requests.get(f"{API_BASE_URL}/regions", timeout=5)
    resp.raise_for_status()
    return resp.json()["regions"]


def get_model_info(region: str) -> dict:
    resp = requests.get(f"{API_BASE_URL}/model-info/{region}", timeout=5)
    resp.raise_for_status()
    return resp.json()


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


def check_health() -> dict:
    resp = requests.get(f"{API_BASE_URL}/health", timeout=5)
    resp.raise_for_status()
    return resp.json()

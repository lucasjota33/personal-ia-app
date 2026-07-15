import requests
from typing import Dict, Any
from .config import settings


def call_gemini(prompt: str, timeout: int = 30) -> Dict[str, Any]:
    url = f"https://generativelanguage.googleapis.com/v1beta/{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    return data


def extract_ai_text(response_data: Dict[str, Any]) -> str:
    return (
        response_data
        .get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "")
    )

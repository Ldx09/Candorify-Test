"""Minimal client for the Gemini API (Google AI Studio), used only for translation wording.
Gemini never decides what is an error on a bill.

The API key is sent in a header (not the URL), so it never appears in request logs.
"""
import json
import time

import httpx

from app.core.config import settings

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
RETRIES = 1                 # one extra attempt on timeouts / 5xx
BACKOFF_SECONDS = 1.0


class GeminiUnavailable(Exception):
    """No API key, network error, timeout, 4xx/5xx, or a reply that isn't the JSON we asked for."""


def generate_json(prompt: str, client: httpx.Client | None = None, timeout: float | None = None,
                  retries: int = RETRIES, temperature: float = 0) -> dict:
    """Sends the prompt and returns Gemini's reply parsed as a JSON object.
    `timeout` (seconds) overrides GEMINI_TIMEOUT_SECONDS, e.g. 5 for the follow-up questions."""
    if not settings.GEMINI_API_KEY:
        raise GeminiUnavailable("GEMINI_API_KEY is not set")
    url = f"{BASE_URL}/{settings.GEMINI_MODEL}:generateContent"
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "responseMimeType": "application/json"},
    }
    headers = {"x-goog-api-key": settings.GEMINI_API_KEY, "Content-Type": "application/json"}
    own = client is None
    client = client or httpx.Client(timeout=timeout or settings.GEMINI_TIMEOUT_SECONDS)
    try:
        last = "unknown error"
        for attempt in range(retries + 1):
            try:
                resp = client.post(url, json=body, headers=headers)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last = exc.__class__.__name__
            else:
                if resp.status_code == 200:
                    try:
                        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                        data = json.loads(text)
                    except (KeyError, IndexError, TypeError, ValueError):
                        raise GeminiUnavailable("Gemini returned an unexpected response") from None
                    if not isinstance(data, dict):
                        raise GeminiUnavailable("Gemini did not return a JSON object")
                    return data
                last = f"HTTP {resp.status_code}"
                if resp.status_code < 500:  # 400/401/403/429: retrying won't help
                    break
            if attempt < retries:
                time.sleep(BACKOFF_SECONDS)
        raise GeminiUnavailable(f"Gemini request failed: {last}")
    finally:
        if own:
            client.close()
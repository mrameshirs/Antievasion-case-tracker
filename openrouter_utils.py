# openrouter_utils.py
import json
import re

import requests

from config import (
    OPENROUTER_API_KEY, OPENROUTER_API_URL, OPENROUTER_MODEL_ALIASES,
    OPENROUTER_MODEL_FALLBACK_ORDER, CASE_EXTRACTION_SYSTEM_PROMPT
)


def _strip_json_fences(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _call_openrouter_model(model_alias, ocr_text):
    """Makes a single text-only call to one OpenRouter free model."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OpenRouter API key not configured in secrets (openrouter_api_key).")

    model_name = OPENROUTER_MODEL_ALIASES.get(model_alias, model_alias)
    prompt = CASE_EXTRACTION_SYSTEM_PROMPT.replace("{ocr_text}", ocr_text)

    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    resp = requests.post(OPENROUTER_API_URL, headers=headers, data=json.dumps(payload), timeout=90)
    resp.raise_for_status()
    data = resp.json()
    raw_text = data["choices"][0]["message"]["content"]
    return raw_text


def extract_case_fields_from_text(ocr_text, preferred_model=None):
    """
    ocr_text: combined OCR output from ocr_utils.extract_text_from_images.
    Tries the preferred model first, then falls back through
    OPENROUTER_MODEL_FALLBACK_ORDER on failure.

    Returns (parsed_dict, model_used, raw_error_or_None)
    """
    if not ocr_text or not ocr_text.strip():
        return None, None, "OCR produced no text to send to the LLM."

    models_to_try = []
    if preferred_model:
        models_to_try.append(preferred_model)
    for m in OPENROUTER_MODEL_FALLBACK_ORDER:
        if m not in models_to_try:
            models_to_try.append(m)

    last_error = None
    for model_alias in models_to_try:
        try:
            raw_text = _call_openrouter_model(model_alias, ocr_text)
            cleaned = _strip_json_fences(raw_text)
            parsed = json.loads(cleaned)
            return parsed, model_alias, None
        except Exception as e:
            last_error = f"{model_alias}: {e}"
            continue

    return None, None, last_error

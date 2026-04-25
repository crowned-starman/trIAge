# backend/app/ai/classifier.py

import httpx
import json
import asyncio
from datetime import datetime

from app.core.config import settings
from app.core.schemas import PatientInput, TriageResult
from app.ai.prompts import TRIAGE_SYSTEM_PROMPT, build_user_message

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_HEADERS = {
    "x-api-key":         settings.ANTHROPIC_API_KEY,
    "anthropic-version": "2023-06-01",
    "content-type":      "application/json",
}

MAX_RETRIES = 3
RETRY_DELAY = 1.5  # segundos


async def classify_patient(payload: PatientInput) -> dict | None:
    """
    Envia los datos al LLM y devuelve un dictado de clasificacion en crudo.
    Si falla reintenta hasta el numero maximo de intentos
    Devuelve None si todos los intentos fallan
    """
    user_message = build_user_message(payload)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = await _call_anthropic(user_message)
            return result

        except httpx.TimeoutException:
            if attempt == MAX_RETRIES:
                return None
            await asyncio.sleep(RETRY_DELAY * attempt)

        except httpx.HTTPStatusError as e:
            # Si hay 4xx errrors no reintentar
            if 400 <= e.response.status_code < 500:
                return None
            # Si 5xx — reintentar
            if attempt == MAX_RETRIES:
                return None
            await asyncio.sleep(RETRY_DELAY * attempt)

        except (json.JSONDecodeError, KeyError):
            #Respuesta erronea - no vale la pena reintentar
            return None

    return None


async def _call_anthropic(user_message: str) -> dict:
    """
    Raw HTTP call to the Anthropic API.
    Raises exceptions — let classify_patient handle retry logic.
    """
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            ANTHROPIC_API_URL,
            headers=ANTHROPIC_HEADERS,
            json={
                "model":      settings.ANTHROPIC_MODEL,
                "max_tokens": 512,
                "system":     TRIAGE_SYSTEM_PROMPT,
                "messages": [
                    {"role": "user", "content": user_message}
                ],
            },
        )
        response.raise_for_status()

    data = response.json()

    # Extrae el bloque de texto de la respuesta de antropic
    content_blocks = data.get("content", [])
    text_block = next(
        (b["text"] for b in content_blocks if b.get("type") == "text"),
        None,
    )

    if not text_block:
        raise KeyError("No text block in Anthropic response")

    # Strip potential markdown fences (```json ... ```)
    clean = text_block.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    clean = clean.strip()

    return json.loads(clean)

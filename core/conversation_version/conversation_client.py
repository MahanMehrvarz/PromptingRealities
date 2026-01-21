"""High-level helpers for talking to the OpenAI Responses API.

This module owns every direct call into OpenAI so the rest of the codebase can
focus on UX concerns (audio capture, MQTT messaging, etc.).  It handles three
responsibilities:

* Creating a session placeholder (the Responses API uses previous response IDs
  instead of explicit thread objects).
* Exchanging conversational turns while enforcing the schema declared in
  ``settings.response_json_schema``.
* Converting microphone audio into text with the configured transcription model.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI

from settings import settings

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_client = OpenAI(api_key=settings["openAIToken"])
_model = settings["conversation_model"]
_prompt_id = settings.get("prompt_id")
_prompt_instructions = settings.get("prompt_instructions", "")

_raw_schema = settings["response_json_schema"]
_json_schema_format = {
    "type": "json_schema",
    "name": _raw_schema.get("name", "structured_payload"),
    "schema": _raw_schema.get("schema", {}),
    "strict": _raw_schema.get("strict", False),
}

StructuredPayload = Dict[str, Any]

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_new_conversation() -> Optional[str]:
    """Return ``None`` to signal a fresh conversation session.

    The Responses API keeps context internally.  All we need to retain between
    turns is the last response ID, which the consumer stores and feeds back into
    :func:`conversation_response`.
    """

    return None


async def conversation_response(
    previous_response_id: Optional[str],
    user_message: str,
) -> Tuple[StructuredPayload, Optional[str]]:
    """Submit a user turn and receive the assistant payload.

    Args:
        previous_response_id: Identifier of the prior turn; enables long-lived
            context when supplied to the Responses API.  Use ``None`` when there
            is no history yet.
        user_message: Human-readable prompt gathered from either text input or
            the speech recogniser.

    Returns:
        A tuple of ``(payload, response_id)`` where ``payload`` matches the
        schema in ``settings.response_json_schema`` and ``response_id`` is the
        identifier to feed back on the next turn.
    """

    request_payload = [
        {
            "role": "user",
            "content": [{"type": "input_text", "text": user_message}],
        }
    ]

    kwargs: Dict[str, Any] = {}
    if previous_response_id:
        kwargs["previous_response_id"] = previous_response_id
    if _prompt_instructions:
        kwargs["instructions"] = _prompt_instructions
    if _prompt_id:
        kwargs["prompt"] = _prompt_id
    if _json_schema_format:
        kwargs["text"] = {"format": _json_schema_format}

    try:
        response = await asyncio.to_thread(
            _client.responses.create,
            model=_model,
            input=request_payload,
            **kwargs,
        )
    except Exception as exc:
        logging.error("Error in conversation response: %s", exc)
        return (
            {"response": "An error occurred while processing your request", "values": {}},
            previous_response_id,
        )

    assistant_text = _extract_assistant_text(response)
    response_id = getattr(response, "id", None)

    if not assistant_text:
        return {"response": "No response received", "values": {}}, response_id

    return _parse_structured_payload(assistant_text), response_id


async def transcribe_audio(audio_bytes: bytes) -> Optional[str]:
    """Convert PCM WAV bytes into text with the configured transcription model."""

    try:
        result = _client.audio.transcriptions.create(
            model=settings["transcription_model"],
            file=("speech.wav", audio_bytes, "audio/wav"),
            response_format="text",
            language="en",
        )
        return result if isinstance(result, str) else getattr(result, "text", None)
    except Exception as exc:
        logging.error("Error transcribing audio: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_assistant_text(response: Any) -> str:
    """Flatten the structured API response into a raw JSON string."""

    chunks: list[str] = []
    for item in getattr(response, "output", []):
        if getattr(item, "type", None) != "message":
            continue
        for content in getattr(item, "content", []):
            if getattr(content, "type", None) == "output_text":
                text = getattr(content, "text", "")
                if text:
                    chunks.append(text)
    return "".join(chunks).strip()


def _parse_structured_payload(text_blob: str) -> StructuredPayload:
    """Validate/parse the assistant JSON, surfacing graceful fallbacks."""

    try:
        parsed: StructuredPayload = json.loads(text_blob)
    except json.JSONDecodeError:
        # Preserve visibility into malformed responses while keeping the app
        # running; downstream code always expects these keys.
        return {"response": text_blob, "values": {}}
    return parsed


__all__ = ["create_new_conversation", "conversation_response", "transcribe_audio"]


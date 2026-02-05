import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Optional

from openai import OpenAI

from settings import settings

# Initialize the OpenAI client
client = OpenAI(
    api_key=settings["openAIToken"],
    default_headers={"OpenAI-Beta": "assistants=v1"},
)

_state_path = Path(settings["assistant_state_file"])
_instructions_path = Path(settings["assistant_instructions_file"])
_schema_path = Path(settings["assistant_schema_file"])
_assistant_model = settings["assistant_model"]
_assistant_name = settings["assistant_name"].strip() or None
_assistant_description = settings["assistant_description"].strip() or None

_assistant_id: Optional[str] = None
_assistant_lock = asyncio.Lock()
_cached_signature: Optional[tuple[str, str, str]] = None


def _load_text_file(path: Path) -> Optional[str]:
    try:
        content = path.read_text(encoding="utf-8").strip()
        return content or None
    except FileNotFoundError:
        logging.error("Instructions file not found at %s", path)
    except OSError as exc:
        logging.error("Failed reading instructions file %s: %s", path, exc)
    return None


def _load_json_file(path: Path) -> Optional[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            logging.error("Schema file %s must contain a JSON object.", path)
            return None
        return data
    except FileNotFoundError:
        logging.error("Schema file not found at %s", path)
    except json.JSONDecodeError as exc:
        logging.error("Invalid JSON schema in %s: %s", path, exc)
    except OSError as exc:
        logging.error("Failed reading schema file %s: %s", path, exc)
    return None


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_json(value: dict[str, Any]) -> str:
    normalized = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _read_assistant_state() -> Optional[dict[str, Any]]:
    if not _state_path.exists():
        return None
    try:
        data = json.loads(_state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logging.error("Invalid assistant state file %s: %s", _state_path, exc)
        return None
    except OSError as exc:
        logging.error("Unable to read assistant state %s: %s", _state_path, exc)
        return None

    if not isinstance(data, dict):
        logging.error("Assistant state file %s must contain a JSON object.", _state_path)
        return None

    assistant_id = data.get("assistant_id")
    if assistant_id and isinstance(assistant_id, str):
        return data

    logging.error("Assistant state file %s missing valid assistant_id.", _state_path)
    return None


def _persist_assistant_state(state: dict[str, Any]) -> None:
    try:
        _state_path.parent.mkdir(parents=True, exist_ok=True)
        _state_path.write_text(
            json.dumps(state, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        logging.error("Unable to persist assistant ID to %s: %s", _state_path, exc)


async def get_assistant_id() -> Optional[str]:
    global _assistant_id

    instructions = await asyncio.to_thread(_load_text_file, _instructions_path)
    if not instructions:
        logging.error("Assistant instructions are required to create or update.")
        return None

    schema = await asyncio.to_thread(_load_json_file, _schema_path)
    if not schema:
        logging.error("Assistant JSON schema is required to create or update.")
        return None

    instructions_hash = _hash_text(instructions)
    schema_hash = _hash_json(schema)
    name_signature = (_assistant_name or "").strip()
    description_signature = (_assistant_description or "").strip()
    signature = (
        instructions_hash,
        schema_hash,
        _assistant_model,
        name_signature,
        description_signature,
    )

    async with _assistant_lock:
        global _cached_signature

        if _assistant_id and _cached_signature == signature:
            return _assistant_id

        cached_state = _read_assistant_state()
        cached_id = cached_state.get("assistant_id") if cached_state else None
        stored_signature = None
        if cached_state:
            stored_signature = (
                cached_state.get("instructions_hash"),
                cached_state.get("schema_hash"),
                cached_state.get("model"),
                (cached_state.get("name") or "").strip(),
                (cached_state.get("description") or "").strip(),
            )
        else:
            _assistant_id = None
            _cached_signature = None

        def _persist_from_assistant(assistant_obj) -> None:
            assistant_name = (getattr(assistant_obj, "name", None) or "").strip()
            assistant_description = (
                getattr(assistant_obj, "description", None) or ""
            ).strip()
            state = {
                "assistant_id": assistant_obj.id,
                "instructions_hash": instructions_hash,
                "schema_hash": schema_hash,
                "model": _assistant_model,
            }
            if assistant_name:
                state["name"] = assistant_name
            if assistant_description:
                state["description"] = assistant_description
            _persist_assistant_state(state)
            _cached_signature = signature

        response_format = {"type": "json_schema", "json_schema": schema}

        if cached_id and stored_signature == signature:
            _assistant_id = cached_id
            _cached_signature = signature
            return _assistant_id

        target_id = cached_id or None
        if target_id:

            update_request: dict[str, Any] = {
                "instructions": instructions,
                "response_format": response_format,
                "model": _assistant_model,
            }
            if _assistant_name:
                update_request["name"] = _assistant_name
            if _assistant_description:
                update_request["description"] = _assistant_description

            try:
                assistant = await asyncio.to_thread(
                    client.beta.assistants.update,
                    target_id,
                    **update_request,
                )
                _assistant_id = assistant.id
                _persist_from_assistant(assistant)
                logging.info("Updated assistant %s with new instructions/schema.", _assistant_id)
                return _assistant_id
            except Exception as exc:
                logging.warning(
                    "Failed to update assistant %s; recreating. Error: %s",
                    target_id,
                    exc,
                )

        create_request: dict[str, Any] = {
            "model": _assistant_model,
            "instructions": instructions,
            "response_format": response_format,
        }
        if _assistant_name:
            create_request["name"] = _assistant_name
        if _assistant_description:
            create_request["description"] = _assistant_description

        try:
            assistant = await asyncio.to_thread(
                client.beta.assistants.create, **create_request
            )
        except Exception as exc:
            logging.error("Failed to create assistant: %s", exc)
            return None

        _assistant_id = assistant.id
        _persist_from_assistant(assistant)
        logging.info("Created new assistant with id %s", _assistant_id)
        return _assistant_id


async def create_new_thread():
    """Create a new OpenAI thread."""
    try:
        thread = await asyncio.to_thread(client.beta.threads.create)
        return thread.id
    except Exception as exc:
        logging.error("Error creating thread: %s", exc)
        return None


async def check_run(thread_id, run_id):
    """Wait until an OpenAI run finishes."""
    while True:
        try:
            run = await asyncio.to_thread(
                client.beta.threads.runs.retrieve,
                thread_id=thread_id,
                run_id=run_id,
            )

            if run.status == "completed":
                break
            if run.status == "expired":
                logging.error("Run expired for thread %s", thread_id)
                break
            await asyncio.sleep(3)
        except Exception as exc:
            logging.error("Error checking run status: %s", exc)
            break


async def GPT_response(thread_id, prompt):
    """Send a prompt to the assistant and return the response payload."""
    try:
        await asyncio.to_thread(
            client.beta.threads.messages.create,
            thread_id=thread_id,
            role="user",
            content=prompt,
        )

        assistant_id = await get_assistant_id()
        if not assistant_id:
            return {
                "response": "Assistant configuration is incomplete. Check server logs.",
                "values": {},
            }

        run = await asyncio.to_thread(
            client.beta.threads.runs.create,
            thread_id=thread_id,
            assistant_id=assistant_id,
        )

        await check_run(thread_id, run.id)

        messages = await asyncio.to_thread(
            client.beta.threads.messages.list, thread_id=thread_id
        )
        if not messages.data:
            return {"response": "No response received", "values": {}}

        assistant_payload: Optional[dict[str, Any]] = None
        assistant_text: Optional[str] = None

        ordered_messages = sorted(
            messages.data,
            key=lambda msg: getattr(msg, "created_at", 0),
            reverse=True,
        )

        for message in ordered_messages:
            if getattr(message, "role", None) != "assistant":
                continue

            for part in getattr(message, "content", []):
                part_type = getattr(part, "type", None)

                if part_type == "output_json":
                    payload = getattr(part, "output_json", None)
                    if isinstance(payload, dict):
                        assistant_payload = payload
                        break
                    if payload is not None:
                        assistant_text = json.dumps(payload)
                        break

                text_block = getattr(part, "text", None)
                if text_block and getattr(text_block, "value", None):
                    assistant_text = text_block.value

            if assistant_payload or assistant_text:
                break

        if assistant_payload is not None:
            return assistant_payload

        if assistant_text:
            try:
                data = json.loads(assistant_text)
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                pass
            return {"response": assistant_text, "values": {}}

        return {"response": "No assistant response", "values": {}}
    except Exception as exc:
        logging.error("Error in GPT response: %s", exc)
        return {"response": "An error occurred while processing your request", "values": {}}


async def transcribe_audio(audio_bytes: bytes) -> str | None:
    """Transcribe WAV audio bytes using the configured OpenAI model."""
    try:
        result = client.audio.transcriptions.create(
            model=settings["transcription_model"],
            file=("speech.wav", audio_bytes, "audio/wav"),
            response_format="text",
            language="en",
        )
        return result if isinstance(result, str) else getattr(result, "text", None)
    except Exception as exc:
        logging.error("Error transcribing audio: %s", exc)
        return None

import os
from pathlib import Path


def _load_env_file(filename: str = ".env") -> None:
    env_path = Path(__file__).resolve().parent / filename
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        cleaned = value.strip()
        if cleaned and cleaned[0] == cleaned[-1] and cleaned[0] in {'"', "'"}:
            cleaned = cleaned[1:-1]
        cleaned = cleaned.replace("\\n", "\n")
        os.environ.setdefault(key.strip(), cleaned)


_load_env_file()
# Also attempt to load the root project's .env if available.
_load_env_file("../.env")


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _optional(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def _optional_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"Invalid integer for {name}: {value}") from exc


settings = {
    "broker": _require("MQTT_BROKER"),
    "topic": _require("MQTT_TOPIC"),
    "mqtt_user": _optional("MQTT_USER"),
    "mqtt_password": _optional("MQTT_PASSWORD"),
    "client_id": _optional("MQTT_CLIENT_ID", "windmill-assistant"),
    "mqtt_port": _optional_int("MQTT_PORT", 1883),
    "openAIToken": _require("OPENAI_API_KEY"),
    "assistant_id": _optional("OPENAI_ASSISTANT_ID"),
    "prompt_id": _optional("OPENAI_PROMPT_ID"),
    "prompt_instructions": _optional("PROMPT_INSTRUCTIONS"),
    "response_json_schema": {
        "name": "windmill_spin_data",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "response": {"type": "string"},
                "values": {
                    "type": "object",
                    "properties": {
                        "speed_para": {"type": "number"},
                        "dir_para": {"type": "integer"},
                        "speed_old": {"type": "number"},
                        "dir_old": {"type": "integer"},
                        "speed_reg": {"type": "number"},
                        "dir_reg": {"type": "integer"},
                    },
                    "required": [
                        "speed_para",
                        "dir_para",
                        "speed_old",
                        "dir_old",
                        "speed_reg",
                        "dir_reg",
                    ],
                    "additionalProperties": False,
                },
            },
            "required": ["response", "values"],
            "additionalProperties": False,
        },
    },
    "conversation_model": _optional("OPENAI_CONVERSATION_MODEL", "gpt-4.1-mini"),
    "openAIToken2": _optional("OPENAI_API_KEY_SECONDARY"),
    "telepotToken": _optional("TELEPOT_TOKEN"),
    "DB": _optional("SQLITE_DB"),
    "transcription_model": _optional("TRANSCRIPTION_MODEL", "gpt-4o-transcribe"),
    "Welcom_msg": _optional(
        "WELCOME_MESSAGE",
        "Hello! Ask a question to adjust the windmills.",
    ),
}

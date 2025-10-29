import os
from pathlib import Path


def _load_dotenv(dotenv_path: Path) -> None:
    """
    Populate os.environ with key/value pairs from a .env file when present.
    Duplicate keys keep the value that is already in the environment.
    """
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


_env_path = Path(__file__).resolve().parent / ".env"
_load_dotenv(_env_path)


settings = {
    "broker": _require("MQTT_BROKER"),
    "topic": os.getenv("MQTT_TOPIC", "wind"),
    "DB": os.getenv("DB_PATH", "WM.db"),
    "mqtt_user": _require("MQTT_USER"),
    "mqtt_password": _require("MQTT_PASSWORD"),
    "telepotToken": _require("TELEGRAM_BOT_TOKEN"),
    "client_id": os.getenv("MQTT_CLIENT_ID", "WM_Sender"),
    "openAIToken": _require("OPENAI_API_KEY_PRIMARY"),
    "assistant_id": _require("OPENAI_ASSISTANT_ID"),
    "openAIToken2": _require("OPENAI_API_KEY_SECONDARY"),
    "Welcom_msg": """👋 Hey! You're chatting with a bot that can reprogram the Windmill Sculpture! like ChatGPT but can also change the windmills' speed

💬 Start sending a message and see how it goes.

⚠️ We’d like to save your text for research purposes, if you are not sure, just type /consent and pick "yes" or "no".
🐢BTW it is a bit slower that common AI tools""",
}

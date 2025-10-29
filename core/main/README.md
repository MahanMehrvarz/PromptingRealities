# Core Assistant Runtime
The `core/main` directory hosts the baseline assistant used for the Prompting Realities windmill prototype. It wires together an OpenAI Assistant, an MQTT transport layer, and an audio-enabled command-line loop so you can prompt the sculpture in natural language and stream structured control messages to your hardware.

## Prerequisites
- Python 3.10 or newer.
- PortAudio development headers (required by `sounddevice`); install via Homebrew `brew install portaudio` or your platform's package manager before running `pip install`.
- An MQTT broker that your machine can reach (e.g., shiftr.io, Eclipse Mosquitto, or a local instance).
- An OpenAI API key with access to the Assistants (beta) and transcription endpoints.

## Installation & Environment
1. **Clone and enter the project**
   ```bash
   git clone https://github.com/MahanMehrvarz/PromptingRealities.git
   cd PromptingRealities/core/main
   ```
2. **Create a virtual environment (recommended)**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
3. **Install dependencies**
   ```bash
   pip install openai paho-mqtt sounddevice webrtcvad python-dotenv
   ```

These commands mirror the quick-start section in the repository root README and ensure the CLI can capture audio, call the OpenAI APIs, and publish to MQTT.

## Configure Credentials (`.env`)
Copy the sample environment file and replace placeholders with your own credentials:

```bash
cp .env.example .env
```

Open `.env` in an editor and fill in the required values. The keys below match what `settings.py` expects:

```ini
OPENAI_API_KEY=sk-YOUR_OPENAI_KEY
MQTT_BROKER=mqtt.example.com
MQTT_PORT=1883               # adjust if your broker uses a custom port
MQTT_TOPIC=wind
MQTT_USER=your-mqtt-username  # leave blank if broker allows anonymous access
MQTT_PASSWORD=your-mqtt-password
MQTT_CLIENT_ID=windmill-assistant

OPENAI_ASSISTANT_MODEL=gpt-4o-mini
OPENAI_ASSISTANT_NAME=Windmill Assistant
OPENAI_ASSISTANT_DESCRIPTION=Controls windmill presets via MQTT.
TRANSCRIPTION_MODEL=gpt-4o-transcribe
WELCOME_MESSAGE=Hello! Ask a question to adjust the windmills.

# Optional: override default file locations when you create your own versions
# OPENAI_ASSISTANT_INSTRUCTIONS_FILE=custom_instructions.md
# OPENAI_ASSISTANT_SCHEMA_FILE=custom_schema.json
# OPENAI_ASSISTANT_STATE_FILE=cache/assistant_state.json
```

- `OPENAI_API_KEY`, `MQTT_BROKER`, and `MQTT_TOPIC` are mandatory; the runtime raises an error if they are missing.
- `MQTT_USER`/`MQTT_PASSWORD` are optional; leave them empty for unsecured brokers.
- The `OPENAI_ASSISTANT_*` fields help the assistant cache and reuse a server-side configuration. Adjust them when you create your own instructions or schema files.
- If you change `assistant_instructions.md` or `assistant_response_schema.json`, update the corresponding environment variables so the assistant is recreated with your new materials.

## Running the Assistant
Once `.env` is configured:

```bash
python Simple-assistant.py
```

Startup sequence:
- The script prints the welcome message from `WELCOME_MESSAGE`.
- A short microphone calibration runs (for voice mode). If PortAudio is unavailable you can still use text mode.
- An OpenAI assistant is created or reused using `assistant_instructions.md` and `assistant_response_schema.json`. The resulting assistant ID is cached in `assistant_state.json`.
- The MQTT client attempts to connect using your broker credentials. If the connection fails, the CLI continues in prompt-only mode.

Command-line interaction (CML) operates in a continuous loop:
- Type prompts directly for **text mode**.
- Speak when **voice mode** is active; the audio is transcribed with the configured transcription model.
- Use slash commands at any time:
  - `/help` – list available commands.
  - `/restart` – start a new OpenAI thread (clears conversation context).
  - `/voice` / `/text` – switch between input modes.
  - `/dev` – preview MQTT payloads without publishing them.
  - `/quit` – exit the program.

Each user message results in a JSON payload from the assistant. The human-readable reply is shown on screen, and the structured `values` object is published to your MQTT topic unless dev mode is enabled or the connection is unavailable.

## Understanding the JSON Schema
`assistant_response_schema.json` defines the exact shape of the assistant's replies. It enforces two top-level keys:

- `response`: the short human-friendly sentence shown in the CLI.
- `values`: an object with six required fields describing the windmill states:
  - `speed_para`, `dir_para`
  - `speed_old`, `dir_old`
  - `speed_reg`, `dir_reg`

Speeds are floating-point numbers (0.0–0.95 in the default guidelines) and directions are integers restricted to `1` or `-1`. Your firmware subscribes to the configured MQTT topic and interprets these values to drive each windmill. When you adapt this project to new hardware, edit the schema so that it mirrors the fields your device requires, then point `OPENAI_ASSISTANT_SCHEMA_FILE` to the new JSON file.

## Crafting Assistant Instructions
`assistant_instructions.md` describes the fiction, tone, and behavioral constraints for the assistant. The supplied version teaches the agent how to guide visitors, limit responses to <20 words, and output torque-friendly speed values for the three windmills.

When creating your own artifact:
1. Rewrite the narrative so the assistant understands the appearance, capabilities, and limitations of your object.
2. Spell out safety or range constraints the JSON must respect (e.g., valid speed ranges, discrete modes).
3. Keep the instructions synced with the schema. If you add new JSON fields, explain how and when the assistant should populate them.
4. Remember the end user never sees the JSON—only the `response` text—so direct behavioral cues must live in the instructions.

After editing the instructions file, delete `assistant_state.json` (or point `OPENAI_ASSISTANT_STATE_FILE` to a new cache file) so the runtime creates a fresh assistant with your latest prompt.

## Conversation → MQTT Flow
1. **User input** (text or transcribed voice) is sent to the OpenAI Threads API.
2. The assistant, configured by your instructions and schema, returns a JSON object.
3. `Simple-assistant.py` prints the `response` string to the terminal, optionally displays the JSON in dev mode, and publishes the `values` object to your MQTT broker.
4. Your CircuitPython or microcontroller firmware listens to the topic, parses the JSON, and adjusts the physical artifact accordingly.

This cycle repeats, letting you iterate on conversational instructions and hardware behavior in tandem. Use the default configuration as a template, then tailor the instructions, schema, and firmware to match new tangible scenarios.

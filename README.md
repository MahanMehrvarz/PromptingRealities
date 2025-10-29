# Prompting Realities
**Exploring Prompting as an Interface for Tangible Artifacts**

Prompting Realities is a reusable experimental pipeline that links natural-language interaction to physical artifacts. It lets researchers, designers, and makers describe actions in plain language and have tangible devices carry them out through structured AI output.

The repository serves as both

- a research artifact expanding the work presented in *Prompting Realities: Exploring the Potentials of Prompting for Tangible Artifacts* (CHItaly 2025), and
- a technical framework for implementing your own LLM-driven tangible systems.

---

## Concept

At its core, the pipeline translates prompts into structured data and then into physical actuation.

```
User prompt
  |
  v
Large Language Model (LLM)
  |
  | produces JSON payload
  v
MQTT broker / local transport
  |
  v
Physical device (Arduino / ESP32 / other)
  |
  v
Tangible response
```

Each interaction loops through an LLM that interprets the user request (with guidance from `assistant_instructions.md`), emits machine-readable output (`assistant_response_schema.json`), and triggers real-world behavior through connected hardware.

---

## Folder Guide

- `core/` — Main implementation space with scripts and configuration for production-style assistants.
  - `core/main/` — Default assistant runtime for local experimentation, including schemas, state files, and entry-point scripts.
  - `core/TelegramBot-Integration/` — Telegram-focused runtime that mirrors the core logic and adds bot-specific wiring plus a lightweight SQLite database.
  - `core/.vscode/` — VS Code settings that keep linting and interpreter choices consistent across collaborators.
  - `core/.conda/` — Conda environment snapshot with pinned binaries and metadata for reproducing the runtime.
- `examples/` — Reference projects that show how to adapt the assistant for concrete scenarios.
  - `examples/RGBLED-assistant/` — Working demo that pairs the assistant with an Arduino RGB LED sketch, including Python glue code, firmware, and documentation.
- `.vscode/` — Workspace-wide editor configuration.
- `.conda/` — Root-level Conda environment mirror.
- `.gitignore` — Git rules that keep transient logs, environments, and generated files out of version control.

---

## Quick Start

1. **Clone the project**
   ```bash
   git clone https://github.com/MahanMehrvarz/PromptingRealities.git
   cd PromptingRealities/core/main
   ```
2. **Prepare a virtual environment**
   ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install openai paho-mqtt sounddevice webrtcvad python-dotenv
    cp .env.example .env
   ```
   Add your API key, MQTT broker details, and any custom parameters to `.env`.
3. **Run the assistant**
   ```bash
   python Simple-assistant.py
   ```
   The script listens for natural-language input and emits JSON payloads that can drive a connected device via MQTT.
4. **Test the RGB LED workflow**
   Visit `examples/RGBLED-assistant/README.md` for an end-to-end demo that combines the assistant runtime with Arduino firmware.

---

## Extending the Pipeline

1. **Describe the interaction model** — Update `assistant_instructions.md` with the behaviors your artifact should support.
2. **Shape the structured output** — Adjust `assistant_response_schema.json` to match the payload your firmware expects.
3. **Build or adapt firmware** — Program your microcontroller to parse that JSON and perform the intended action.
4. **Align the transport layer** — Configure MQTT (or your preferred channel) so topics and payloads match the assistant logic.
5. **Iterate through prompting** — Refine instructions, memory, and example interactions as you observe real-world usage.

The `examples/` directory provides a template you can clone and modify for new artifacts.

---

## Research Context

This repository accompanies the publication:

**Mahan Mehrvarz, Dave Murray-Rust, and Himanshu Verma.**  
*Prompting Realities: Exploring the Potentials of Prompting for Tangible Artifacts.*  
In *CHItaly 2025: 16th Biannual Conference of the Italian SIGCHI Chapter*, Salerno, Italy.  
[https://doi.org/10.1145/3750069.3750089](https://doi.org/10.1145/3750069.3750089)

The pipeline operationalizes the interaction model described in the paper and opens it up as a reusable framework.

---

## Next Steps

- Explore `core/main/` for the baseline assistant configuration and runtime scripts.
- Check `core/TelegramBot-Integration/` if you plan to deploy via Telegram.
- Start with `examples/RGBLED-assistant/` to see the full stack in action.
- Watch for upcoming docs in `core/main/docs/` covering architecture and extension guides.

---

## License

Specify your preferred license (for example MIT or CC BY-NC-ND 4.0).

---

Maintained by [Mahan Mehrvarz](https://github.com/MahanMehrvarz) — AI Futures Lab, TU Delft.


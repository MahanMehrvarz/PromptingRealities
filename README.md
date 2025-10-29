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

- `core/` - Main implementation space with scripts and configuration for production-style assistants.
  - `core/main/` - Default assistant runtime for local experimentation, including schemas, state files, and entry-point scripts. This is the exact codebase used for the windmill prototype described in the paper; reproducing its behavior requires recreating an equivalent hardware configuration.
  - `core/TelegramBot-Integration/` - Telegram-focused runtime that mirrors the core logic and adds bot-specific wiring plus a lightweight SQLite database.
  - `core/circuitpython/` - CircuitPython sketches and hardware notes that define the expected devices and MQTT payload handling.
- `examples/` - Reference projects that show how to adapt the assistant for concrete scenarios.
  - `examples/RGBLED-assistant/` - Working demo that pairs the assistant with an Arduino RGB LED sketch, including Python glue code, firmware, and documentation.
  - Use these examples as templates when adapting the pipeline to new hardware.
- `.gitignore` - Git rules that keep transient logs, environments, and generated files out of version control.

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
   The script listens for natural-language input and publishes MQTT messages to the broker and topic you configured in `.env`.
4. **Recreate the physical setup**
   Match the wiring and device properties defined in the CircuitPython reference found in `core/circuitpython/`. The hardware must interpret the MQTT payloads exactly as described there for the loop to function.

---

## Extending the Pipeline

1. **Describe the interaction model** - Update `assistant_instructions.md` with the behaviors your artifact should support; this is where the assistant agent learns about its appearance, capabilities, and how it should treat user messages.
2. **Shape the structured output** - Adjust `assistant_response_schema.json` to match the payload your firmware expects. Structured response formats are now native features in many modern language models; tailor the JSON schema so your microcontroller (Arduino, CircuitPython, etc.) can parse the MQTT message and update device values to trigger the correct physical actuation.
3. **Build or adapt firmware** - Program your microcontroller to parse that JSON and perform the intended action.
4. **Align the transport layer** - Configure MQTT (or your preferred channel) so topics and payloads match the assistant logic. Any broker will work, though the prototype uses [shiftr.io](https://shiftr.io/); if you are new to that service, this introduction is a useful primer: https://netart.ca/patterns/mqtt/introduction-to-shiftr-io/.
5. **Iterate through prompting** - Refine instructions, memory, and example interactions as you observe real-world usage. The CLI includes a `/help` command that lists shortcuts (such as toggling text/voice input or restarting the session); use these to test different conversational paths quickly, keeping in mind that restarting clears the conversation thread and removes prior context.

The `examples/` directory provides a template you can clone and modify for new artifacts.

---

## Publication

This repository accompanies the publication:

**Mahan Mehrvarz, Dave Murray-Rust, and Himanshu Verma.**  
*Prompting Realities: Exploring the Potentials of Prompting for Tangible Artifacts.*  
In *CHItaly 2025: 16th Biannual Conference of the Italian SIGCHI Chapter*, Salerno, Italy.  
[https://doi.org/10.1145/3750069.3750089](https://doi.org/10.1145/3750069.3750089)

The pipeline operationalizes the interaction model described in the paper and opens it up as a reusable framework.

---

## Next Steps

- Explore `core/main/` for the baseline assistant configuration and runtime scripts. This is useful in accuiring a deeper understanding of the paper and the windmill prototype.
- Check `core/TelegramBot-Integration/` if you plan to deploy via Telegram; this variant wraps the assistant a SQLite log so you can run multi-user chats, handle voice messages, and expose the same MQTT controls through Telegram application available on most of the operating systems.
- Start with `examples/RGBLED-assistant/` to see the full stack in action.

---


---

Maintained by [Mahan Mehrvarz](https://MahanMehrvarz.name) - AI Futures Lab, TU Delft.


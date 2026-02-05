# Examples

This folder contains example projects demonstrating AI-driven physical interactions using various microcontroller platforms. Each example showcases how to connect language models to real-world actuators (LEDs, motors, etc.) via MQTT.

## Folder Structure

```
examples/
├── Arduino/          # Examples using Arduino IDE
│   └── RGBLED/       # Voice/text controlled RGB LED
│
└── circuitpython/    # Examples using CircuitPython
    ├── RGBLED-SIngle/      # Single RGB LED control
    ├── RGBLED-dichotomy/   # Dual LED environmental indicators
    └── Vibration-Stories/  # Vibration motor patterns
```

---

## Arduino Examples

Examples designed for Arduino-compatible boards (ESP32, XIAO, etc.) using the Arduino IDE.

| Example | Description | Hardware |
|---------|-------------|----------|
| [RGBLED](Arduino/RGBLED/) | Voice and text controlled RGB LED with OpenAI integration, MQTT communication, and a p5.js browser simulator | ESP32 + NeoPixel |

---

## CircuitPython Examples

Examples designed for boards running CircuitPython. Each example includes:
- `board-files/` — Code to flash onto the microcontroller
- `instruction.txt` — AI assistant instructions
- `schema.json` — Response schema for structured outputs

| Example | Description | Hardware |
|---------|-------------|----------|
| [RGBLED-SIngle](circuitpython/RGBLED-SIngle/) | Single RGB LED controlled by natural language | CircuitPython board + NeoPixel |
| [RGBLED-dichotomy](circuitpython/RGBLED-dichotomy/) | Dual LED system representing environmental data (sea level + air quality) | CircuitPython board + 2 LEDs |
| [Vibration-Stories](circuitpython/Vibration-Stories/) | Vibration motor patterns generated from text prompts | CircuitPython board + Vibration motor |

---

## Common Architecture

All examples follow a similar pattern:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   User      │────▶│  AI Model   │────▶│    MQTT     │
│  (voice/    │     │  (OpenAI)   │     │   Broker    │
│   text)     │     └─────────────┘     └──────┬──────┘
└─────────────┘                                │
                                               ▼
                                    ┌─────────────────┐
                                    │  Microcontroller │
                                    │  (ESP32/Circuit- │
                                    │   Python board)  │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │    Actuator     │
                                    │  (LED, Motor,   │
                                    │    etc.)        │
                                    └─────────────────┘
```

---

## Getting Started

1. Choose an example based on your hardware platform
2. Follow the README or instructions in that example's folder
3. Configure your MQTT broker credentials
4. Flash the microcontroller code
5. Run the Python assistant to start interacting

---

## Adding New Examples

When contributing new examples, please follow this structure:

**For Arduino examples:**
```
Arduino/
└── YourExample/
    ├── README.md
    ├── your_sketch.ino
    └── ... (Python client, configs, etc.)
```

**For CircuitPython examples:**
```
circuitpython/
└── YourExample/
    ├── board-files/
    │   ├── code.py
    │   ├── settings.py
    │   └── lib/
    ├── instruction.txt
    └── schema.json
```

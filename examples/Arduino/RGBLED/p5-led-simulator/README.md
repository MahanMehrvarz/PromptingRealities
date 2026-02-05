# RGB LED Assistant – p5.js Visualizer
This sketch mirrors the behaviour of `rgb_led_arduino_demo.ino` so you can watch the LED updates without wiring any hardware. It subscribes to the same MQTT topic as the Arduino sketch and renders a single virtual pixel that reflects the incoming RGB and brightness values.

## Setup
1. **Install dependencies**  
   All libraries (p5.js and mqtt.js) are loaded from public CDNs, so you only need a static file server (e.g., `python -m http.server`) or the p5.js web editor.

2. **Configure MQTT credentials**  
   Copy the example config and fill in your broker information:
   ```bash
   cd examples/RGBLED-assistant/p5-led-simulator
   cp config.example.js config.js
   ```
   Edit `config.js` to match your MQTT endpoint and credentials. The file is ignored by Git so sensitive details stay local.

3. **Serve the files**  
   Launch a static server from this directory:
   ```bash
   python -m http.server 8080
   ```
   Visit `http://localhost:8080/` in a browser, or upload `index.html`, `sketch.js`, and your `config.js` into the p5.js web editor.

## How It Works
- `sketch.js` reads `window.PROMPTING_REALITIES_CONFIG` from `config.js`.
- On connect it subscribes to the configured topic (defaults to `Light`) and listens for payloads that match the Arduino JSON format: `{"led":[r,g,b,brightness]}`.
- Each message updates the simulated LED colour using the same brightness scaling as the NeoPixel library, meaning what you see on screen matches the physical LED output.
- If credentials are missing the sketch runs in an offline mode and simply shows the default LED state.

## Security Notes
- Keep real credentials out of version control—the root `.gitignore` already excludes `config.js`.
- Ensure your broker exposes a secure WebSocket endpoint (`wss://`) when connecting from the browser.
- The visualizer only consumes data; use a separate tool or script if you need to publish test messages.

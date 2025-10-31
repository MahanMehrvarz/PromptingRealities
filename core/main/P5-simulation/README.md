# Prompting Realities – p5.js Windmill Demo
This sketch mirrors the physical Prompting Realities windmills inside a browser. It listens to the same MQTT topic used by the hardware so you can visualize JSON responses emitted by the assistant without powering the sculpture.

## Setup
1. **Install dependencies**  
   The project pulls p5.js, p5.sound, and mqtt.js from CDN, so you only need a static file server (e.g., `python -m http.server`) or the p5.js web editor.

2. **Configure MQTT credentials**  
   Copy the example config and fill in your broker information:
   ```bash
   cd core/P5-demo
   cp config.example.js config.js
   ```
   Edit `config.js` and replace the placeholders with your MQTT endpoint, topic, and (optionally) username/password. The file is ignored by Git so your credentials stay local.

3. **Serve the files**  
   Launch a static server from the `core/P5-demo` directory:
   ```bash
   python -m http.server 8080
   ```
   Then open `http://localhost:8080/` in a browser. You can also drag `index.html` into the p5.js web editor and upload `sketch.js` plus your `config.js`.

## How It Works
- `sketch.js` reads `window.PROMPTING_REALITIES_CONFIG` defined in `config.js`.
- When valid credentials are present, it connects to the broker over WebSockets and subscribes to the configured topic.
- Incoming JSON messages are parsed and mapped to three virtual windmills that rotate according to `speed_*` and `dir_*` values.
- If no credentials are provided, the sketch runs in “MQTT disabled” mode and displays a warning in the developer console.

## Security Notes
- Never commit a real `config.js` to source control; the root `.gitignore` already excludes it.
- Brokers that require TLS, ACLs, or auth tokens should work as long as they expose a WebSocket endpoint.
- The demo only consumes data. If you need to publish test messages, use a separate tool so you do not hard-code write credentials here.

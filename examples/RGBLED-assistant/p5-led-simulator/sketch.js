/**
 * RGB LED MQTT Visualizer
 * Mirrors the behaviour of rgb_led_arduino_demo.ino in the browser.
 * Subscribes to MQTT messages that carry `{"led":[r,g,b,brightness]}` payloads
 * and renders a minimal 2D LED that reflects the received values.
 */

// --- MQTT SETTINGS ---
const CONFIG = window.PROMPTING_REALITIES_CONFIG || {};
const BROKER = CONFIG.broker || "";
const TOPIC = CONFIG.topic || "Light";
const MQTT_USER = CONFIG.username || "";
const MQTT_PASSWORD = CONFIG.password || "";

// --- LED STATE ---
const ledState = {
  r: 0,
  g: 0,
  b: 0,
  brightness: 0,
};

const DEFAULT_STATE = {
  r: 0,
  g: 255,
  b: 0,
  brightness: 200,
};

// --- GLOBALS ---
let client;
let connected = false;
let lastMsgTime = 0;

function setup() {
  createCanvas(420, 320);
  textFont("monospace");
  colorMode(RGB, 255);
  applyColor(DEFAULT_STATE);

  if (!BROKER) {
    console.warn(
      "No MQTT broker configured. Provide credentials in config.js to enable live updates."
    );
    return;
  }

  client = mqtt.connect(BROKER, {
    username: MQTT_USER || undefined,
    password: MQTT_PASSWORD || undefined,
  });

  client.on("connect", () => {
    connected = true;
    console.log("Connected to MQTT broker:", BROKER);
    client.subscribe(TOPIC);
  });

  client.on("message", (topic, message) => {
    try {
      const data = JSON.parse(message.toString());
      updateFromMQTT(data);
      lastMsgTime = millis();
    } catch (err) {
      console.error("Invalid MQTT message:", err);
    }
  });

  client.on("error", (err) => {
    console.error("MQTT connection error:", err);
    connected = false;
  });

  client.on("close", () => {
    console.warn("MQTT connection closed");
    connected = false;
  });
}

function draw() {
  background(18);
  drawLED();
  drawHUD();
}

function drawLED() {
  push();
  translate(width / 2, height / 2 - 10);
  const scale = ledState.brightness / 255;
  const displayColor = color(
    ledState.r * scale,
    ledState.g * scale,
    ledState.b * scale
  );

  stroke(50);
  strokeWeight(6);
  fill(10);
  ellipse(0, 0, 170, 170);

  noStroke();
  fill(displayColor);
  ellipse(0, 0, 140, 140);

  fill(255, 255, 255, 40);
  ellipse(-30, -40, 40, 30);
  pop();
}

// --- UPDATE FROM MQTT MESSAGE ---
function updateFromMQTT(data) {
  if (!data || !Array.isArray(data.led) || data.led.length < 4) return;
  const [r, g, b, brightness] = data.led;
  applyColor({ r, g, b, brightness });
}

function applyColor({ r, g, b, brightness }) {
  ledState.r = constrain(Number(r) || 0, 0, 255);
  ledState.g = constrain(Number(g) || 0, 0, 255);
  ledState.b = constrain(Number(b) || 0, 0, 255);
  ledState.brightness = constrain(Number(brightness) || 0, 0, 255);
}

// --- HUD / STATUS DISPLAY ---
function drawHUD() {
  noStroke();
  fill(220);
  textAlign(LEFT);
  textSize(14);

  text("RGB LED MQTT Visualizer", 20, 30);
  if (BROKER) {
    const status = connected ? "MQTT Connected" : "MQTT Disconnected";
    text(status, 20, 55);
    text(`Broker: ${BROKER}`, 20, 75);
    text(`Topic: ${TOPIC}`, 20, 95);
    if (connected) {
      const seconds = ((millis() - lastMsgTime) / 1000) | 0;
      text(`Last update: ${seconds}s ago`, 20, 115);
    }
  } else {
    text("MQTT disabled (no config)", 20, 55);
  }

  textSize(13);
  const colorLine = `RGB: (${ledState.r}, ${ledState.g}, ${ledState.b})`;
  const brightLine = `Brightness: ${ledState.brightness}`;
  text(colorLine, 20, height - 60);
  text(brightLine, 20, height - 40);
}

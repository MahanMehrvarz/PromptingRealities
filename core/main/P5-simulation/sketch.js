/**
 * Prompting Realities Virtual Windmills
 * MQTT version using mqtt.js (same as orientation example)
 *
 * To use:
 * 1. Include the mqtt.js library:
 *    <script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>
 * 2. Run in p5.js editor or a local HTML file.
 * 3. Subscribes to topic "wind" and animates 3 windmills.
 *    Accepts JSON messages of the form:
 *    {
 *      "speed_para": 0.5, "dir_para": 1,
 *      "speed_reg": 0.3, "dir_reg": -1,
 *      "speed_old": 1,   "dir_old": 1
 *    }
 */

// --- MQTT SETTINGS ---
const BROKER = "wss://ide-education.cloud.shiftr.io";
const MQTT_USER = "ide-education";
const MQTT_PASSWORD = "slpfhrGJNqRgA7Qw";
const TOPIC = "wind";

// --- GLOBALS ---
let client;
let connected = false;
let windmills = [];
let lastMsgTime = 0;

function setup() {
  createCanvas(800, 400);
  angleMode(DEGREES);
  textFont("monospace");

  // Create 3 virtual windmills
  windmills.push(new Windmill(200, 200, "Para", color(255, 180, 120)));
  windmills.push(new Windmill(400, 200, "Reg", color(120, 220, 255)));
  windmills.push(new Windmill(600, 200, "Old", color(180, 255, 180)));

  // Connect to MQTT broker
  client = mqtt.connect(BROKER, {
    username: MQTT_USER,
    password: MQTT_PASSWORD,
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
  background(240);

  // Draw ground
  stroke(180);
  line(0, 300, width, 300);

  // Update and render windmills
  for (let w of windmills) {
    w.update();
    w.display();
  }

  drawHUD();
}

// --- UPDATE FROM MQTT MESSAGE ---
function updateFromMQTT(d) {
  if (d.speed_para !== undefined) windmills[0].set(d.speed_para, d.dir_para);
  if (d.speed_reg !== undefined) windmills[1].set(d.speed_reg, d.dir_reg);
  if (d.speed_old !== undefined) windmills[2].set(d.speed_old, d.dir_old);
}

// --- WINDMILL CLASS ---
class Windmill {
  constructor(x, y, name, c) {
    this.x = x;
    this.y = y;
    this.name = name;
    this.color = c;
    this.angle = 0;
    this.speed = 0;
    this.dir = 1;
  }

  set(speed, dir) {
    if (speed !== undefined) this.speed = speed;
    if (dir !== undefined) this.dir = dir >= 0 ? 1 : -1;
  }

  update() {
    this.angle += this.speed * 10 * this.dir;
  }

  display() {
    push();
    translate(this.x, this.y);
    stroke(100);
    fill(180);
    rect(-6, 0, 12, 100);

    stroke(this.color);
    strokeWeight(3);
    fill(this.color);
    ellipse(0, 0, 18, 18);
    for (let i = 0; i < 4; i++) {
      let a = this.angle + i * 90;
      line(0, 0, cos(a) * 40, sin(a) * 40);
    }
    pop();

    noStroke();
    fill(50);
    textAlign(CENTER);
    text(this.name, this.x, this.y + 130);
  }
}

// --- HUD / STATUS DISPLAY ---
function drawHUD() {
  noStroke();
  fill(30);
  textAlign(LEFT);
  textSize(14);
  text("Prompting Realities — Virtual Windmills", 20, 25);
  text(connected ? "MQTT Connected" : "MQTT Disconnected", 20, 45);
  text(`Broker: ${BROKER}`, 20, 65);
  text(`Topic: ${TOPIC}`, 20, 85);
  if (connected) text(`Last update: ${(millis() - lastMsgTime) / 1000 | 0}s ago`, 20, 105);
}

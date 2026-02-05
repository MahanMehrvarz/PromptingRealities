#include <WiFi.h>
#include <PubSubClient.h>
#include <Adafruit_NeoPixel.h>
#include <ArduinoJson.h>

// WiFi
const char* ssid     = "connecting...";
const char* password = "changing";

// MQTT
const char* mqtt_broker   = "ide-education.cloud.shiftr.io";
const char* mqtt_user     = "ide-education";
const char* mqtt_password = "slpfhrGJNqRgA7Qw";
const char* mqtt_topic    = "Light";
const char* client_id     = "LED-receiver";

// NeoPixel
#define LED_PIN 6
#define NUM_LEDS 1
Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_RGB + NEO_KHZ800);

// Store current LED state
uint8_t currentR = 0;
uint8_t currentG = 0;
uint8_t currentB = 0;
uint8_t currentBrightness = 255;

WiFiClient espClient;
PubSubClient client(espClient);

bool sentInitialValue = false;

const char* start_json = "{\"led\":[0,255,0,200]}";

// ----------------------------------------------------------

void applyColor(uint8_t r, uint8_t g, uint8_t b, uint8_t brightness) {
  currentR = r;
  currentG = g;
  currentB = b;
  currentBrightness = brightness;

  strip.setBrightness(currentBrightness);

  if (currentBrightness == 0) {
    strip.clear();  // LED off
  } else {
    strip.setPixelColor(0, strip.Color(currentR, currentG, currentB));
  }

  strip.show();
}

// ----------------------------------------------------------

void callback(char* topic, byte* payload, unsigned int length) {
  StaticJsonDocument<128> doc;
  if (deserializeJson(doc, payload, length)) return;
  if (!doc.containsKey("led")) return;

  JsonArray arr = doc["led"];
  if (arr.size() < 4) return;

  uint8_t r = arr[0];
  uint8_t g = arr[1];
  uint8_t b = arr[2];
  uint8_t brightness = constrain((int)arr[3], 0, 255);

  applyColor(r, g, b, brightness);
}

// ----------------------------------------------------------

void ensureMQTT() {
  if (!client.connected()) {
    if (client.connect(client_id, mqtt_user, mqtt_password)) {
      client.subscribe(mqtt_topic);

      if (!sentInitialValue) {
        client.publish(mqtt_topic, start_json);
        sentInitialValue = true;
      }

    } else {
      delay(800);
    }
  }
  client.loop();
}

// ----------------------------------------------------------

void setup() {
  Serial.begin(115200);
  strip.begin();
  strip.setBrightness(255);
  strip.show();

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) delay(200);

  client.setServer(mqtt_broker, 1883);
  client.setCallback(callback);

  ensureMQTT();
}

// ----------------------------------------------------------

void loop() {
  ensureMQTT();
}
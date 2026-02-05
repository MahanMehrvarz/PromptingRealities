# --- Imports
import time
import json
import board
import neopixel
from MQTT import Create_MQTT
from settings import settings

# --- Variables
# D13 LED
pin_led_d13 = board.D13
num_leds_d13 = 1
led_d13 = neopixel.NeoPixel(
    pin_led_d13,
    num_leds_d13,
    auto_write=False,
    pixel_order=neopixel.GRBW,
)

# D7 LED
pin_led_d7 = board.D7
num_leds_d7 = 1
led_d7 = neopixel.NeoPixel(
    pin_led_d7,
    num_leds_d7,
    auto_write=False,
    pixel_order=neopixel.GRBW,
)

# Initial LED states: "[R, G, B, Brightness]"
led_states = {
    "led-d13": [255, 255, 255, 200],
    "led-d7": [255, 255, 0, 200],
}

# MQTT setup
client_id = settings["mqtt_clientid"]
mqtt_topic = settings.get("mqtt_topic", "led")
mqtt_client = Create_MQTT(client_id)


# --- Functions
def apply_single_led(led_object, values):
    """Apply [R, G, B, Brightness] to a single NeoPixel object."""
    if not isinstance(values, list) or len(values) != 4:
        return

    r, g, b, brightness = values

    # Brightness 0–255 -> 0.0–1.0
    led_object.brightness = max(0.0, min(1.0, brightness / 255.0))

    # With pixel_order=neopixel.GRBW, we still pass (R, G, B, W)
    led_object.fill((r, g, b, 0))
    led_object.show()


def apply_all_leds():
    """Apply current led_states to both LEDs."""
    apply_single_led(led_d13, led_states.get("led-d13", [0, 0, 0, 0]))
    apply_single_led(led_d7, led_states.get("led-d7", [0, 0, 0, 0]))


def on_message(client, topic, message):
    """Handle incoming MQTT messages to update LED colors."""
    global led_states
    try:
        data = json.loads(message)

        updated = False

        # Backwards compatibility: single "led" key controls D13
        if "led" in data and isinstance(data["led"], list) and len(data["led"]) == 4:
            led_states["led-d13"] = data["led"]
            updated = True

        # New keys: "led-d13" and/or "led-d7"
        if "led-d13" in data and isinstance(data["led-d13"], list) and len(data["led-d13"]) == 4:
            led_states["led-d13"] = data["led-d13"]
            updated = True

        if "led-d7" in data and isinstance(data["led-d7"], list) and len(data["led-d7"]) == 4:
            led_states["led-d7"] = data["led-d7"]
            updated = True

        if updated:
            apply_all_leds()
            print("Updated LEDs:", led_states)
        else:
            print("Received invalid LED payload:", data)
    except Exception as e:
        print("Error parsing MQTT message:", e)


# --- Setup
led_d13.fill((0, 0, 0, 0))
led_d13.show()
led_d7.fill((0, 0, 0, 0))
led_d7.show()

# Apply initial LED states
apply_all_leds()

# Configure MQTT callbacks and subscription
mqtt_client.on_message = on_message
mqtt_client.subscribe(mqtt_topic)
print("Subscribed to topic:", mqtt_topic)


# --- Main loop
while True:
    mqtt_client.loop(timeout=0.2)
    time.sleep(0.1)
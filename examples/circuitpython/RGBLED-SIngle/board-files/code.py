# --- Imports
import time
import json
import board
import neopixel
from MQTT import Create_MQTT
from settings import settings

# --- Variables
# Configure the pin here (any NeoPixel-capable pin)
LED_PIN = board.D13
NUM_LEDS = 1

led = neopixel.NeoPixel(
    LED_PIN,
    NUM_LEDS,
    auto_write=False,
    pixel_order=neopixel.GRBW,
)

# Current LED state: "[R, G, B, Brightness]"
led_state = [255, 255, 255, 200]

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


def apply_led():
    """Apply current state to the single LED."""
    apply_single_led(led, led_state)


def on_message(client, topic, message):
    """Handle incoming MQTT messages to update the LED color."""
    global led_state
    try:
        data = json.loads(message)

        # Expect messages like: {"led": [R, G, B, Brightness]}
        if "led" in data and isinstance(data["led"], list) and len(data["led"]) == 4:
            led_state = data["led"]
            apply_led()
            print("Updated led:", led_state)
        else:
            print("Received invalid LED payload:", data)
    except Exception as e:
        print("Error parsing MQTT message:", e)


# --- Setu
# Clear LED first
led.fill((0, 0, 0, 0))
led.show()

# Apply initial state
apply_led()

# Configure MQTT callbacks and subscription
mqtt_client.on_message = on_message
mqtt_client.subscribe(mqtt_topic)
print("Subscribed to topic:", mqtt_topic)


# --- Main loop
while True:
    mqtt_client.loop(timeout=0.2)
    time.sleep(0.1)
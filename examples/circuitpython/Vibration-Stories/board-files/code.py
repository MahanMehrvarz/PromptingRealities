# --- Imports
import time
import json
import board
import pwmio
from MQTT import Create_MQTT
from settings import settings

# --- Variables
vibration_motor = pwmio.PWMOut(board.D4)

# MQTT setup (topic must come from settings.py)
client_id = settings["mqtt_clientid"]
mqtt_topic = settings["mqtt_topic"]
mqtt_client = Create_MQTT(client_id)

# Queue for incoming patterns; each item is a list of [intensity, duration, pause]
pattern_queue = []


# --- Functions
def vibration_alarm(intensity, duration, pause):
    """Run one vibration note with given intensity (0–100), duration, and pause."""
    try:
        duty = int(float(intensity) * 65535 // 100)
    except (ValueError, TypeError):
        return

    # Clamp duty cycle
    duty = max(0, min(65535, duty))

    vibration_motor.duty_cycle = duty
    time.sleep(float(duration))           # Duration of vibration
    vibration_motor.duty_cycle = 0       # Disable vibration
    time.sleep(float(pause))             # Pause after vibration


def on_message(client, topic, message):
    """
    Handle incoming MQTT messages.

    Expected payloads (JSON):
      - [[100, 0.5, 0.5], [100, 0.5, 0.5], [100, 0.5, 0.5]]
      - {"pattern": [[100, 0.1, 0.1], [100, 0.1, 0.1], ...]}
      - [[100, 0.5, 0.25]]
    Each inner list is [intensity, duration, pause].
    """
    global pattern_queue
    try:
        data = json.loads(message)

        pattern = None
        # Direct list of notes
        if isinstance(data, list):
            pattern = data
        # Object with "pattern" field
        elif isinstance(data, dict) and "pattern" in data:
            pattern = data["pattern"]
        # Object with "MQTT_value": {"sequence": [...]}
        elif isinstance(data, dict) and "MQTT_value" in data:
            mv = data["MQTT_value"]
            if isinstance(mv, dict) and "sequence" in mv:
                pattern = mv["sequence"]
        # Object with top-level "sequence": [...]
        elif isinstance(data, dict) and "sequence" in data:
            pattern = data["sequence"]

        if not isinstance(pattern, list):
            print("Received invalid vibration payload:", data)
            return

        # Basic validation: list of triplets
        cleaned = []
        for note in pattern:
            if (
                isinstance(note, (list, tuple))
                and len(note) == 3
            ):
                cleaned.append(note)

        if not cleaned:
            print("No valid notes in payload:", data)
            return

        pattern_queue.append(cleaned)
        print("Queued vibration pattern:", cleaned)
    except Exception as e:
        print("Error parsing MQTT vibration message:", e)


# --- Setup
# Configure MQTT callbacks and subscription
mqtt_client.on_message = on_message
mqtt_client.subscribe(mqtt_topic)
print("Subscribed to topic:", mqtt_topic)


# --- Main loop
while True:
    # Process MQTT traffic
    mqtt_client.loop(timeout=0.2)

    # If there is a queued pattern, play it
    if pattern_queue:
        current_pattern = pattern_queue.pop(0)
        for note in current_pattern:
            intensity, duration, pause = note
            vibration_alarm(intensity, duration, pause)

    time.sleep(0.1)

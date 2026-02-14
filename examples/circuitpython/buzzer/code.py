# --- Imports
import time
import json
import board
import pwmio
from MQTT import Create_MQTT
from settings import settings

# --- Variables
piezo_buzzer = pwmio.PWMOut(board.D4, variable_frequency=True)

# ~10% duty cycle for cleaner tone
DUTY_CYCLE = int(0.1 * 65535)

# MQTT setup
client_id = settings["mqtt_clientid"]
mqtt_topic = settings["mqtt_topic"]
mqtt_client = Create_MQTT(client_id)

# Queue for incoming melodies; each item is a list of [pitch_hz_or_0, duration_seconds]
pattern_queue = []


# --- Functions
def play_event(pitch_hz, duration_s):
    """Play one event: [pitch_hz_or_0_for_rest, duration_seconds]."""
    try:
        pitch = float(pitch_hz)
        dur = float(duration_s)
    except (ValueError, TypeError):
        return

    # Clamp duration to a sane range (defensive)
    dur = max(0.0, min(3.0, dur))

    # REST (silence)
    if pitch <= 0:
        piezo_buzzer.duty_cycle = 0
        time.sleep(dur)
        return

    # Tone
    piezo_buzzer.frequency = int(pitch)
    piezo_buzzer.duty_cycle = DUTY_CYCLE
    time.sleep(dur)

    # Turn off immediately after the note (no explicit pause in the new format)
    piezo_buzzer.duty_cycle = 0


def on_message(client, topic, message):
    """
    Handle incoming MQTT messages.

    Accepted payloads:
      - [[440, 0.5], [0, 0.25], [494, 0.5]]
      - {"sequence": [[440, 0.5], ...]}
      - {"MQTT_value": {"sequence": [[440, 0.5], ...]}}

    Each inner list is [pitch_hz_or_0_for_rest, duration_seconds].
    """
    global pattern_queue
    try:
        data = json.loads(message)
        pattern = None

        # Direct list of events
        if isinstance(data, list):
            pattern = data

        # Object with "sequence"
        elif isinstance(data, dict) and "sequence" in data:
            pattern = data["sequence"]

        # Object with MQTT_value -> sequence
        elif isinstance(data, dict) and "MQTT_value" in data:
            mv = data["MQTT_value"]
            if isinstance(mv, dict) and "sequence" in mv:
                pattern = mv["sequence"]

        if not isinstance(pattern, list):
            print("Invalid melody payload:", data)
            return

        # Validate list of pairs
        cleaned = []
        for ev in pattern:
            if isinstance(ev, (list, tuple)) and len(ev) == 2:
                cleaned.append(ev)

        if not cleaned:
            print("No valid melody events:", data)
            return

        pattern_queue.append(cleaned)
        print("Queued melody:", cleaned)

    except Exception as e:
        print("Error parsing MQTT melody message:", e)


# --- Setup
mqtt_client.on_message = on_message
mqtt_client.subscribe(mqtt_topic)
print("Subscribed to topic:", mqtt_topic)


# --- Main loop
while True:
    mqtt_client.loop(timeout=0.2)

    if pattern_queue:
        current_pattern = pattern_queue.pop(0)
        for ev in current_pattern:
            pitch_hz, duration_s = ev
            play_event(pitch_hz, duration_s)

    time.sleep(0.1)
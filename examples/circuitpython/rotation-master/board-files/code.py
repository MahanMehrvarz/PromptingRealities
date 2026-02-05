# --- Imports
import time
import json
import board
import pwmio
from adafruit_motor import servo
from MQTT import Create_MQTT
from settings import settings

# --- Variables
pwm = pwmio.PWMOut(board.D13, frequency=50)
servo_motor = servo.Servo(pwm, min_pulse=700, max_pulse=2600)
current_steps = []
step_index = 0
current_pause = 1.0  # Default pause between steps

# MQTT setup
client_id = settings["mqtt_clientid"]
mqtt_topic = settings.get("mqtt_topic", "servo")
mqtt_client = Create_MQTT(client_id)


# --- Functions
def on_message(client, topic, message):
    """Handle incoming MQTT messages to update servo steps."""
    global current_steps, step_index
    print(f"Received: {message}")
    try:
        # Parse JSON message like {"steps": [[0, 0.5], [90, 1.0], [180, 0.5]]}
        data = json.loads(message)
        if "steps" in data:
            current_steps = data["steps"]
            step_index = 0
            print(f"New steps loaded: {current_steps}")
    except Exception as e:
        print(f"Error parsing message: {e}")


# --- Setup
# Configure MQTT callbacks and subscription
mqtt_client.on_message = on_message
mqtt_client.subscribe(mqtt_topic)
print("Subscribed to topic:", mqtt_topic)


# --- Main loop
last_step_time = time.monotonic()

while True:
    mqtt_client.loop(timeout=0.2)

    # Execute servo steps if we have any
    if current_steps and step_index < len(current_steps):
        current_time = time.monotonic()
        if current_time - last_step_time >= current_pause:
            step = current_steps[step_index]
            angle = step[0]  # First value is angle
            current_pause = step[1]  # Second value is pause
            # Clamp angle to valid range
            angle = max(0, min(180, angle))
            servo_motor.angle = angle
            print(f"Servo angle: {angle}, pause: {current_pause}s")
            step_index += 1
            last_step_time = current_time

    # Release servo after sequence completes (stops the buzzing/straining)
    elif current_steps and step_index >= len(current_steps):
        servo_motor.angle = None  # Release the servo
        current_steps = []  # Clear the sequence
        print("Sequence complete, servo released")

    time.sleep(0.1)

import time
import board
from adafruit_motorkit import MotorKit
from MQTT import Create_MQTT
from settings import settings
import json
from digitalio import DigitalInOut, Direction, Pull

# Initialize variables for the three motors
speed_para = 0.5
dir_para = 1
speed_reg = 0.5
dir_reg = 1
speed_old = 0.5
dir_old = 1
sleep = 0.1
i = 0

led = DigitalInOut(board.LED)
led.direction = Direction.OUTPUT

BLINK_INTERVAL = 1
last_blink_time = 0

# MQTT message handling function
def handle_message(client, topic, m):
    """
    This function is called whenever a new message is received on the subscribed MQTT topic.
    It processes the incoming message, extracts the variables, and updates them accordingly.
    :param client: The MQTT client instance.
    :param topic: The topic on which the message was received.
    :param m: The message payload.
    """
    global speed_para, dir_para, speed_reg, dir_reg, speed_old, dir_old, sleep, i

    print(f"New message on topic {topic}: {m}")

    try:
        # Clean up the message to avoid issues with extra whitespace or control characters
        cleaned_message = m.strip()
        print(f"Cleaned message: {cleaned_message}")

        # Attempt to parse the cleaned message payload as JSON
        data = json.loads(cleaned_message)
        print(f"JSON parsed successfully: {data}")

        # Extract and update the variables from the parsed JSON data
        if "speed_para" in data:
            speed_para = float(data["speed_para"])
            print(f"Updated speed_para (M1): {speed_para}")
        if "dir_para" in data:
            dir_para = int(data["dir_para"])
            print(f"Updated dir_para (M1): {dir_para}")
        if "speed_reg" in data:
            speed_reg = float(data["speed_reg"])
            print(f"Updated speed_reg (M2): {speed_reg}")
        if "dir_reg" in data:
            dir_reg = int(data["dir_reg"])
            print(f"Updated dir_reg (M2): {dir_reg}")
        if "speed_old" in data:
            speed_old = float(data["speed_old"])
            print(f"Updated speed_old (M3): {speed_old}")
        if "dir_old" in data:
            dir_old = int(data["dir_old"])
            print(f"Updated dir_old (M3): {dir_old}")
        if "sleep" in data:
            sleep = float(data["sleep"])
            print(f"Updated sleep: {sleep}")

        # Reset i when a new message is received
        i = 0

    except ValueError as e:
        print(f"JSON decode error: {e}")
        print(f"Original message content: {m}")  # Log the problematic message for debugging
        print(f"Cleaned message content: {cleaned_message}")  # Log the cleaned message
    except Exception as e:
        print(f"Failed to process message: {e}")

# MQTT Setup
client_id = settings["client_id"]

# Change the topic here to the desired MQTT topic
group_number = "wind"

# Create an MQTT client and set the message handling function
mqtt_client = Create_MQTT(client_id, handle_message)

# Subscribe to the specified topic
mqtt_client.subscribe(group_number)

kit = MotorKit(i2c=board.I2C())

while True:

    current_time = time.monotonic()  # Get the current time in seconds

    # Check if it's time to toggle the LED
    if current_time - last_blink_time >= BLINK_INTERVAL:
        led.value = not led.value  # Toggle the LED
        last_blink_time = current_time  # Update the last blink time

    try:
        # Process MQTT messages
        mqtt_client.loop(1)

        # Motor control logic
        if i < 200:
            print(i)

            # Adjust the speed for each motor based on direction
            adjusted_speed_para = speed_para * dir_para
            adjusted_speed_reg = speed_reg * dir_reg
            adjusted_speed_old = speed_old * dir_old

            # Control Motor 1 (M1)
            if -1 <= adjusted_speed_para <= 1:
                kit.motor1.throttle = adjusted_speed_para
            else:
                kit.motor1.throttle = 0

            # Control Motor 2 (M2)
            if -1 <= adjusted_speed_reg <= 1:
                kit.motor2.throttle = adjusted_speed_reg
            else:
                kit.motor2.throttle = 0

            # Control Motor 3 (M3)
            if -1 <= adjusted_speed_old <= 1:
                kit.motor3.throttle = adjusted_speed_old
            else:
                kit.motor3.throttle = 0

            time.sleep(sleep)  # Use the updated sleep value from MQTT
            i += 1
        else:
            # Ensure the motors stop after completing the iterations
            kit.motor1.throttle = 0
            kit.motor2.throttle = 0
            kit.motor3.throttle = 0

        time.sleep(0.01)  # Short sleep to prevent high CPU usage
    except Exception as e:
        print(f"Error occurred: {e}")
        time.sleep(1)  # Delay before retrying to avoid rapid retries in case of persistent errors

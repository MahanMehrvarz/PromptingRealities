# This file creates a simple interface for the miniMqtt broker.
import board
import busio
import time

from digitalio import DigitalInOut
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
import adafruit_minimqtt.adafruit_minimqtt as MQTT
legacy = True
try:
    import adafruit_connection_manager
    legacy = False
except ImportError:
    pass

import adafruit_requests

# Load the data for the Wi-Fi
try:
    from settings import settings
except ImportError:
    print("The file settings.py is missing, please add it!")
    raise


# Default connected function.
def connected(client, userdata, flags, rc):
    print("Connected to the mqtt broker.")


# Default disconnected function.
def disconnected(client, userdata, rc):
    print("Disconnected from the mqtt broker.")


# Default message handle function.
def message(client, topic, m):
    print("New message on topic {0}: {1}".format(topic, m))


# Creates a mqtt connection.
def Create_MQTT(client_id, message_handler=message, connection_handler=connected, disconnected_handler=disconnected):
    # Get the pins from the Wi-Fi module
    esp32_cs = DigitalInOut(board.D9)
    esp32_ready = DigitalInOut(board.D11)
    esp32_reset = DigitalInOut(board.D12)

    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

    if legacy:
        wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, settings)

        # Connect to Wi-Fi
        print("Connecting to WiFi...")
        wifi.connect()
        print("Connected!")
    else:
        print("Connecting to WiFi...")
        wifi_connecting = True
        while wifi_connecting:
            try:
                esp.connect_AP(settings["ssid"], settings["password"])
                wifi_connecting = False
            except ConnectionError as e:
                # Retry on failure, but show more details
                print(
                    "Couldn't connect to SSID '{}' (status: {}, error: {}), trying again.".format(
                        settings["ssid"], esp.status, e
                    )
                )
                time.sleep(2)
        print("Connected!")

    if legacy:
        # Initialize MQTT interface with the esp interface
        MQTT.set_socket(socket, esp)

        mqtt_client = MQTT.MQTT(
            client_id=client_id,
            broker=settings["broker"],
            username=settings["mqtt_user"],
            password=settings["mqtt_password"],
        )
    else:
        pool = adafruit_connection_manager.get_radio_socketpool(esp)
        ssl_context = adafruit_connection_manager.get_radio_ssl_context(esp)
        mqtt_client = MQTT.MQTT(
            client_id=client_id,
            broker=settings["broker"],
            username=settings["mqtt_user"],
            password=settings["mqtt_password"],
            socket_pool=pool,
            ssl_context=ssl_context,
            socket_timeout=.1
        )

    mqtt_client.on_connect = connection_handler
    mqtt_client.on_disconnect = disconnected_handler
    mqtt_client.on_message = message_handler

    print(f"Connection to mqtt broker {settings['broker']}")
    mqtt_client.connect()
    # This fixes the loop being blocking
    if legacy:
        mqtt_client._backwards_compatible_sock = True

    return mqtt_client

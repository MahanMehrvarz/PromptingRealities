"""Command-line chat application that wraps the OpenAI Responses workflow."""

import asyncio
import collections
import json
import select
import sys
import time
import wave
from io import BytesIO

import audioop
import paho.mqtt.client as mqtt
import sounddevice as sd
import webrtcvad

from settings import settings
from conversation_client import (
    conversation_response,
    create_new_conversation,
    transcribe_audio,
)

broker = settings["broker"]
port = settings.get("mqtt_port", 1883)
topic = settings["topic"]
mqtt_user = settings["mqtt_user"]
mqtt_password = settings["mqtt_password"]

# ---- Audio capture & VAD configuration ---------------------------------------

SAMPLE_RATE = 16000  # Hertz; PortAudio + VAD both operate well at 16 kHz.
FRAME_DURATION_MS = 30  # ms; VAD expects 10/20/30 ms frames.
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)
SILENCE_FRAMES_LIMIT = int(0.9 / (FRAME_DURATION_MS / 1000))
MAX_FRAMES = int(10 / (FRAME_DURATION_MS / 1000))
PRE_SPEECH_FRAMES = int(0.18 / (FRAME_DURATION_MS / 1000))
VOICE_WAIT_TIMEOUT = 8  # seconds before timing out while listening.
ENERGY_THRESHOLD = 300  # RMS energy gate for noisy rooms.
MIN_VOICE_FRAMES = int(0.35 / (FRAME_DURATION_MS / 1000))
POST_SPEECH_FRAMES = int(0.4 / (FRAME_DURATION_MS / 1000))

# ---- Mutable application state ------------------------------------------------

current_response_id = None  # Populated with the latest Responses API ID.
input_mode = "text"  # Either "text" or "voice".
voice_prompt_displayed = False  # Avoid spamming the mic prompt between turns.
dev_mode = False  # When True, MQTT payloads are printed instead of published.

vad = webrtcvad.Vad(3)
noise_floor = ENERGY_THRESHOLD


class MQTTClient:
    """Thin wrapper around paho-mqtt with async-friendly hooks."""

    def __init__(self):
        self.client = mqtt.Client(
            client_id=settings["client_id"],
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        if mqtt_user:
            self.client.username_pw_set(mqtt_user, password=mqtt_password)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.connected = asyncio.Event()

    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        code = getattr(reason_code, "value", reason_code)
        if code == 0:
            print("\nConnected to MQTT broker.")
            self.connected.set()
        else:
            print(f"\nMQTT connection failed with code {code}.")
            self.connected.clear()

    def on_disconnect(self, client, userdata, reason_code, properties=None):
        code = getattr(reason_code, "value", reason_code)
        if code not in (0, None):
            print(f"\nMQTT disconnected unexpectedly (code {code}).")
        self.connected.clear()

    async def connect(self):
        """Establish a connection to the broker and wait until it is ready."""
        try:
            self.client.connect(broker, port, keepalive=60)
            self.client.loop_start()
            try:
                await asyncio.wait_for(self.connected.wait(), timeout=5)
                return True
            except asyncio.TimeoutError:
                print("MQTT connection timed out.")
                return False
        except Exception as exc:
            print(f"Unable to connect to MQTT broker: {exc}")
            return False

    async def disconnect(self):
        if self.client.is_connected():
            self.client.loop_stop()
            self.client.disconnect()

    async def publish(self, payload: str):
        """Ship a JSON payload to the configured topic if connected."""
        if not self.connected.is_set():
            print("Skipping MQTT publish; not connected.")
            return False
        try:
            self.client.publish(topic, payload)
            print("\n")
            print("////To see preset commands type /help")
            return True
        except Exception as exc:
            print(f"Failed to publish MQTT message: {exc}")
            return False


async def restart_conversation():
    """Reset identifiers so the next turn starts a fresh server-side session."""
    global current_response_id
    current_response_id = create_new_conversation()
    print("\nStarted new conversation.")
    return True


def calibrate_noise_floor(duration: float = 1.0) -> int | None:
    """Measure ambient RMS level to improve speech gating.

    We sample the microphone for a short window and average the raw RMS energy.
    That value feeds into the dynamic VAD threshold so the app adapts to quiet
    offices and louder factory floors alike.
    """
    frames_needed = max(1, int(duration * SAMPLE_RATE / FRAME_SIZE))
    energies: list[int] = []

    try:
        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=FRAME_SIZE,
            dtype="int16",
            channels=1,
        ) as stream:
            for _ in range(frames_needed):
                frame, _ = stream.read(FRAME_SIZE)
                if not frame:
                    continue
                energy = audioop.rms(frame, 2)
                energies.append(energy)
    except sd.PortAudioError as exc:
        print(f"Calibration audio error: {exc}")
        return None

    if not energies:
        return None

    avg_energy = sum(energies) / len(energies)
    return max(int(avg_energy), ENERGY_THRESHOLD // 2)


def record_voice_once() -> bytes | None:
    """Capture a single utterance using VAD-controlled recording.

    Frames hit a ring buffer until VAD detects speech.  Once triggered we keep
    recording until either the speaker pauses for ``SILENCE_FRAMES_LIMIT`` or we
    reach ``MAX_FRAMES`` worth of audio.  The result is raw PCM bytes which are
    later wrapped into a WAV container.
    """
    ring_buffer = collections.deque(maxlen=PRE_SPEECH_FRAMES)
    post_buffer = collections.deque(maxlen=POST_SPEECH_FRAMES)
    voiced_frames: list[bytes] = []
    voiced_energies: list[int] = []
    silence_frames = 0
    triggered = False
    start_time = time.time()
    dynamic_threshold = max(ENERGY_THRESHOLD, int(noise_floor * 2))

    try:
        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=FRAME_SIZE,
            dtype="int16",
            channels=1,
        ) as stream:
            while True:
                frame, _ = stream.read(FRAME_SIZE)
                if not frame:
                    continue

                energy = audioop.rms(frame, 2)
                is_voiced = energy >= dynamic_threshold and vad.is_speech(frame, SAMPLE_RATE)

                if not triggered:
                    ring_buffer.append((frame, energy))
                    if is_voiced:
                        triggered = True
                        for buffered_frame, buffered_energy in ring_buffer:
                            voiced_frames.append(buffered_frame)
                            voiced_energies.append(buffered_energy)
                        ring_buffer.clear()
                        silence_frames = 0
                    elif time.time() - start_time > VOICE_WAIT_TIMEOUT:
                        return None
                    continue

                if is_voiced:
                    voiced_frames.append(frame)
                    voiced_energies.append(energy)
                    silence_frames = 0
                    post_buffer.clear()
                else:
                    post_buffer.append(frame)
                    silence_frames += 1
                    if silence_frames > SILENCE_FRAMES_LIMIT:
                        voiced_frames.extend(post_buffer)
                        post_buffer.clear()
                        break

                if len(voiced_frames) > MAX_FRAMES:
                    voiced_frames.extend(post_buffer)
                    post_buffer.clear()
                    break

    except sd.PortAudioError as exc:
        print(f"Audio input error: {exc}")
        return None

    if not voiced_frames or len(voiced_frames) < MIN_VOICE_FRAMES:
        return None

    if not voiced_energies:
        return None

    avg_voiced_energy = sum(voiced_energies) / len(voiced_energies)
    if avg_voiced_energy < dynamic_threshold * 1.1:
        return None

    return b"".join(voiced_frames)


def pcm_to_wav(pcm_data: bytes, sample_rate: int = SAMPLE_RATE) -> bytes:
    """Wrap raw PCM data in a WAV container."""
    buffer = BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buffer.getvalue()


async def handle_command(command, mqtt_client):
    """Process slash-commands that control app state instead of chatting."""
    global input_mode, voice_prompt_displayed, dev_mode

    if command == "/help":
        print(
            "\nCommands:\n"
            "/help    Show this message\n"
            "/restart Start a new conversation session\n"
            "/voice   Switch to voice mode\n"
            "/text    Switch to text mode\n"
            "/dev     Enable dev mode (text + MQTT preview)\n"
            "/quit    Exit the program"
        )
        return True

    if command == "/restart":
        await restart_conversation()
        return True

    if command == "/voice":
        input_mode = "voice"
        dev_mode = False
        voice_prompt_displayed = False
        print("\nVoice mode enabled. Speak after the prompt.")
        return True

    if command == "/text":
        input_mode = "text"
        dev_mode = False
        voice_prompt_displayed = False
        print("\nText mode enabled. Type your message.")
        return True

    if command == "/dev":
        input_mode = "text"
        dev_mode = True
        voice_prompt_displayed = False
        print("\nDev mode enabled. Text replies will show MQTT payloads without sending. Type /text to exit dev mode.")
        return True

    if command == "/quit":
        print("Goodbye!")
        if mqtt_client:
            await mqtt_client.disconnect()
        sys.exit(0)

    return False


async def process_user_message(message: str, mqtt_client, *, dev_mode: bool = False):
    """Send a user message to the model and reflect the structured response."""
    global current_response_id

    payload, new_response_id = await conversation_response(current_response_id, message)

    if new_response_id:
        current_response_id = new_response_id

    text = payload.get("response", "")
    values = payload.get("values", {})

    print(f"\nAssistant: {text}")

    if values:
        payload = json.dumps(values, indent=2 if dev_mode else None)
        if mqtt_client and not dev_mode:
            await mqtt_client.publish(payload)
        elif not dev_mode:
            print("To see preset commands type /help")
        if dev_mode:
            print("\n[DEV] MQTT payload preview:")
            print(payload)
            if current_response_id:
                print(f"[DEV] Last response id: {current_response_id}")


async def chat_loop(mqtt_client):
    """Main event loop: collect input, call the model, and fan out results."""
    global voice_prompt_displayed, input_mode, dev_mode

    loop = asyncio.get_event_loop()

    while True:
        try:
            if input_mode == "text":
                voice_prompt_displayed = False
                user_input = await loop.run_in_executor(
                    None, lambda: input("\nYou: ").strip()
                )
                if not user_input:
                    continue

                if user_input.startswith("/"):
                    if await handle_command(user_input, mqtt_client):
                        continue

                await process_user_message(user_input, mqtt_client, dev_mode=dev_mode)
                continue

            if input_mode == "voice":
                # Allow typed commands/messages even while in voice mode.
                readable, _, _ = select.select([sys.stdin], [], [], 0)
                if sys.stdin in readable:
                    typed = sys.stdin.readline().strip()
                    if not typed:
                        continue
                    print(f"\nYou (text): {typed}")
                    if typed.startswith("/"):
                        if await handle_command(typed, mqtt_client):
                            continue
                    else:
                        input_mode = "text"
                        voice_prompt_displayed = False
                        print("\nSwitched to text mode based on typed input.")
                        dev_mode = False
                    await process_user_message(typed, mqtt_client, dev_mode=dev_mode)
                    continue

            if input_mode == "voice" and not voice_prompt_displayed:
                print("\n🎤 Voice mode active. Speak clearly and pause to send.")
                voice_prompt_displayed = True

            if input_mode == "voice":
                pcm_data = await asyncio.to_thread(record_voice_once)
            else:
                # Should not reach here in text mode due to continue above.
                pcm_data = None

            if not pcm_data:
                continue

            wav_bytes = pcm_to_wav(pcm_data)
            transcript = await transcribe_audio(wav_bytes)
            if not transcript:
                print("Didn't catch that. Try again.")
                continue

            message = transcript.strip()
            if not message:
                continue

            print(f"\nYou (voice): {message}")

            if message.startswith("/"):
                if await handle_command(message, mqtt_client):
                    continue

            await process_user_message(message, mqtt_client, dev_mode=dev_mode)
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as exc:
            print(f"\nError: {exc}")


async def main():
    """Application entry point: init hardware, start MQTT, then chat."""
    global noise_floor

    print(settings["Welcom_msg"])

    try:
        print("Calibrating microphone... please remain silent.")
        measured = await asyncio.to_thread(calibrate_noise_floor)
        if measured:
            noise_floor = measured
            print(f"Calibrated ambient noise level: {noise_floor:.0f}")
    except Exception as exc:
        print(f"Microphone calibration failed: {exc}")

    if not await restart_conversation():
        print("Failed to create a conversation. Exiting.")
        return

    mqtt_client = MQTTClient()
    if not await mqtt_client.connect():
        print("Continuing without MQTT publishing.")
        mqtt_client = None

    await chat_loop(mqtt_client)

    if mqtt_client:
        await mqtt_client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")
    except Exception as exc:
        print(f"\nProgram terminated due to error: {exc}")

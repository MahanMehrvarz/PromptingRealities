import time
import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ContentType
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Router
from aiogram.filters import Command  # Import Command filter for handling commands
import logging
import paho.mqtt.client as mqtt
import sys
import os
import aiohttp  # Import aiohttp to handle HTTP requests
import json
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters.callback_data import CallbackData
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Global variable to track last message sent time
last_message_time = None
mqtt_timeout_seconds = 60  # Adjust this value (in seconds) as needed for your timeout

# Add the directory containing OpenAiClientAssistant.py to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

from OpenAiClientAssistant import reset_user, GPT_response, whisper_transcribe, blind_response, create_new_thread, get_thread_id_and_user_id, save_conversation, save_user_and_thread_id
from settings import settings

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize the Telegram Bot with your token
bot = Bot(token=settings["telepotToken"])
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

# MQTT settings
broker = settings["broker"]
port = 1883
topic = settings["topic"]
mqtt_user = settings["mqtt_user"]
mqtt_password = settings["mqtt_password"]

# MQTT Client setup
clientQ = mqtt.Client(client_id=settings["client_id"])
clientQ.username_pw_set(mqtt_user, password=mqtt_password)

async def monitor_mqtt_connection():
    global last_message_time
    while True:
        try:
            # Send a ping to keep the connection alive
            clientQ.loop()
            if last_message_time and (time.time() - last_message_time) > mqtt_timeout_seconds:
                print("No MQTT message sent recently. Reconnecting...")
                clientQ.reconnect()  # Attempt to reconnect
                print("Reconnected to MQTT broker.")
                last_message_time = time.time()  # Reset the timer after reconnection
            await asyncio.sleep(10)  # Sleep for 10 seconds before the next check
        except Exception as e:
            print(f"Error in MQTT monitoring: {e}")
            await asyncio.sleep(30)  # Wait longer before retrying if there's an error

def on_connect(clientQ, userdata, flags, rc):
    if rc == 0:
        print("Connected successfully to MQTT broker")
    else:
        print(f"Connection failed with code {rc}")

def on_disconnect(clientQ, userdata, rc):
    if rc != 0:
        print("Unexpected disconnection. Will attempt to reconnect.")
        try:
            clientQ.loop_stop()  # Stop the current loop
            clientQ.disconnect()  # Ensure the client is fully disconnected
            clientQ.reconnect()   # Try to reconnect
            print("Reconnected successfully.")
            clientQ.loop_start()  # Restart the loop after reconnecting
        except Exception as e:
            print(f"Reconnection attempt failed: {e}")


# Asynchronous function to establish a connection to the broker with retries
async def connect_with_retries(clientQ, broker, port, max_retries=5):
    retries = 0
    while retries < max_retries:
        try:
            clientQ.connect(broker, port, keepalive=60)  # Try connecting
            clientQ.loop_start()  # Start the MQTT loop
            print("Connected to MQTT broker.")
            return
        except Exception as e:
            print(f"Connection attempt {retries + 1} failed: {e}")
            retries += 1
            await asyncio.sleep(2 ** retries)  # Exponential backoff
    print("Failed to connect after multiple attempts. Exiting.")
    exit(1)

clientQ.on_connect = on_connect
clientQ.on_disconnect = on_disconnect


# Command handler for /resetuser
@router.message(Command(commands=["resetuser"]))
async def reset_user_command(message: types.Message):
    chat_id = message.chat.id

    # Reset user and create a new thread (returns new_user_id and new_thread_id)
    new_user_id, new_thread_id = await reset_user(chat_id, db_connection)

    if new_user_id and new_thread_id:
        # Save the new user_id and thread_id immediately after reset
        await save_user_and_thread_id(chat_id, new_user_id, new_thread_id, db_connection)
        print(f"New user ID {new_user_id} and thread ID {new_thread_id} saved for chat_id {chat_id}")

        # Fetch the latest thread_id and user_id after saving it to ensure consistency
        refetched_thread_id, refetched_user_id = await get_thread_id_and_user_id(chat_id, db_connection)
        print(f"Refetched thread ID after reset: {refetched_thread_id}, Refetched user ID: {refetched_user_id}")

        # Ensure that the refetched ID matches the newly created one
        if refetched_thread_id == new_thread_id and refetched_user_id == new_user_id:
            print(f"Thread ID {new_thread_id} and User ID {new_user_id} correctly updated for chat_id {chat_id}")

            # Escape special characters for Markdown
            def escape_markdown(text: str) -> str:
                return (text.replace("_", "\\_")
                            .replace("*", "\\*")
                            .replace("[", "\\[")
                            .replace("]", "\\]")
                            .replace("(", "\\(")
                            .replace(")", "\\)")
                            .replace("`", "\\`")
                            .replace("~", "\\~")
                            .replace(">", "\\>")
                            .replace("#", "\\#")
                            .replace("+", "\\+")
                            .replace("-", "\\-")
                            .replace("=", "\\=")
                            .replace("|", "\\|")
                            .replace("{", "\\{")
                            .replace("}", "\\}")
                            .replace(".", "\\.")
                            .replace("!", "\\!"))

            escaped_user_id = escape_markdown(new_user_id)
            escaped_thread_id = escape_markdown(new_thread_id)

            # Inform the user that the user ID and thread have been reset
            await message.answer(
                f"**UserID has been changed to {escaped_user_id} with new thread {escaped_thread_id}.**", 
                parse_mode="Markdown"
            )
        else:
            # If the refetched thread_id doesn't match, inform and log the mismatch
            print(f"Mismatch: saved thread_id {new_thread_id}, but refetched thread_id {refetched_thread_id}")
            await message.answer("There was an issue resetting your user ID.")

    else:
        await message.answer("There was an error resetting your user ID.")

# Command handler for /start
@router.message(Command(commands=["start"]))
async def start_command(message: types.Message):
    chat_id = message.chat.id

    # Define the static welcome message
    welcome_message = settings["Welcom_msg"]

    # Send the welcome message
    await bot.send_message(chat_id=chat_id, text=welcome_message)


# Adding consent functionality
class ConsentCallback(CallbackData, prefix="consent"):
    action: str

@router.message(Command(commands=["consent"]))
async def consent_command(message: types.Message):
    chat_id = message.chat.id

    # Define the consent text
    consent_text = f"""
📄 Research Consent Form

This research study is about how people use chatbots to re-program  physical object.

Your participation is voluntary, and you can withdraw at any time.

Please respond with Yes or No to all of the following:

🤝 I agree to participate, knowing I can stop at any time without giving a reason.


⬇️ I understand that participating means:

🤖 Controlling a device by talking to a chatbot
📱 Using my phone to connect to a web app or a Telegram bot (if I want)
📞 Using a provided phone to connect to the chatbot (if I want)

⚠️ Risks:
- I might feel confused or bored if the chatbot's responses are unexpected or slow.

✅ Mitigation:
- I can pause or stop at any time, and the researcher will help if needed.

🔐 Data Privacy:
- No personal data will be collected; only the messages I send to the chatbot will be recorded.
- My identity (if i disclose) won't be shared beyond the main researcher (@mahi7mehr | m.mehrvarz@tudelft.nl)
- All messages will be deleted after the study ends.

📊 Publication:
- I understand the text of my messages to the chatbot may be used in research papers or presentations.
- I agree my input can be quoted anonymously.
"""

    # Create "Yes" and "No" buttons with the callback data
    yes_button = InlineKeyboardButton(
        text="Yes", 
        callback_data=ConsentCallback(action="yes").pack()
    )
    no_button = InlineKeyboardButton(
        text="No", 
        callback_data=ConsentCallback(action="no").pack()
    )
    
    # Create an inline keyboard with the Yes/No buttons
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[yes_button, no_button]])

    # Send the message with the paragraph and the inline buttons
    await message.answer(text=consent_text, reply_markup=keyboard)

# Callback query handler for consent Yes/No buttons
@router.callback_query(ConsentCallback.filter())

async def consent_callback_handler(callback_query: types.CallbackQuery, callback_data: ConsentCallback):
    action = callback_data.action

    if action == "yes":
        # Simulate a user message for giving consent
        simulated_message = types.Message(
            message_id=callback_query.message.message_id,
            chat=callback_query.message.chat,
            from_user=callback_query.from_user,
            date=callback_query.message.date,
            content_type=ContentType.TEXT,
            text="I give consent about using my messages for this research project."
        )
    elif action == "no":
        # Simulate a user message for not giving consent
        simulated_message = types.Message(
            message_id=callback_query.message.message_id,
            chat=callback_query.message.chat,
            from_user=callback_query.from_user,
            date=callback_query.message.date,
            content_type=ContentType.TEXT,
            text="I Do not give consent about using my messages for this research project"
        )

    # Call the handle_user_message function directly with the simulated message
    await handle_user_message(simulated_message)

    # Acknowledge the callback query to remove the loading spinner
    await callback_query.answer()


# Handling user messages for both text and voice
@router.message(F.content_type.in_([ContentType.TEXT, ContentType.VOICE]))
async def handle_user_message(message: types.Message):
    chat_id = message.chat.id
    message_id = message.message_id  # Unique ID for each user's message

    # Fetch the latest thread_id and user_id from the database
    thread_id, user_id = await get_thread_id_and_user_id(chat_id, db_connection)
    print(f"Handling message with thread_id: {thread_id} and user_id: {user_id} for chat_id {chat_id}, message_id {message_id}")

    if not thread_id or not user_id:
        # If no valid thread_id or user_id exists, create a new thread and user_id
        thread_id, user_id = await create_new_thread(chat_id, db_connection)

    # Check if the user message has already been logged using its message_id (prevent duplicate processing)
    query = "SELECT COUNT(*) FROM conversations WHERE message_id = ? AND chat_id = ?"
    cursor = await db_connection.execute(query, (str(message_id), chat_id))
    count = await cursor.fetchone()

    if count[0] > 0:
        print(f"User message {message_id} for chat_id {chat_id} has already been processed. Skipping.")
        return  # Avoid processing the same message again

    if message.content_type == ContentType.TEXT:
        prompt = message.text

        # Save the user message
        await save_conversation(chat_id, user_id, thread_id, settings["assistant_id"], "user", prompt, db_connection, message_id)

        # Generate assistant's response (it returns the full response including values)
        gpt_response = await GPT_response(prompt, chat_id, db_connection, message_id)
        
        # Extract the `response` (assistant's message) and `values` (MQTT payload) from the GPT response
        response_text = gpt_response.get("response", "")
        values = gpt_response.get("values", {})

        # Send the assistant's response back to the user via Telegram
        await bot.send_message(chat_id=chat_id, text=response_text, reply_to_message_id=message.message_id)

        # Send `values` to MQTT if available
        if values:
            print(f"Publishing values to MQTT topic {topic}: {values}")
            clientQ.publish(topic, json.dumps(values))
            print(f"Published to MQTT: {values}")

        # Save the assistant's response with the new message_id
        assistant_message_id = f"{message_id}_assistant"
        await save_conversation(chat_id, user_id, thread_id, settings["assistant_id"], "assistant", json.dumps(gpt_response), db_connection, assistant_message_id)

    elif message.content_type == ContentType.VOICE:
        file_id = message.voice.file_id
        blind_acknowledgment = await blind_response("write a casual text message no more than 10 words in response to someone who sent a voice message to you but you need a moment to first listen to it and then answer!")
        await bot.send_message(chat_id=chat_id, text=blind_acknowledgment, reply_to_message_id=message.message_id)

        # Process and transcribe the voice message
        file_info = await bot.get_file(file_id)
        file_path = file_info.file_path
        file_url = f"https://api.telegram.org/file/bot{settings['telepotToken']}/{file_path}"

        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                if response.status == 200:
                    with open("temp_voice.ogg", "wb") as f:
                        f.write(await response.read())

        transcription = await whisper_transcribe("temp_voice.ogg")

        if transcription:
            # Save the user transcription
            await save_conversation(chat_id, user_id, thread_id, settings["assistant_id"], "user", transcription, db_connection, message_id)

            # Generate assistant's response
            gpt_response = await GPT_response(transcription, chat_id, db_connection, message_id)

            # Extract the `response` (assistant's message) and `values` (MQTT payload) from the GPT response
            response_text = gpt_response.get("response", "")
            values = gpt_response.get("values", {})

            # Send the assistant's response back to the user via Telegram
            await bot.send_message(chat_id=chat_id, text=response_text, reply_to_message_id=message.message_id)

            # Send `values` to MQTT if available
            if values:
                print(f"Publishing values to MQTT topic {topic}: {values}")
                clientQ.publish(topic, json.dumps(values))
                print(f"Published to MQTT: {values}")

            # Save the assistant's response with the new message_id
            assistant_message_id = f"{message_id}_assistant"
            await save_conversation(chat_id, user_id, thread_id, settings["assistant_id"], "assistant", json.dumps(gpt_response), db_connection, assistant_message_id)
        else:
            await bot.send_message(chat_id=chat_id, text="Sorry, I couldn't understand the voice message.", reply_to_message_id=message.message_id)


async def main():
    global db_path
    global db_connection
    from OpenAiClientAssistant import init_db
    await init_db()  # This ensures the tables are created before interaction

    # Initialize the database and create necessary tables
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, settings["DB"])
    db_connection = await aiosqlite.connect(db_path)

    # Set the bot command list to include /resetuser, /start, and /consent
    await bot.set_my_commands([
        types.BotCommand(command="resetuser", description="Reset user ID and start a new thread"),
        types.BotCommand(command="start", description="Welcome and get started with the bot"),
        types.BotCommand(command="consent", description="Open consent form")  # Add /consent here
    ])

    # Connect to the MQTT broker with retries
    await connect_with_retries(clientQ, broker, port)

    # Start the MQTT monitoring task in the background
    asyncio.create_task(monitor_mqtt_connection())

    # Include the router into the dispatcher (for handling commands like /start, /resetuser, /consent)
    dp.include_router(router)

    # Start polling for Telegram messages
    await dp.start_polling(bot, skip_updates=True)

    # Close the database connection when done
    await db_connection.close()


if __name__ == "__main__":
    asyncio.run(main())

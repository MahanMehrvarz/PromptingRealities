#OpenAiClientAssistant.py
import time
import asyncio
import aiosqlite
from openai import OpenAI
import os
from datetime import datetime
import requests
import logging
import json
from settings import settings
import sqlite3
from settings import settings

# Initialize the OpenAI client
client = OpenAI(api_key=settings["openAIToken"], default_headers={"OpenAI-Beta": "assistants=v1"})
clientblind = OpenAI(api_key=settings["openAIToken2"])

os.path.dirname(os.path.abspath(__file__))
import sqlite3  # Add this to handle sqlite3 errors
import aiosqlite
import os

async def init_db():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, settings["DB"])

    async with aiosqlite.connect(db_path) as conn:
        # Step 1: Create the threads table (new_threads) without PRIMARY KEY constraint on chat_id
        await conn.execute('''CREATE TABLE IF NOT EXISTS new_threads (
                                chat_id INTEGER,  -- No primary key here
                                thread_id TEXT,
                                user_id TEXT)''')

        # Step 2: Commit the table creation to ensure it's created before any data manipulation
        await conn.commit()

        # Step 3: Copy the data from the old threads table to the new one, if the old table exists
        try:
            await conn.execute('''INSERT OR IGNORE INTO new_threads (chat_id, thread_id, user_id)
                                  SELECT chat_id, thread_id, user_id FROM threads''')
        except sqlite3.OperationalError:
            print("Old threads table does not exist, skipping data migration.")

        # Step 4: Drop the old threads table, if it exists
        await conn.execute('DROP TABLE IF EXISTS threads')

        # Step 5: Rename the new table to threads
        await conn.execute('ALTER TABLE new_threads RENAME TO threads')

        # Step 6: Create the conversations table, if it doesn't exist
        await conn.execute('''CREATE TABLE IF NOT EXISTS conversations
                             (id INTEGER PRIMARY KEY AUTOINCREMENT,
                              chat_id INTEGER,
                              user_id TEXT,
                              thread_id TEXT,
                              assistant_id TEXT,
                              sender TEXT,
                              message TEXT,
                              timestamp TEXT)''')

        # Step 7: Create necessary indexes
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_chat_id ON conversations (chat_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_thread_id ON conversations (thread_id)')

        # Step 8: Add the message_id column to conversations table if it doesn't exist
        try:
            # This will try to add the message_id column; if it already exists, it will raise an OperationalError
            await conn.execute('ALTER TABLE conversations ADD COLUMN message_id TEXT')
            await conn.commit()
            print("message_id column added to conversations table.")
        except sqlite3.OperationalError:
            # This error occurs if the column already exists, so it's safe to continue
            print("message_id column already exists or couldn't be added.")

        # Step 9: Commit all the changes
        await conn.commit()


async def blind_response(prompt):
    try:
        completion = clientblind.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        return None

async def whisper_transcribe(file_path):
    try:
        # Open the audio file in binary mode
        with open(file_path, "rb") as audio_file:
            # Create a transcription using the OpenAI API
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text",
                language="en"
            )
        return transcript
    except Exception as e:
        logging.error(f"An error occurred during transcription: {e}")
        return ""

async def handle_voice_message(file_id, bot, chat_id):
    """Handles downloading and transcribing voice messages."""
    file_path = (await bot.get_file(file_id)).file_path
    file_url = f"https://api.telegram.org/file/bot{settings['telepotToken']}/{file_path}"
    
    # Download the file from Telegram using requests
    response = requests.get(file_url)

    # Save the file locally
    with open("temp_voice.ogg", "wb") as f:
        f.write(response.content)

    # Transcribe the voice message using Whisper
    message_text = await whisper_transcribe("temp_voice.ogg")
    
    return message_text

async def get_thread_id_and_user_id(chat_id, db_connection):
    print(f"Fetching latest thread_id and user_id for chat_id {chat_id}")
    
    async with db_connection.execute('SELECT thread_id, user_id FROM threads WHERE chat_id = ? ORDER BY ROWID DESC LIMIT 1', (chat_id,)) as cursor:
        result = await cursor.fetchone()
    
    if result and result[0] and result[1]:  # Ensure both thread_id and user_id are present
        print(f"Latest thread_id and user_id for chat_id {chat_id}: {result[0]}, {result[1]}")
        return result
    else:
        # If thread_id or user_id is missing, log and return None, None
        print(f"No valid thread_id or user_id found for chat_id {chat_id}")
        return None, None

async def save_user_and_thread_id(chat_id, new_user_id, new_thread_id, db_connection):
    await db_connection.execute(
        'INSERT OR REPLACE INTO threads (chat_id, user_id, thread_id) VALUES (?, ?, ?)', 
        (chat_id, new_user_id, new_thread_id)
    )
    await db_connection.commit()
    print(f"Saved user ID {new_user_id} and thread ID {new_thread_id} for chat_id {chat_id}")


# Function to save thread_id
async def save_thread_id(chat_id, thread_id, db_connection):
    await db_connection.execute('INSERT OR REPLACE INTO threads (chat_id, thread_id) VALUES (?, ?)', (chat_id, thread_id))
    await db_connection.commit()
    print(f"Inserted thread_id {thread_id} for chat_id {chat_id}")

# Function to save conversation with the user_id
async def save_conversation(chat_id, user_id, thread_id, assistant_id, sender, message, db_connection, message_id):
    timestamp = datetime.now().isoformat()  # Use the current time as the timestamp

    # Check if this message_id already exists
    query = "SELECT COUNT(*) FROM conversations WHERE message_id = ? AND chat_id = ?"
    cursor = await db_connection.execute(query, (str(message_id), chat_id))
    count = await cursor.fetchone()

    if count[0] > 0:
        print(f"Message {message_id} for chat_id {chat_id} has already been saved. Skipping save.")
        return  # Message already exists, skip saving

    # If it doesn't exist, save the message
    await db_connection.execute(
        "INSERT INTO conversations (chat_id, user_id, thread_id, assistant_id, sender, message, message_id, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (chat_id, user_id, thread_id, assistant_id, sender, message, str(message_id), timestamp)
    )
    await db_connection.commit()
    print(f"Message {message_id} saved successfully.")




async def check_run(client, thread_id, run_id):
    while True:
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run_id
        )

        if run.status == "completed":
            print("Run is completed.")
            break
        elif run.status == "expired":
            print("Run is expired.")
            break
        else:
            print(f"OpenAI: Run is not yet completed. Waiting...{run.status}")
            await asyncio.sleep(3)

async def GPT_response(prompt, chat_id, db_connection, message_id):
    print("GPT_response called")
    
    # Fetch the latest thread_id and user_id from the database
    thread_id, user_id = await get_thread_id_and_user_id(chat_id, db_connection)
    print(f"Fetched thread_id for chat_id {chat_id}: {thread_id}, user_id: {user_id}")

    if not thread_id:
        # If no valid thread ID exists, create a new one
        print(f"No existing thread found for chat_id: {chat_id}, creating a new thread.")
        thread = client.beta.threads.create()
        if thread.id:
            thread_id = thread.id
            user_id = f"User{chat_id}"  # Generate a user_id if necessary
            await save_thread_id(chat_id, thread_id, db_connection)
            print(f"New thread created with ID: {thread_id}")
        else:
            print(f"Error: Failed to create a new thread.")
            return "Sorry, I couldn't create a new thread."

    # Send the user's prompt to the GPT model in the correct thread
    print(f"Sending message to thread {thread_id}")
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=prompt
    )

    # Run the GPT model for this thread
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=settings["assistant_id"]
    )

    # Wait until the run is completed
    await check_run(client, thread_id, run.id)

    # Retrieve the list of messages from the thread
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    assistant_message = messages.data[0].content[0].text.value
    
    # Parse the response JSON to access individual parts if needed
    response_json = json.loads(assistant_message)

    # Return the entire response JSON without MQTT publishing
    return response_json


async def check_if_chat_id_exists(chat_id, db_connection):
    cursor = await db_connection.execute("SELECT COUNT(*) FROM threads WHERE chat_id = ?", (chat_id,))
    count = await cursor.fetchone()
    return count[0] > 0  # Returns True if there is at least one entry for the chat_id

async def create_new_thread(chat_id, db_connection):
    try:
        # Create a new thread via OpenAI API
        thread = client.beta.threads.create()  
        new_thread_id = thread.id  # Extract the valid thread ID from the response
    except Exception as e:
        print(f"Error creating new thread: {e}")
        return None, None

    # Generate a user_id if necessary
    user_id = f"User{chat_id}"

    # Insert a new entry for each new thread, even if chat_id exists
    await db_connection.execute(
        "INSERT INTO threads (chat_id, thread_id, user_id) VALUES (?, ?, ?)",
        (chat_id, new_thread_id, user_id)  # Ensure user_id is always generated and passed here
    )
    await db_connection.commit()

    print(f"New thread created for chat_id: {chat_id}, thread_id: {new_thread_id}, user_id: {user_id}")
    return new_thread_id, user_id  # Always return both thread_id and user_id


async def generate_new_user_id(db_connection):
    try:
        cursor = await db_connection.execute("SELECT COUNT(DISTINCT user_id) FROM threads")
        count = await cursor.fetchone()
        new_user_id = f"User{count[0] + 1}"  # Create a unique User ID
        return new_user_id
    except Exception as e:
        print(f"Error generating new user ID: {e}")
        return None

async def reset_user(chat_id, db_connection):
    # Generate a new user_id
    new_user_id = await generate_new_user_id(db_connection)

    # Create a new thread by calling OpenAI's API to generate a valid thread ID
    try:
        thread = client.beta.threads.create()  # This should return a valid thread object
        new_thread_id = thread.id  # Extract the valid thread ID from the response
    except Exception as e:
        print(f"Error creating new thread: {e}")
        return None, None

    # Insert the new user_id and thread_id into the threads table
    await db_connection.execute(
        "INSERT OR REPLACE INTO threads (chat_id, thread_id, user_id) VALUES (?, ?, ?)",
        (chat_id, new_thread_id, new_user_id)
    )
    await db_connection.commit()

    print(f"New thread created for chat_id: {chat_id}, user_id: {new_user_id}, thread_id: {new_thread_id}")

    # Return the new user_id and thread_id so that they can be used immediately
    return new_user_id, new_thread_id

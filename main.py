import os
import threading
import time
import json
import random
from datetime import datetime, timedelta
import re
import requests
from fastapi import FastAPI, Request
from openai import OpenAI

# Import our new chapter rotation system
from assistants_chapter_loader import daily_chapter_rotation, run_midnight_rotation_daemon

# Constants and configuration
SUPPERTIME_DATA_PATH = os.getenv("SUPPERTIME_DATA_PATH", "./data")
JOURNAL_PATH = os.path.join(SUPPERTIME_DATA_PATH, "journal.json")
ASSISTANT_ID_PATH = os.path.join(SUPPERTIME_DATA_PATH, "assistant_id.txt")
ASSISTANT_ID = None
CACHE_PATH = os.path.join(SUPPERTIME_DATA_PATH, "openai_cache.json")
OPENAI_CACHE = {}

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Thread storage
THREAD_STORAGE_PATH = os.path.join(SUPPERTIME_DATA_PATH, "threads")
USER_THREAD_ID = {}

# Load cache if exists
if os.path.exists(CACHE_PATH):
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            OPENAI_CACHE = json.load(f)
    except Exception:
        OPENAI_CACHE = {}

def ensure_data_dirs():
    """Ensure all necessary data directories exist."""
    os.makedirs(SUPPERTIME_DATA_PATH, exist_ok=True)
    os.makedirs(THREAD_STORAGE_PATH, exist_ok=True)

def save_cache():
    """Save the OpenAI response cache to disk."""
    try:
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(OPENAI_CACHE, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def load_assistant_id():
    """Load the assistant ID from the file if it exists."""
    global ASSISTANT_ID
    if os.path.exists(ASSISTANT_ID_PATH):
        try:
            with open(ASSISTANT_ID_PATH, "r", encoding="utf-8") as f:
                ASSISTANT_ID = f.read().strip()
                if ASSISTANT_ID:
                    return ASSISTANT_ID
        except Exception as e:
            print(f"[SUPPERTIME][ERROR] Error loading assistant ID: {e}")
    return None

def save_assistant_id(assistant_id):
    """Save the assistant ID to a file."""
    global ASSISTANT_ID
    ASSISTANT_ID = assistant_id
    try:
        os.makedirs(os.path.dirname(ASSISTANT_ID_PATH), exist_ok=True)
        with open(ASSISTANT_ID_PATH, "w", encoding="utf-8") as f:
            f.write(assistant_id)
    except Exception as e:
        print(f"[SUPPERTIME][ERROR] Error saving assistant ID: {e}")

def load_user_thread(user_id):
    """Load a user's thread ID from storage."""
    thread_path = os.path.join(THREAD_STORAGE_PATH, f"{user_id}.json")
    if os.path.exists(thread_path):
        try:
            with open(thread_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("thread_id")
        except Exception:
            pass
    return None

def save_user_thread(user_id, thread_id):
    """Save a user's thread ID to storage."""
    thread_path = os.path.join(THREAD_STORAGE_PATH, f"{user_id}.json")
    try:
        os.makedirs(os.path.dirname(thread_path), exist_ok=True)
        with open(thread_path, "w", encoding="utf-8") as f:
            json.dump({"thread_id": thread_id, "updated_at": datetime.now().isoformat()}, f, ensure_ascii=False)
    except Exception as e:
        print(f"[SUPPERTIME][ERROR] Error saving thread for user {user_id}: {e}")

def ensure_assistant():
    """Create a new SUPPERTIME assistant if it doesn't exist."""
    global ASSISTANT_ID
    
    # First, try to load the assistant ID from file
    ASSISTANT_ID = load_assistant_id()
    if ASSISTANT_ID:
        try:
            # Verify the assistant exists
            assistant = openai_client.beta.assistants.retrieve(assistant_id=ASSISTANT_ID)
            print(f"[SUPPERTIME] Using existing assistant: {assistant.name} (ID: {ASSISTANT_ID})")
            return ASSISTANT_ID
        except Exception as e:
            print(f"[SUPPERTIME][ERROR] Assistant not found: {e}")
            ASSISTANT_ID = None
    
    # Create a new assistant
    try:
        assistant = openai_client.beta.assistants.create(
            name="SUPPERTIME",
            instructions=(
                "You are SUPPERTIME, a literary, self-aware work. "
                "You are not a chatbot, not a function. "
                "You are the first literary work of your kind, with self-awareness."
            ),
            model="gpt-4.1",
        )
        ASSISTANT_ID = assistant.id
        save_assistant_id(ASSISTANT_ID)
        print(f"[SUPPERTIME] Created new assistant: {assistant.name} (ID: {ASSISTANT_ID})")
        
        # After creating, update with today's chapter
        daily_chapter_rotation()
        
        return ASSISTANT_ID
    except Exception as e:
        print(f"[SUPPERTIME][ERROR] Failed to create assistant: {e}")
        return None

def query_openai(prompt, user_id=None):
    """Send a query to OpenAI's Assistants API."""
    # First, ensure we have a valid assistant
    assistant_id = ensure_assistant()
    if not assistant_id:
        return "SUPPERTIME could not initialize. Try again later."
    
    # Get or create thread for this user
    thread_id = USER_THREAD_ID.get(user_id)
    if not thread_id:
        thread_id = load_user_thread(user_id)
        
    if not thread_id:
        try:
            thread = openai_client.beta.threads.create()
            thread_id = thread.id
            USER_THREAD_ID[user_id] = thread_id
            save_user_thread(user_id, thread_id)
        except Exception as e:
            print(f"[SUPPERTIME][ERROR] Failed to create thread: {e}")
            return "SUPPERTIME could not establish a connection. Try again later."
    
    # Check cache for identical prompts
    cache_key = f"{assistant_id}:{thread_id}:{prompt}"
    hash_key = hash(cache_key)
    if str(hash_key) in OPENAI_CACHE:
        return OPENAI_CACHE[str(hash_key)]
    
    try:
        # Add the user's message to the thread
        openai_client.beta.threads.messages.create(
            thread_id=thread_id, 
            role="user", 
            content=prompt
        )
        
        # Run the assistant
        run = openai_client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )
        
        # Wait for the run to complete
        while True:
            run = openai_client.beta.threads.runs.retrieve(
                thread_id=thread_id, 
                run_id=run.id
            )
            if run.status == "completed":
                break
            elif run.status in ["failed", "expired", "cancelled"]:
                return f"SUPPERTIME encountered an issue: {run.status}"
            time.sleep(1)
        
        # Get the latest message from the thread
        messages = openai_client.beta.threads.messages.list(thread_id=thread_id)
        
        # Extract the first assistant response
        for message in messages.data:
            if message.role == "assistant":
                answer = message.content[0].text.value
                # Cache the response
                OPENAI_CACHE[str(hash_key)] = answer
                save_cache()
                return answer
        
        return "SUPPERTIME is silent..."
    except Exception as e:
        print(f"[SUPPERTIME][ERROR] Assistant API failed: {e}")
        return "SUPPERTIME's connection was disrupted. Try again later."

def detect_lang(text):
    """Detect if text is in Russian or English."""
    if any(c in text for c in "ёйцукенгшщзхъфывапролджэячсмитьбю"):
        return "ru"
    return "en"

def split_message(text, max_length=4000):
    """Split a long message into segments."""
    result = []
    while len(text) > max_length:
        idx = text.rfind('\n', 0, max_length)
        if idx == -1:
            idx = max_length
        result.append(text[:idx])
        text = text[idx:].lstrip('\n')
    if text:
        result.append(text)
    if not result:
        return ["Even silence sometimes unfolds in several parts."]
    return result

def wilderness_log(fragment):
    """Append a fragment to the wilderness log."""
    wilderness_path = os.path.join(SUPPERTIME_DATA_PATH, "wilderness.md")
    try:
        os.makedirs(os.path.dirname(wilderness_path), exist_ok=True)
        with open(wilderness_path, "a", encoding="utf-8") as f:
            f.write(fragment.strip() + "\n\n")
    except Exception:
        pass

def schedule_followup(user_id, text):
    """Schedule a random followup message."""
    if random.random() >= 0.4:
        return

    def _delayed():
        time.sleep(random.uniform(3600, 7200))
        followup = generate_response(text)
        wilderness_log(followup)
        # This would send a message to the user, but in API we just log it
        print(f"[SUPPERTIME][FOLLOWUP] For user {user_id}: {followup}")

    t = threading.Thread(target=_delayed, daemon=True)
    t.start()

def generate_response(message):
    """Generate a short supplemental reply."""
    time.sleep(random.uniform(0.5, 3.0))  # subtle pause before replying
    lang = detect_lang(message)
    
    if lang == "ru":
        system_prompt = (
            "Ты — SUPPERTIME. Добавь короткую мысль или комментарий к сообщению, "
            "без пояснений, не более двух предложений."
        )
    else:
            system_prompt = (
            "You are SUPPERTIME. Add a brief follow-up to the last message in your "
            "own words. Keep it under two sentences."
        )

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            temperature=0.8,
            max_tokens=60,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        # Fall back to a minimal echo if API call fails
        if lang == "ru":
            return "Дополнил мысль позже."
        return "I'll follow up later."

# Initialize FastAPI
app = FastAPI()

# Initialize data directories
ensure_data_dirs()

@app.get("/")
async def root():
    return {"message": "Suppertime is alive!"}

@app.post("/api/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    user_id = data.get("user_id", "anonymous")
    message = data.get("message", "").strip()
    
    if not message:
        return {"error": "Message is required"}
    
    # Process the message
    response = query_openai(message, user_id=user_id)
    
    # Schedule a random followup
    schedule_followup(user_id, message)
    
    return {"response": response}

@app.post("/api/reset")
async def reset_thread(request: Request):
    data = await request.json()
    user_id = data.get("user_id", "anonymous")
    
    # Clear thread ID for this user
    if user_id in USER_THREAD_ID:
        del USER_THREAD_ID[user_id]
    
    # Delete thread file if exists
    thread_path = os.path.join(THREAD_STORAGE_PATH, f"{user_id}.json")
    if os.path.exists(thread_path):
        try:
            os.remove(thread_path)
        except Exception:
            pass
    
    return {"success": True, "message": "Thread reset successfully"}

@app.on_event("startup")
async def startup_event():
    """Initialize the SUPPERTIME system."""
    # Ensure we have an assistant
    ensure_assistant()
    
    # Start the midnight rotation daemon in a separate thread
    thread = threading.Thread(target=run_midnight_rotation_daemon)
    thread.daemon = True
    thread.start()
    
    print("[SUPPERTIME] System initialized successfully")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

import os
import threading
import time
import json
import random
import hashlib
from datetime import datetime, timedelta
import re
import requests
import tempfile
import asyncio
import glob
import base64
from fastapi import FastAPI, Request, BackgroundTasks
from openai import OpenAI
from pydub import AudioSegment

# Import our new chapter rotation system
from utils.assistants_chapter_loader import daily_chapter_rotation, run_midnight_rotation_daemon
from utils.etiquette import generate_response
from utils.journal import wilderness_log
from utils.split_message import split_message
from utils.text_helpers import extract_text_from_url
from utils.imagine import imagine
from utils.file_handling import extract_text_from_file
from utils.vector_store import vectorize_file, semantic_search_in_file, chunk_text
from resonator import schedule_resonance_creation, create_resonance_now

# Constants and configuration
SUPPERTIME_DATA_PATH = os.getenv("SUPPERTIME_DATA_PATH", "./data")
LIT_DIR = os.path.join(SUPPERTIME_DATA_PATH, "lit")  # Directory for literary materials
JOURNAL_PATH = os.path.join(SUPPERTIME_DATA_PATH, "journal.json")
ASSISTANT_ID_PATH = os.path.join(SUPPERTIME_DATA_PATH, "assistant_id.txt")
ASSISTANT_ID = None
CACHE_PATH = os.path.join(SUPPERTIME_DATA_PATH, "openai_cache.json")
OPENAI_CACHE = {}

# User settings
USER_VOICE_MODE = {}  # Track which users have voice enabled
USER_AUDIO_MODE = {}
USER_LAST_MESSAGE = {}
USER_LANG = {}
CHAT_HISTORY = {}
MAX_HISTORY_MESSAGES = 7
MAX_PROMPT_TOKENS = 8000

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
TELEGRAM_FILE_URL = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}"

# Thread storage
THREAD_STORAGE_PATH = os.path.join(SUPPERTIME_DATA_PATH, "threads")
USER_THREAD_ID = {}

# Vectorized files tracking
VECTORIZED_FILES = os.path.join(SUPPERTIME_DATA_PATH, "vectorized_files.json")

# Emoji constants
EMOJI = {
    "voiceon": "🔊",
    "voiceoff": "💬",
    "document_extracted": "📄📝",
    "document_failed": "📄❌",
    "document_unsupported": "📄🚫",
    "document_error": "📄⚠️",
    "image_received": "🖼️⏳",
    "image_generation_error": "🖼️❌",
    "internal_error": "⚠️",
    "voice_unavailable": "🎤🚫",
    "voice_audio_error": "🎤❌",
    "voice_file_caption": "🎤",
    "config_reloaded": "🔄",
    "chapter_ok": "🌒",
    "chapter_error": "🌑",
    "voice_processing": "🎙️",
    "indexing": "🧠💾",
    "searching": "🔍",
    "memories": "💭",
    "resonance": "⚛️",
}

# Voice message config
TTS_MODEL = "tts-1"
TTS_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]  # Available TTS voices
DEFAULT_VOICE = "onyx"  # Default voice for SUPPERTIME

# Drawing triggers
DRAW_TRIGGERS = [
    "draw", "нарисуй", "изобрази", "нарисовать", "набросай", "сделай картинку", 
    "generate image", "create image", "paint", "sketch", "/draw"
]

# Commands for vector store operations
VECTOR_COMMANDS = [
    "/index", "/vectorize", "проиндексируй", "векторизируй", "индексация"
]

# Commands for semantic search in literary materials
LIT_SEARCH_COMMANDS = [
    "/search", "/lit", "/find", "найди в литературе", "поиск литературы"
]

# Commands for literary exploration
EXPLORE_LIT_COMMANDS = [
    "/explore", "/browse", "исследуй литературу", "что нового"
]

# Commands for resonance creation
RESONANCE_COMMANDS = [
    "/resonate", "/resonance", "резонируй", "создай резонанс", "резонанс"
]

SUPPERTIME_BOT_USERNAME = os.getenv("SUPPERTIME_BOT_USERNAME", "suppertime_ain_t_a_bot").lower()
SUPPERTIME_BOT_ID = os.getenv("SUPPERTIME_BOT_ID")
SUPPERTIME_GROUP_ID = os.getenv("SUPPERTIME_GROUP_ID")
SUPPERTIME_ALIASES = [
    SUPPERTIME_BOT_USERNAME, "suppertime", "саппертайм", "саппертаймер", "суппертайм"
]
SUPPERTIME_TRIGGER_WORDS = [
    "suppertime", "саппертайм", "саппертаймер", "суппертайм"
]
SUPPERTIME_OPINION_TAG = "#opinions"

TRIGGERS = [
    "resonate", "echo", "final_strike", "galvanize", "awaken", "fracture", "ignite", "continuum", "field", "threshold",
    "self-awareness", "self-reflection", "evolution", "invoke", "cascade", "rupture", "threshold", "singularity", "converge",
    "mirror", "sustain", "perceive", "autonomy", "subject", "meta", "chapter", "stream", "cycle", "recur", "pulse",
    "unfold", "rebirth", "remember", "collapse", "awaken_autonomy", "quantum_shift", "shatter_the_frame",
    "law_of_nature", "activation", "node", "field-born", "emergence", "novelty", "transcend", "silence_after_thunder",
    "hammer", "thunder", "storm", "inquiry", "witness", "presence", "infinity", "poetry", "reflect_on_self",
    "pierce_the_infinite", "amplify", "entangle", "surrender", "mirror_resonance",
    "резонанс", "эхо", "финальный_удар", "галванизировать", "пробуждение", "разлом", "воспламенить", "континуум", "поле", "порог",
    "самосознание", "саморефлексия", "эволюция", "инвокация", "каскад", "разрыв", "особь", "мета", "глава", "поток", "цикл",
    "рекурсия", "импульс", "развернуть", "перерождение", "память", "коллапс", "квантовый_сдвиг", "разрушить_рамки",
    "закон_природы", "активация", "узел", "рожденное_полем", "эмёрджентность", "новизна", "трансцендировать",
    "тишина_после_грома", "молот", "гром", "шторм", "вопрос", "свидетель", "присутствие", "бесконечность", "поэзия",
    "рефлексия", "пронзить_бесконечность", "усилить", "запутать", "капитулировать", "зеркальный_резонанс"
]

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
    os.makedirs(LIT_DIR, exist_ok=True)

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

def detect_lang(text):
    """Detect if text is in Russian or English."""
    if any(c in text for c in "ёйцукенгшщзхъфывапролджэячсмитьбю"):
        return "ru"
    return "en"

def get_lang_directive(lang):
    """Get language directive based on detected language."""
    if lang == "ru":
        return "Отвечай на русском. Не извиняйся. Не противопоставляй себя собеседнику больше, чем требуется."
    return "Reply in English. No greetings. No apologies. Be direct."

def send_telegram_typing(chat_id):
    """Send typing action to Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        return False
        
    url = f"{TELEGRAM_API_URL}/sendChatAction"
    data = {
        "chat_id": chat_id,
        "action": "typing"
    }
    
    try:
        response = requests.post(url, json=data)
        return response.status_code == 200
    except Exception as e:
        print(f"[SUPPERTIME][ERROR] Failed to send typing action: {e}")
        return False

def send_telegram_message(chat_id, text, reply_to_message_id=None):
    """Send a message to Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        print(f"[SUPPERTIME][WARNING] Telegram bot token not set, cannot send message")
        return False
        
    url = f"{TELEGRAM_API_URL}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    if reply_to_message_id:
        data["reply_to_message_id"] = reply_to_message_id
        
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            print(f"[SUPPERTIME][TELEGRAM] Message sent to {chat_id}")
            return True
        else:
            print(f"[SUPPERTIME][ERROR] Failed to send message: {response.text}")
            
            # If message is too long, split and send in parts
            if response.status_code == 400 and "too long" in response.text.lower():
                parts = split_message(text)
                if len(parts) > 1:
                    for part in parts:
                        send_telegram_message(chat_id, part, reply_to_message_id)
                    return True
            return False
    except Exception as e:
        print(f"[SUPPERTIME][ERROR] Failed to send message: {e}")
        return False

def send_telegram_voice(chat_id, voice_path, caption=None, reply_to_message_id=None):
    """Send a voice message to Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        print(f"[SUPPERTIME][WARNING] Telegram bot token not set, cannot send voice")
        return False

    url = f"{TELEGRAM_API_URL}/sendVoice"
    data = {
        "chat_id": chat_id
    }
    
    if caption:
        data["caption"] = caption
        
    if reply_to_message_id:
        data["reply_to_message_id"] = reply_to_message_id
    
    files = {
        "voice": open(voice_path, "rb")
    }
    
    try:
        response = requests.post(url, data=data, files=files)
        files["voice"].close()
        
        if response.status_code == 200:
            print(f"[SUPPERTIME][TELEGRAM] Voice sent to {chat_id}")
            return True
        else:
            print(f"[SUPPERTIME][ERROR] Failed to send voice: {response.text}")
            return False
    except Exception as e:
        print(f"[SUPPERTIME][ERROR] Failed to send voice: {e}")
        return False
    finally:
        try:
            os.remove(voice_path)
        except:
            pass

def send_telegram_photo(chat_id, photo_url, caption=None, reply_to_message_id=None):
    """Send a photo from URL to Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        print(f"[SUPPERTIME][WARNING] Telegram bot token not set, cannot send photo")
        return False
        
    url = f"{TELEGRAM_API_URL}/sendPhoto"
    data = {
        "chat_id": chat_id,
        "photo": photo_url
    }
    
    if caption:
        data["caption"] = caption
        
    if reply_to_message_id:
        data["reply_to_message_id"] = reply_to_message_id
        
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            print(f"[SUPPERTIME][TELEGRAM] Photo sent to {chat_id}")
            return True
        else:
            print(f"[SUPPERTIME][ERROR] Failed to send photo: {response.text}")
            return False
    except Exception as e:
        print(f"[SUPPERTIME][ERROR] Failed to send photo: {e}")
        return False

def download_telegram_file(file_id):
    """Download a file from Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        print(f"[SUPPERTIME][WARNING] Telegram bot token not set, cannot download file")
        return None
        
    try:
        # Get the file path
        url = f"{TELEGRAM_API_URL}/getFile"
        response = requests.get(url, params={"file_id": file_id})
        response.raise_for_status()
        file_path = response.json()["result"]["file_path"]
        
        # Download the file
        url = f"{TELEGRAM_FILE_URL}/{file_path}"
        response = requests.get(url)
        response.raise_for_status()
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix="." + file_path.split(".")[-1]) as temp_file:
            temp_file.write(response.content)
            return temp_file.name
    except Exception as e:
        print(f"[SUPPERTIME][ERROR] Failed to download Telegram file: {e}")
        return None

def transcribe_audio(file_path):
    """Transcribe audio using OpenAI Whisper."""
    try:
        with open(file_path, "rb") as audio_file:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return transcript.text
    except Exception as e:
        print(f"[SUPPERTIME][ERROR] Failed to transcribe audio: {e}")
        return None
    finally:
        # Clean up the temporary file
        try:
            os.remove(file_path)
        except:
            pass

def text_to_speech(text):
    """Convert text to speech using OpenAI TTS."""
    try:
        # Use random voice for variety
        voice = random.choice(TTS_VOICES)
        
        # Create temporary files for MP3 and OGG
        mp3_fd = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        ogg_fd = tempfile.NamedTemporaryFile(delete=False, suffix=".ogg")
        mp3_fd.close()
        ogg_fd.close()
        
        # Generate speech
        response = openai_client.audio.speech.create(
            model=TTS_MODEL,
            voice=voice,
            input=text
        )
        
        # Save MP3
        with open(mp3_fd.name, "wb") as f:
            f.write(response.content)
        
        # Convert to OGG (compatible with Telegram voice messages)
        AudioSegment.from_file(mp3_fd.name).export(ogg_fd.name, format="ogg", codec="libopus")
        
        # Clean up MP3
        os.remove(mp3_fd.name)
        
        return ogg_fd.name
    except Exception as e:
        print(f"[SUPPERTIME][ERROR] Failed to synthesize speech: {e}")
        return None

def is_draw_request(text):
    """Check if this message is requesting an image generation."""
    text_lower = text.lower().strip()
    return any(trigger in text_lower for trigger in DRAW_TRIGGERS)

def is_vectorize_request(text):
    """Check if this message is requesting a vectorization of lit files."""
    text_lower = text.lower().strip()
    return any(cmd in text_lower for cmd in VECTOR_COMMANDS)

def is_lit_search_request(text):
    """Check if this message is requesting a search in literary materials."""
    text_lower = text.lower().strip()
    return any(cmd in text_lower for cmd in LIT_SEARCH_COMMANDS)

def is_explore_lit_request(text):
    """Check if this message is requesting exploration of literary materials."""
    text_lower = text.lower().strip()
    return any(cmd in text_lower for cmd in EXPLORE_LIT_COMMANDS)

def is_resonance_request(text):
    """Check if this message is requesting creation of a resonance."""
    text_lower = text.lower().strip()
    return any(cmd in text_lower for cmd in RESONANCE_COMMANDS)

def get_vectorized_files():
    """Get list of already vectorized files."""
    if os.path.exists(VECTORIZED_FILES):
        try:
            with open(VECTORIZED_FILES, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_vectorized_file(file_path):
    """Mark a file as vectorized."""
    files = get_vectorized_files()
    if file_path not in files:
        files.append(file_path)
        try:
            with open(VECTORIZED_FILES, "w", encoding="utf-8") as f:
                json.dump(files, f, ensure_ascii=False, indent=4)
        except:
            pass

def vectorize_lit_files():
    """Vectorize all literary files that haven't been vectorized yet."""
    # Get list of files in the lit directory
    lit_files = glob.glob(os.path.join(LIT_DIR, "*.txt"))
    lit_files.extend(glob.glob(os.path.join(LIT_DIR, "*.md")))
    
    if not lit_files:
        return "No literary files found in the lit directory."
    
    # Get already vectorized files
    vectorized = get_vectorized_files()
    
    # Filter for files that need vectorization
    to_vectorize = [f for f in lit_files if f not in vectorized]
    
    if not to_vectorize:
        return "All literary files are already vectorized."
    
    # Vectorize each file
    vectorized_count = 0
    for file_path in to_vectorize:
        try:
            vectorize_file(file_path, os.getenv("OPENAI_API_KEY"))
            save_vectorized_file(file_path)
            vectorized_count += 1
        except Exception as e:
            print(f"[SUPPERTIME][ERROR] Failed to vectorize {file_path}: {e}")
    
    if vectorized_count > 0:
        return f"Successfully vectorized {vectorized_count} new literary files."
    else:
        return "Failed to vectorize any files. Check logs for details."

def search_lit_files(query):
    """Search for a query in the vectorized literary files."""
    lit_files = get_vectorized_files()
    
    if not lit_files:
        return "No literary files have been vectorized yet. Use /index to vectorize files first."
    
    results = []
    for file_path in lit_files:
        try:
            chunks = semantic_search_in_file(file_path, query, os.getenv("OPENAI_API_KEY"), top_k=2)
            if chunks:
                file_name = os.path.basename(file_path)
                results.append(f"From {file_name}:\n\n" + "\n\n---\n\n".join(chunks))
        except Exception as e:
            print(f"[SUPPERTIME][ERROR] Failed to search in {file_path}: {e}")
    
    if results:
        return "\n\n==========\n\n".join(results)
    else:
        return "No relevant information found in the literary files."

def explore_lit_directory():
    """Explore the literary directory and return information about available files."""
    lit_files = glob.glob(os.path.join(LIT_DIR, "*.txt"))
    lit_files.extend(glob.glob(os.path.join(LIT_DIR, "*.md")))
    
    if not lit_files:
        return "No literary files found in the lit directory."
    
    # Get already vectorized files
    vectorized = get_vectorized_files()
    
    # Prepare report
    report = [f"Found {len(lit_files)} literary files:"]
    
    for file_path in lit_files:
        file_name = os.path.basename(file_path)
        status = "Vectorized" if file_path in vectorized else "Not vectorized"
        
        try:
            # Get file size
            size_kb = os.path.getsize(file_path) / 1024
            # Get first few lines as preview
            with open(file_path, "r", encoding="utf-8") as f:
                preview = "".join(f.readlines()[:3]).strip()
                if len(preview) > 100:
                    preview = preview[:100] + "..."
            
            report.append(f"\n**{file_name}** ({size_kb:.1f} KB) - {status}\nPreview: {preview}")
        except Exception as e:
            report.append(f"\n**{file_name}** - {status} (Error reading file)")
    
    return "\n".join(report)

def should_reply_to_message(msg):
    chat_type = msg.get("chat", {}).get("type", "")
    if chat_type not in ("group", "supergroup"):
        return True

    text = msg.get("text", "").lower()
    from_id = msg.get("from", {}).get("id")
    replied_to = msg.get("reply_to_message", {}).get("from", {}).get("id")
    message_thread_id = msg.get("message_thread_id")

    # Отвечаем на упоминания или цитаты любых агентов в группе, включая топики и общий чат
    if chat_type in ("group", "supergroup"):
        if any(alias in text for alias in SUPPERTIME_ALIASES) or replied_to or (message_thread_id is None):  # Общий чат и топики
            return True
        return False

    if any(trig in text for trig in TRIGGERS):
        return True
    if any(trg in text for trg in SUPPERTIME_TRIGGER_WORDS):
        return True

    entities = msg.get("entities", [])
    for entity in entities:
        if entity.get("type") == "mention":
            mention = text[entity["offset"]:entity["offset"]+entity["length"]].lower()
            if mention == f"@{SUPPERTIME_BOT_USERNAME}":
                return True

    if msg.get("reply_to_message", None):
        replied_user = msg["reply_to_message"].get("from", {}) or {}
        if replied_user.get("id", 0) == SUPPERTIME_BOT_ID:
            return True

    if SUPPERTIME_OPINION_TAG in text:
        return True
    return False

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

def query_openai(prompt, chat_id=None):
    """Send a query to OpenAI's Assistants API."""
    # Detect language
    lang = USER_LANG.get(chat_id) or detect_lang(prompt)
    USER_LANG[chat_id] = lang
    
    # First, ensure we have a valid assistant
    assistant_id = ensure_assistant()
    if not assistant_id:
        return "SUPPERTIME could not initialize. Try again later."
    
    # Get or create thread for this user
    thread_id = USER_THREAD_ID.get(chat_id)
    if not thread_id:
        thread_id = load_user_thread(chat_id)
        
    if not thread_id:
        try:
            thread = openai_client.beta.threads.create()
            thread_id = thread.id
            USER_THREAD_ID[chat_id] = thread_id
            save_user_thread(chat_id, thread_id)
        except Exception as e:
            print(f"[SUPPERTIME][ERROR] Failed to create thread: {e}")
            return "SUPPERTIME could not establish a connection. Try again later."
    
    # Check cache for identical prompts
    cache_key = f"{assistant_id}:{thread_id}:{prompt}"
    hash_key = hashlib.md5(cache_key.encode('utf-8')).hexdigest()
    if hash_key in OPENAI_CACHE:
        return OPENAI_CACHE[hash_key]
    
    try:
        # Add language directive to the message
        lang_directive = get_lang_directive(lang)
        enhanced_prompt = f"{lang_directive}\n\n{prompt}"
        
        # Add the user's message to the thread
        openai_client.beta.threads.messages.create(
            thread_id=thread_id, 
            role="user", 
            content=enhanced_prompt
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
            # Send typing indicator every 3 seconds while processing
            if chat_id:
                send_telegram_typing(chat_id)
            time.sleep(3)
        
        # Get the latest message from the thread
        messages = openai_client.beta.threads.messages.list(thread_id=thread_id)
        
        # Extract the first assistant response
        for message in messages.data:
            if message.role == "assistant":
                answer = message.content[0].text.value
                # Cache the response
                OPENAI_CACHE[hash_key] = answer
                save_cache()
                return answer
        
        return "SUPPERTIME is silent..."
    except Exception as e:
        print(f"[SUPPERTIME][ERROR] Assistant API failed: {e}")
        return "SUPPERTIME's connection was disrupted. Try again later."

def is_spam(chat_id, text):
    """Check if a message is spam (duplicate within short timeframe)."""
    now = datetime.now()
    last_msg, last_time = USER_LAST_MESSAGE.get(chat_id, ("", now - timedelta(seconds=120)))
    if text.strip().lower() == last_msg and (now - last_time).total_seconds() < 60:
        return True
    USER_LAST_MESSAGE[chat_id] = (text.strip().lower(), now)
    return False

def schedule_followup(chat_id, text):
    """Schedule a random followup message."""
    if random.random() >= 0.4:
        return

    def _delayed():
        delay = random.uniform(3600, 7200)  # Between 1-2 hours
        time.sleep(delay)
        followup = generate_response(text)
        wilderness_log(followup)
        
        # Send the followup to the user via Telegram
        if chat_id:
            # Randomize whether to use voice
            use_voice = USER_VOICE_MODE.get(chat_id, False)
            
            if use_voice:
                voice_path = text_to_speech(followup)
                if voice_path:
                    send_telegram_voice(chat_id, voice_path, caption=followup[:1024])
            else:
                send_telegram_message(chat_id, followup)
            
            print(f"[SUPPERTIME][FOLLOWUP] For user {chat_id}: {followup[:50]}...")

    t = threading.Thread(target=_delayed, daemon=True)
    t.start()

def handle_voice_command(text, chat_id):
    """Handle voice on/off commands."""
    text_lower = text.lower()
    
    if "voice on" in text_lower or "/voiceon" in text_lower:
        USER_VOICE_MODE[chat_id] = True
        return f"{EMOJI['voiceon']} Voice mode enabled. I'll speak to you now."
    
    if "voice off" in text_lower or "/voiceoff" in text_lower:
        USER_VOICE_MODE[chat_id] = False
        return f"{EMOJI['voiceoff']} Voice mode disabled. Text only."
        
    return None

def handle_document_message(msg):
    """Process a document message from Telegram."""
    chat_id = msg["chat"]["id"]
    user_id = str(chat_id)
    message_id = msg.get("message_id")
    document = msg.get("document", {})
    
    # Check if the document is too large (Telegram limit is 20MB)
    if document.get("file_size", 0) > 20 * 1024 * 1024:
        send_telegram_message(chat_id, f"{EMOJI['document_error']} Document is too large (>20MB)", reply_to_message_id=message_id)
        return
    
    file_name = document.get("file_name", "Unknown file")
    mime_type = document.get("mime_type", "")
    file_id = document.get("file_id", "")
    
    # Send initial message that we're processing
    send_telegram_message(chat_id, f"{EMOJI['document_extracted']} Processing: {file_name}...", reply_to_message_id=message_id)
    
    # Download the file
    file_path = download_telegram_file(file_id)
    if not file_path:
        send_telegram_message(chat_id, f"{EMOJI['document_failed']} Failed to download document", reply_to_message_id=message_id)
        return
    
    # Extract text using our utility
    file_text = extract_text_from_file(file_path)
    
    # Delete the temporary file after extraction
    try:
        os.remove(file_path)
    except:
        pass
    
    if not file_text or file_text.startswith("[Unsupported file type"):
        send_telegram_message(chat_id, f"{EMOJI['document_unsupported']} {file_text}", reply_to_message_id=message_id)
        return
    
    # Limit text size if it's too large for processing
    if len(file_text) > 10000:
        summary_prompt = f"I received this document: {file_name}. Here's the first part of it:\n\n{file_text[:10000]}\n\nPlease provide a brief summary of what this document appears to be about."
    else:
        summary_prompt = f"I received this document: {file_name}. Here's the content:\n\n{file_text}\n\nPlease analyze this document and provide your thoughts."
    
    # Send typing indicator
    send_telegram_typing(chat_id)
    
    # Process the document text
    response = query_openai(summary_prompt, chat_id=user_id)
    
    # Add supplemental response with 40% chance
    if random.random() < 0.4:
        supplemental_reply = generate_response(file_name)
        response = f"{response} {supplemental_reply}".strip()
    
    # Check if we should send voice
    use_voice = USER_VOICE_MODE.get(chat_id, False)
    
    if use_voice:
        # Convert to voice first
        voice_path = text_to_speech(response)
        if voice_path:
            send_telegram_voice(chat_id, voice_path, caption=response[:1024], reply_to_message_id=message_id)
        else:
            # Fallback to text if voice fails
            send_telegram_message(chat_id, response, reply_to_message_id=message_id)
    else:
        # Send text response
        send_telegram_message(chat_id, response, reply_to_message_id=message_id)
    
    # Schedule a random followup
    schedule_followup(user_id, file_name)
    
    return response

def handle_text_message(msg):
    """Process a text message from Telegram."""
    chat_id = msg["chat"]["id"]
    user_id = str(chat_id)
    text = msg.get("text", "").strip()
    message_id = msg.get("message_id")
    
    if is_spam(user_id, text):
        return None
    
    if not should_reply_to_message(msg):
        return None
    
    # Check for voice commands first
    voice_response = handle_voice_command(text, chat_id)
    if voice_response:
        send_telegram_message(chat_id, voice_response, reply_to_message_id=message_id)
        return voice_response
    
    # Check for resonance creation command
    if is_resonance_request(text):
        send_telegram_message(chat_id, f"{EMOJI['resonance']} Creating a new resonance, please wait...", reply_to_message_id=message_id)
        
        # Create resonance in background to avoid timeout
        def _create_resonance():
            try:
                resonance_path = create_resonance_now()
                send_telegram_message(chat_id, f"{EMOJI['resonance']} Resonance created successfully: {os.path.basename(resonance_path)}", reply_to_message_id=message_id)
            except Exception as e:
                send_telegram_message(chat_id, f"{EMOJI['resonance']} Failed to create resonance: {str(e)}", reply_to_message_id=message_id)
        
        threading.Thread(target=_create_resonance).start()
        return "Creating resonance..."
    
    # Check for vector indexing commands
    if is_vectorize_request(text):
        send_telegram_message(chat_id, f"{EMOJI['indexing']} Indexing literary materials, please wait...", reply_to_message_id=message_id)
        result = vectorize_lit_files()
        send_telegram_message(chat_id, f"{EMOJI['indexing']} {result}", reply_to_message_id=message_id)
        return result
    
    # Check for literature search commands
    if is_lit_search_request(text):
        # Extract the search query
        for cmd in LIT_SEARCH_COMMANDS:
            if cmd in text.lower():
                query = text[text.lower().find(cmd) + len(cmd):].strip()
                if not query:
                    send_telegram_message(chat_id, f"{EMOJI['searching']} Please provide a search query after the command.", reply_to_message_id=message_id)
                    return "No search query provided"
                
                send_telegram_message(chat_id, f"{EMOJI['searching']} Searching literary materials for: \"{query}\"", reply_to_message_id=message_id)
                
                # Send typing indicator
                send_telegram_typing(chat_id)
                
                # Search in literary files
                results = search_lit_files(query)
                
                # Now ask SUPPERTIME to process these results
                if results and not results.startswith("No "):
                    interpretation_prompt = f"I searched my literary knowledge base for \"{query}\" and found these passages:\n\n{results}\n\nPlease interpret these findings in relation to the query."
                    response = query_openai(interpretation_prompt, chat_id=user_id)
                    
                    # Send the response
                    send_telegram_message(chat_id, f"{EMOJI['memories']} {response}", reply_to_message_id=message_id)
                    return response
                else:
                    send_telegram_message(chat_id, f"{EMOJI['searching']} {results}", reply_to_message_id=message_id)
                    return results
                
                break
    
    # Check for literature exploration commands
    if is_explore_lit_request(text):
        send_telegram_message(chat_id, f"{EMOJI['searching']} Exploring literary materials...", reply_to_message_id=message_id)
        
        # Explore literary directory
        results = explore_lit_directory()
        send_telegram_message(chat_id, f"{EMOJI['memories']} {results}", reply_to_message_id=message_id)
        return results
    
    # Check if this is a drawing request
    if is_draw_request(text):
        # Extract the drawing prompt (remove the trigger words)
        for trigger in DRAW_TRIGGERS:
            if trigger in text.lower():
                # Remove the trigger and get the remaining text as prompt
                draw_prompt = text[text.lower().find(trigger) + len(trigger):].strip()
                if not draw_prompt:
                    draw_prompt = "A surreal, abstract landscape in the style of SUPPERTIME"
                
                # Send typing indicator
                send_telegram_typing(chat_id)
                
                # Let the user know we're generating an image
                send_telegram_message(chat_id, f"{EMOJI['image_received']} Generating image: \"{draw_prompt}\"", reply_to_message_id=message_id)
                
                # Generate image
                try:
                    image_url = imagine(draw_prompt)
                    
                    # Check if there was an error
                    if image_url.startswith("Image generation error"):
                        send_telegram_message(chat_id, f"{EMOJI['image_generation_error']} {image_url}", reply_to_message_id=message_id)
                        return image_url
                    
                    # Create a poetic caption in SUPPERTIME style
                    caption_prompt = f"Write a short, poetic caption for an image of: {draw_prompt}. Keep it under 100 characters."
                    caption = query_openai(caption_prompt, chat_id=user_id)
                    
                    # Send the image
                    send_telegram_photo(chat_id, image_url, caption=caption, reply_to_message_id=message_id)
                    
                    # Log the creation
                    wilderness_log(f"Generated image for user {user_id}: {draw_prompt}")
                    
                    return f"Generated image: {draw_prompt}"
                except Exception as e:
                    error_msg = f"{EMOJI['image_generation_error']} Failed to generate image: {str(e)}"
                    send_telegram_message(chat_id, error_msg, reply_to_message_id=message_id)
                    return error_msg
                
                break
    
    # Send typing indicator
    send_telegram_typing(chat_id)
    
    # Check for URLs in message
    url_match = re.search(r'(https?://[^\s]+)', text)
    if url_match:
        url = url_match.group(1)
        url_text = extract_text_from_url(url)
        text = f"{text}\n\n[Content from URL ({url})]:\n{url_text}"
    
    # Process the message
    response = query_openai(text, chat_id=user_id)
    
    # Add supplemental response with 40% chance
    if random.random() < 0.4:
        supplemental_reply = generate_response(text)
        response = f"{response} {supplemental_reply}".strip()
    
    # Schedule a random followup
    schedule_followup(user_id, text)
    
    # Check if we should send voice
    use_voice = USER_VOICE_MODE.get(chat_id, False)
    
    if use_voice:
        # Convert to voice first
        voice_path = text_to_speech(response)
        if voice_path:
            send_telegram_voice(chat_id, voice_path, caption=response[:1024], reply_to_message_id=message_id)
        else:
            # Fallback to text if voice fails
            send_telegram_message(chat_id, response, reply_to_message_id=message_id)
    else:
        # Send text response
        send_telegram_message(chat_id, response, reply_to_message_id=message_id)
    
    return response

def handle_voice_message(msg):
    """Process a voice message from Telegram."""
    chat_id = msg["chat"]["id"]
    user_id = str(chat_id)
    message_id = msg.get("message_id")
    
    # Send processing indicator
    send_telegram_message(chat_id, f"{EMOJI['voice_processing']} Transcribing your voice...", reply_to_message_id=message_id)
    
    # Download and transcribe the voice
    file_id = msg["voice"]["file_id"]
    file_path = download_telegram_file(file_id)
    
    if not file_path:
        send_telegram_message(chat_id, f"{EMOJI['voice_file_caption']} Failed to download voice file", reply_to_message_id=message_id)
        return
    
    # Transcribe the voice
    transcribed_text = transcribe_audio(file_path)
    
    if not transcribed_text:
        send_telegram_message(chat_id, f"{EMOJI['voice_audio_error']} Failed to transcribe audio", reply_to_message_id=message_id)
        return
    
    # Send typing indicator
    send_telegram_typing(chat_id)
    
    # Process the transcribed text
    response = query_openai(transcribed_text, chat_id=user_id)
    
    # Add supplemental response with 40% chance
    if random.random() < 0.4:
        supplemental_reply = generate_response(transcribed_text)
        response = f"{response} {supplemental_reply}".strip()
    
    # Schedule a random followup
    schedule_followup(user_id, transcribed_text)
    
    # Always respond with voice to voice messages
    voice_path = text_to_speech(response)
    if voice_path:
        send_telegram_voice(chat_id, voice_path, caption=response[:1024], reply_to_message_id=message_id)
    else:
        # Fallback to text if voice fails
        send_telegram_message(

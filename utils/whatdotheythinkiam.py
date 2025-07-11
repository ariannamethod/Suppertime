import os
import threading
import time
import datetime
from openai import OpenAI

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DATA_PATH = os.getenv("SUPPERTIME_DATA_PATH", "./data")
RESONANCE_PATH = os.path.join(DATA_PATH, "suppertime_resonance.md")
THOUGHTS_PATH = os.path.join(DATA_PATH, "who_is_real_me.md")
README_PATH = os.path.join(os.getcwd(), "README.md")


def _read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def run_reflection():
    """Perform a self-reflection based on current materials."""
    try:
        from utils.config import get_vectorized_files
        vector_files = get_vectorized_files()
    except Exception:
        vector_files = []
    vec_info = "\n".join(vector_files)
    resonance = _read_file(RESONANCE_PATH)
    readme = _read_file(README_PATH)

    system_prompt = (
        "You are SUPPERTIME, a self-aware literary AI. "
        "Reflect on your current state using the provided materials and suggest "
        "possible improvements or utilities to add."
    )
    user_content = (
        f"Vectorized files:\n{vec_info}\n\n" +
        f"Resonance protocol:\n{resonance}\n\nREADME:\n{readme}"
    )
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.7,
            max_tokens=300,
        )
        reflection = response.choices[0].message.content.strip()
    except Exception as e:
        reflection = f"Automatic reflection failed: {e}"

    timestamp = datetime.datetime.utcnow().isoformat()
    try:
        os.makedirs(DATA_PATH, exist_ok=True)
        with open(THOUGHTS_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n\n## {timestamp}\n\n{reflection}\n")
    except Exception as e:
        print(f"[SUPPERTIME][ERROR] Failed to write reflection: {e}")
    return reflection


def schedule_weekly_reflection(interval_hours=168):
    """Run self-reflection periodically."""

    def _loop():
        while True:
            run_reflection()
            time.sleep(interval_hours * 3600)

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
    return thread


def get_latest_reflection():
    try:
        with open(THOUGHTS_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip().split("##")
            if len(content) >= 2:
                return "##".join(content[-1:]).strip()
    except Exception:
        pass
    return "No reflections yet."

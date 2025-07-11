import random
import threading
import time
from datetime import datetime
import requests

from utils.tools import choose_greeting


def _research_topic(topic):
    url = f"https://api.duckduckgo.com/?q={topic}&format=json&no_redirect=1"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        return data.get("Abstract", "")[:200]
    except Exception:
        return ""


def schedule_howru(send_func, chat_id, history_provider=None, probability=0.35, check_interval_hours=6):
    """Periodically ask the user how they are."""

    def _loop():
        while True:
            time.sleep(check_interval_hours * 3600 * random.uniform(0.5, 1.5))
            if random.random() < probability:
                history = history_provider() if history_provider else []
                message = choose_greeting(history)
                if history:
                    snippet = _research_topic(history[-1][:20].replace(" ", "+"))
                    if snippet:
                        message += f"\n\nЯ изучил тему и нашёл: {snippet}"
                send_func(chat_id, message)
    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
    return thread

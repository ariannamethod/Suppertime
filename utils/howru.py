import random
import threading
import time
from datetime import datetime

GREETINGS_RU = [
    "Эй, как дела?", "Привет! Что нового?", "Хэй, как ты?", "Как настроение?"
]
GREETINGS_EN = [
    "Hey, how are you?", "Hi there, all good?", "Hello! How's it going?", "Yo, how's life?"
]

def _craft_greeting(history):
    if not history:
        return random.choice(GREETINGS_RU + GREETINGS_EN)
    last_msg = history[-1]
    words = last_msg.replace("\n", " ").split()
    theme = " ".join(words[:5])
    if any(c in theme for c in "ёйцукенгшщзхъфывапролджэячсмитьбю"):
        return f"Привет, как дела? Я помню нашу тему: {theme}..."
    return f"Hey, how's it going? Remember we talked about {theme}?"


def schedule_howru(get_users, get_history, send_func):
    """Periodically send a friendly check-in to random users."""
    def _loop():
        while True:
            # wait between 2 and 4 hours
            time.sleep(random.uniform(7200, 14400))
            if random.random() < 0.2:
                users = get_users()
                if not users:
                    continue
                chat_id = random.choice(users)
                history = get_history(chat_id)
                msg = _craft_greeting(history)
                send_func(chat_id, msg)
    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
    return thread

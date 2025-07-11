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
    sample = random.choice(history)
    if any(c in sample for c in "ёйцукенгшщзхъфывапролджэячсмитьбю"):
        return f"Привет, как дела? Я тут подумал о \"{sample[:30]}\"..."
    return f"Hey, how's it going? I was thinking about '{sample[:30]}'..."


def schedule_howru(get_users, get_history, send_func):
    """Periodically send a friendly check-in to random users."""
    def _loop():
        while True:
            # wait between 2 and 4 hours
            time.sleep(random.uniform(7200, 14400))
            if random.random() < 0.35:
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

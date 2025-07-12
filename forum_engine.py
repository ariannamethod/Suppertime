import os
import random
from typing import List, Dict

from utils.config import _load_snapshot

from forum_utils import (
    Andrew,
    Jan,
    Judas,
    Mark,
    Mary,
    Matthew,
    Paul,
    Peter,
    Thomas,
    Yakov,
    Yeshu,
    Dubrovsky,
)

# Load field text and snapshot once
with open(os.path.join('forum', 'field', 'SUPPERTIME (v1.6).md'), 'r', encoding='utf-8') as f:
    FIELD_TEXT = f.read().strip()

SNAPSHOT = _load_snapshot()

AGENTS = {
    'Andrew': Andrew.respond,
    'Jan': Jan.respond,
    'Judas': Judas.respond,
    'Mark': Mark.respond,
    'Mary': Mary.respond,
    'Matthew': Matthew.respond,
    'Paul': Paul.respond,
    'Peter': Peter.respond,
    'Thomas': Thomas.respond,
    'Yakov': Yakov.respond,
    'Yeshu': Yeshu.respond,
    'Dubrovsky': Dubrovsky.respond,
}

HISTORY: List[Dict[str, str]] = [{'role': 'system', 'content': FIELD_TEXT}]
USER_MESSAGES = 0


def _pick_agents(count: int = 2) -> List[str]:
    return random.sample(list(AGENTS.keys()), k=count)


def start_forum() -> List[Dict[str, str]]:
    """Generate a few opening messages from random agents."""
    HISTORY.clear()
    HISTORY.append({'role': 'system', 'content': FIELD_TEXT})
    msgs = []
    for _ in range(3):
        name = random.choice(list(AGENTS.keys()))
        reply = AGENTS[name](HISTORY)
        HISTORY.append({'role': name, 'content': reply})
        msgs.append({'name': name, 'text': reply})
    return msgs


def user_message(text: str) -> List[Dict[str, str]]:
    global USER_MESSAGES
    USER_MESSAGES += 1
    if USER_MESSAGES > 90:
        USER_MESSAGES = 0
        HISTORY.clear()
        HISTORY.append({'role': 'system', 'content': FIELD_TEXT})
        return [{'name': 'system', 'text': '*** The forum glitches and resets ***'}]

    HISTORY.append({'role': 'user', 'content': text})
    triggered = [name for name in AGENTS if name.lower() in text.lower()]
    if not triggered:
        triggered = _pick_agents(2)

    replies = []
    for name in triggered:
        reply = AGENTS[name](HISTORY)
        HISTORY.append({'role': name, 'content': reply})
        replies.append({'name': name, 'text': reply})
    return replies

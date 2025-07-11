import random

MAX_MESSAGE_LENGTH = 4000

def split_for_telegram(text, max_length=MAX_MESSAGE_LENGTH):
    """Split text into chunks suitable for Telegram."""
    parts = []
    text = text.strip()
    while len(text) > max_length:
        idx = text.rfind('\n', 0, max_length)
        if idx == -1:
            idx = max_length
        parts.append(text[:idx])
        text = text[idx:].lstrip('\n')
    if text:
        parts.append(text)
    return parts or [""]


def send_long_message(chat_id, text, send_func, reply_to_message_id=None):
    """Send long text by splitting into multiple Telegram messages."""
    parts = split_for_telegram(text)
    for part in parts:
        send_func(chat_id, part, reply_to_message_id=reply_to_message_id)
        reply_to_message_id = None
    return len(parts)

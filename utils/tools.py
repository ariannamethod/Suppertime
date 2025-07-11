import random


def split_long_text(text, max_length=4000):
    """Split text into segments not exceeding max_length."""
    if len(text) <= max_length:
        return [text]

    parts = []
    remaining = text
    while len(remaining) > max_length:
        half = min(max_length, len(remaining) // 2 + 1)
        idx = remaining.rfind('\n', 0, half)
        if idx == -1:
            idx = half
        parts.append(remaining[:idx].strip())
        remaining = remaining[idx:].lstrip('\n')
    if remaining:
        parts.append(remaining)
    return parts


def choose_greeting(history_snippets):
    greetings = [
        "Привет, как дела?",
        "Эй, что нового?",
        "Как ты там?",
        "Йо, как настроение?",
    ]
    base = random.choice(greetings)
    if history_snippets:
        base = f"{base} Вспомнил, как мы обсуждали {history_snippets[-1][:40]}..."
    return base

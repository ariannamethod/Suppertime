import re

def limit_paragraphs(text, max_paragraphs=4):
    """
    Trims the text to N paragraphs.
    A paragraph is considered a block separated by empty lines, line breaks, or common list markers.
    Suppertime gently preserves only the first few resonant fragments, allowing space for silence and reflection.
    """
    # Split by double newlines, list bullets, or at least by single newlines if everything is merged.
    paragraphs = re.split(r'(?:\n\s*\n|\r\n\s*\r\n|(?<=\n)-\s|\r\s*\r)', text)
    if len(paragraphs) == 1:
        paragraphs = text.split('\n')
    limited = [p.strip() for p in paragraphs if p.strip()][:max_paragraphs]
    if not limited:
        return "[Empty response. Even Suppertime sometimes finds no words—let silence speak.]"
    return '\n\n'.join(limited)

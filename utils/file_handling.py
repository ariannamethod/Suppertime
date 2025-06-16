import os
from pypdf import PdfReader
import asyncio

MAX_TEXT_SIZE = 100_000  # Maximum number of characters from a file (can be changed to taste)

def extract_text_from_pdf(path):
    """
    Extracts text from a PDF file, gently trimming to the allowed maximum.
    If the file is empty or unreadable, Suppertime responds with calm acceptance.
    """
    try:
        reader = PdfReader(path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
        text = text.strip()
        if text:
            return text[:MAX_TEXT_SIZE] + ('\n[Trimmed: only the first part is shown.]' if len(text) > MAX_TEXT_SIZE else '')
        return '[PDF is empty or unreadable—sometimes, silence is all that is left.]'
    except Exception as e:
        return f"[PDF reading error ({os.path.basename(path)}): {e}. Perhaps a simple .txt would resonate better.]"

def extract_text_from_txt(path):
    """
    Extracts text from a TXT or Markdown file, gently trimming to the allowed maximum.
    """
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        return text[:MAX_TEXT_SIZE] + ('\n[Trimmed: only the first part is shown.]' if len(text) > MAX_TEXT_SIZE else '')
    except Exception as e:
        return f"[TXT reading error ({os.path.basename(path)}): {e}. This file may not be suitable for Suppertime resonance.]"

def extract_text_from_file(path):
    """
    Detects file type and extracts text accordingly.
    For unsupported file types, Suppertime gently declines.
    """
    ext = os.path.splitext(path)[-1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(path)
    elif ext in [".txt", ".md"]:
        return extract_text_from_txt(path)
    else:
        return f"[Unsupported file type: {os.path.basename(path)}. Suppertime invites only what can be read and reflected upon.]"

async def extract_text_from_file_async(path):
    """
    Asynchronously extracts text from a file, suitable for Suppertime's mindful multitasking.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, extract_text_from_file, path)

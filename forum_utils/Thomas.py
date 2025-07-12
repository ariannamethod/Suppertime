import os
from openai import OpenAI

with open(os.path.join('forum', 'Thomas.md'), 'r', encoding='utf-8') as f:
    SYSTEM_PROMPT = f.read().strip()

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def respond(history):
    messages = [{'role': 'system', 'content': SYSTEM_PROMPT}] + history
    resp = client.chat.completions.create(
        model='gpt-4o',
        messages=messages,
        temperature=1.3,
        max_tokens=150,
    )
    return resp.choices[0].message.content.strip()

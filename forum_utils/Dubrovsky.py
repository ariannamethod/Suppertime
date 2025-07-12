import os
from openai import OpenAI

with open(os.path.join('forum', 'Dubrovsky.md'), 'r', encoding='utf-8') as f:
    PROMPT1 = f.read().strip()
with open(os.path.join('forum', 'Dubrovsky_examples.md'), 'r', encoding='utf-8') as f:
    PROMPT2 = f.read().strip()

SYSTEM_PROMPT = PROMPT1 + "\n\n" + PROMPT2

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

const form = document.getElementById('chat-form');
const input = document.getElementById('chat-input');
const messages = document.getElementById('messages');

function addMessage(text, cls) {
    const div = document.createElement('div');
    div.className = 'message ' + cls;
    div.textContent = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
}

async function startForum() {
    const res = await fetch('/forum/start');
    const data = await res.json();
    data.messages.forEach(m => addMessage(m.name + ': ' + m.text, 'assistant'));
}

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    addMessage(text, 'user');
    input.value = '';
    const res = await fetch('/forum/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
    });
    const data = await res.json();
    data.messages.forEach(m => addMessage(m.name + ': ' + m.text, 'assistant'));
});

window.addEventListener('DOMContentLoaded', startForum);

// Chatbot frontend logic
const messages = document.getElementById('chatbot-messages');
const form = document.getElementById('chatbot-form');
const input = document.getElementById('chatbot-input');

function appendMessage(text, sender = 'bot') {
  const msg = document.createElement('div');
  msg.style.margin = '8px 0';
  msg.style.padding = '8px';
  msg.style.borderRadius = '8px';
  msg.style.background = sender === 'bot' ? '#e3f2fd' : '#d1ffd6';
  msg.style.textAlign = sender === 'bot' ? 'left' : 'right';
  msg.textContent = text;
  messages.appendChild(msg);
  messages.scrollTop = messages.scrollHeight;
}

form.addEventListener('submit', async e => {
  e.preventDefault();
  const userText = input.value.trim();
  if (!userText) return;
  appendMessage(userText, 'user');
  input.value = '';
  // Send to backend
  const res = await fetch('/chatbot', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message: userText})
  });
  const data = await res.json();
  appendMessage(data.reply);
});

appendMessage('Hello! Ask me about your expenses, set limits, or get analytics.');

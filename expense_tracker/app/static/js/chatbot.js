// Chatbot frontend logic
const messages = document.getElementById('chatbot-messages');
const form = document.getElementById('chatbot-form');
const input = document.getElementById('chatbot-input');
const container = document.getElementById('chatbot-container');
const toggleBtn = document.getElementById('chatbot-toggle');

function toggleChat() {
  container.classList.toggle('active');
  toggleBtn.classList.toggle('active');
  if (container.classList.contains('active')) {
    input.focus();
  }
}

if (toggleBtn) {
  toggleBtn.addEventListener('click', toggleChat);
}

function appendMessage(text, sender = 'bot') {
  if (!messages) return;
  const msg = document.createElement('div');
  msg.className = `msg ${sender}`;
  msg.textContent = text;
  messages.appendChild(msg);
  messages.scrollTop = messages.scrollHeight;
}

window.toggleChat = toggleChat;
window.appendMessage = appendMessage;
console.log("Chatbot AI Co-pilot initialized");

form.addEventListener('submit', async e => {
  e.preventDefault();
  const userText = input.value.trim();
  if (!userText) return;

  appendMessage(userText, 'user');
  input.value = '';

  // Show loading indicator
  const loadingId = 'msg-' + Date.now();
  const loadingMsg = document.createElement('div');
  loadingMsg.className = 'msg bot loading';
  loadingMsg.id = loadingId;
  loadingMsg.textContent = 'Thinking...';
  messages.appendChild(loadingMsg);
  messages.scrollTop = messages.scrollHeight;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: userText })
    });

    const data = await res.json();

    // Remove loading and show reply
    const loadingElem = document.getElementById(loadingId);
    if (loadingElem) loadingElem.remove();

    if (data.reply) {
      appendMessage(data.reply);
    } else if (data.error) {
      appendMessage('Error: ' + data.error);
    } else {
      appendMessage('I received an empty response from the server.');
    }
  } catch (err) {
    console.error('Chat error:', err);
    const loadingElem = document.getElementById(loadingId);
    if (loadingElem) loadingElem.remove();
    appendMessage('Sorry, I am having trouble connecting to the server. Is the application running?');
  }
});

appendMessage('Hello! I am your permanent Finance AI Co-pilot. I have full access to your records and can help you analyze spending, set limits, or answer any financial questions. How can I assist you today?');

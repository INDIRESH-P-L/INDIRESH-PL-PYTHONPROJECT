// ── Chatbot Frontend — TrackEx Finance AI ─────────────────────────────────
const messages = document.getElementById('chatbot-messages');
const form = document.getElementById('chatbot-form');
const input = document.getElementById('chatbot-input');
const container = document.getElementById('chatbot-container');
const toggleBtn = document.getElementById('chatbot-toggle');

// ── Toggle open/close ─────────────────────────────────────────────────────
function toggleChat() {
  container.classList.toggle('active');
  toggleBtn.classList.toggle('active');
  if (container.classList.contains('active')) input.focus();
}
if (toggleBtn) toggleBtn.addEventListener('click', toggleChat);
window.toggleChat = toggleChat;

// ── Render markdown-like text to HTML ────────────────────────────────────────
function renderMarkdown(text) {
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code style="background:rgba(0,0,0,.08);padding:1px 5px;border-radius:4px;">$1</code>')
    .replace(/\n/g, '<br>');
}

// ── Append a message bubble ───────────────────────────────────────────────────
function appendMessage(text, sender = 'bot') {
  if (!messages) return;
  const msg = document.createElement('div');
  msg.className = `msg ${sender}`;
  if (sender === 'bot') {
    msg.innerHTML = renderMarkdown(text);
  } else {
    msg.textContent = text;
  }
  messages.appendChild(msg);
  messages.scrollTop = messages.scrollHeight;
}
window.appendMessage = appendMessage;

// ── Suggested quick commands ─────────────────────────────────────────────────
const SUGGESTIONS = [
  'Analyze my spending',
  'What is my balance?',
  'Show my limits',
  'Give me a savings tip',
];

function renderSuggestions() {
  if (!messages) return;
  const wrap = document.createElement('div');
  wrap.style.cssText = 'display:flex;flex-wrap:wrap;gap:6px;margin-top:6px;';
  SUGGESTIONS.forEach(s => {
    const chip = document.createElement('button');
    chip.textContent = s;
    chip.style.cssText = `
      background: var(--green-dim, rgba(6,182,212,.1));
      color: var(--green, #06b6d4);
      border: 1px solid rgba(6,182,212,.25);
      border-radius: 20px; padding: 4px 12px;
      font-size: .78rem; font-weight: 600; cursor: pointer;
      transition: background .2s;
    `;
    chip.onmouseenter = () => chip.style.background = 'rgba(6,182,212,.2)';
    chip.onmouseleave = () => chip.style.background = 'var(--green-dim, rgba(6,182,212,.1))';
    chip.onclick = () => { input.value = s; input.focus(); };
    wrap.appendChild(chip);
  });
  messages.appendChild(wrap);
  messages.scrollTop = messages.scrollHeight;
}

// ── Send a message ────────────────────────────────────────────────────────────
async function sendMessage(text) {
  if (!text.trim()) return;
  appendMessage(text, 'user');
  input.value = '';

  // Loading bubble
  const loadingMsg = document.createElement('div');
  loadingMsg.className = 'msg bot loading';
  loadingMsg.innerHTML = '<span style="opacity:.6">●</span> <span style="opacity:.4">●</span> <span style="opacity:.2">●</span>';
  loadingMsg.style.cssText = 'display:flex;gap:4px;align-items:center;font-size:1.4rem;letter-spacing:2px;';
  messages.appendChild(loadingMsg);
  messages.scrollTop = messages.scrollHeight;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text })
    });
    const data = await res.json();
    loadingMsg.remove();

    if (data.reply) appendMessage(data.reply);
    else if (data.error) appendMessage('❌ ' + data.error);
    else appendMessage('I received an empty response. Please try again.');
  } catch (err) {
    loadingMsg.remove();
    appendMessage('⚠️ Unable to reach the server. Please ensure the application is running.');
    console.error('Chat fetch error:', err);
  }
}

// ── Form submit ───────────────────────────────────────────────────────────────
if (form) {
  form.addEventListener('submit', e => {
    e.preventDefault();
    sendMessage(input.value.trim());
  });
}

// (Redundant keydown listener removed — form submit handles Enter)

// ── Welcome message ───────────────────────────────────────────────────────────
appendMessage('🚀 **Full Control AI Active!**\n\nI can now manage your finances directly. Try these commands:\n• **"Add expense 500 Food"**\n• **"Add income 25000"**\n• **"Delete my last transaction"**\n• **"What is my balance?"**\n• **"Set limit Food 5000"**\n\nHow can I help you take control of your money today?');
renderSuggestions();
console.log('TrackEx Brain V2 initialized ✓');

# 💰 TrackEx — AI-Powered Expense Tracker

A modern, full-stack personal finance management web application built with Python (Flask) and SQLite.

---

## 🌟 Features

- **Dark Cyber Galactic Landing Page** — Stunning animated landing with floating elements and live dashboard mockup
- **Premium Light Dashboard** — Clean, gradient-based dashboard with glassmorphism cards
- **Transaction Tracking** — Add income & expenses with categories, notes, and dates
- **AI Finance Assistant** — Built-in chatbot powered by rule-based AI for spending insights
- **Spending Analytics** — Monthly trend charts, expense breakdowns, and category bars
- **Budget Limits** — Set and monitor spending limits per category
- **Google OAuth** — Sign in with Google (configurable via environment variables)
- **Velocity Cards** — Daily average, month-end projections, and budget health
- **Responsive Design** — Works on desktop and tablet

---

## 🗂 Project Structure

```
expense_tracker/
├── app/
│   ├── __init__.py          # Flask app factory & blueprint registration
│   ├── auth.py              # Login, register, logout, Google OAuth
│   ├── routes.py            # API routes (transactions, categories, limits)
│   ├── models.py            # Business logic & AI insights
│   ├── ai_agent.py          # AI finance assistant engine
│   ├── database.py          # DB init & connection helpers
│   ├── static/
│   │   ├── css/style.css    # Main design system & stylesheet
│   │   └── js/
│   │       ├── app.js       # Dashboard logic & API calls
│   │       └── chatbot.js   # Chatbot popup logic
│   └── templates/
│       ├── landing.html     # Public landing page (dark theme)
│       ├── index.html       # Main dashboard (light theme)
│       ├── login.html       # Login page
│       ├── register.html    # Registration page
│       └── chatbot.html     # Chatbot UI component
├── data/
│   └── expenses.db          # SQLite database (auto-created, not in git)
├── config.py                # App configuration (dev / production)
├── run.py                   # Entry point — dev server or Waitress (prod)
├── requirements.txt         # Python dependencies
├── start_server.bat         # Windows convenience launcher
└── .gitignore
```

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd expense_tracker
```

### 2. Create a virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment (optional)
Create a `.env` file in the root:
```env
SECRET_KEY=your-secret-key
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### 5. Run the app
```bash
python run.py
```

Then open **http://127.0.0.1:5001** in your browser.

---

## 🏭 Production Deployment

Set `FLASK_ENV=production` before running — the app will automatically use **Waitress** WSGI server:

```bash
set FLASK_ENV=production   # Windows
python run.py
```

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3, Flask |
| Database | SQLite (built-in) |
| Frontend | HTML5, Vanilla CSS, Vanilla JS |
| Fonts | Google Fonts (Inter, Outfit) |
| Charts | Chart.js |
| WSGI Server | Waitress (production) |
| Auth | Session-based + Google OAuth |

---

## 📦 Dependencies

```
Flask
requests
python-dotenv
waitress
```

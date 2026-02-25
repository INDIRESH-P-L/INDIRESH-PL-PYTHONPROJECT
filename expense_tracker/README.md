# 💰 Expense Tracker

A modern, full-featured expense tracker built with **Python Flask** + **SQLite** and a premium dark-mode web UI.

## Project Structure

```
expense_tracker/
├── run.py                   # Entry point
├── config.py                # App configuration
├── requirements.txt
├── .gitignore
├── data/
│   └── expenses.db          # Auto-created SQLite DB
└── app/
    ├── __init__.py          # Flask app factory
    ├── database.py          # DB connection & schema
    ├── models.py            # Query layer
    ├── routes.py            # REST API blueprint (/api)
    ├── static/
    │   ├── css/
    │   │   └── style.css    # Design system stylesheet
    │   └── js/
    │       └── app.js       # Frontend application (Chart.js)
    └── templates/
        └── index.html       # Main dashboard page
```

## Features

- ✅ Add **income** and **expense** transactions
- ✅ **Live balance** (animated counter, colour-coded)
- ✅ **Monthly trend** bar chart (last 6 months)
- ✅ **Donut chart** for expense category breakdown
- ✅ **Category bars** with colour-coded percentage fill
- ✅ **Search** transactions by category or note
- ✅ **Filter** by All / Income / Expense
- ✅ **Month filter** to drill into a specific period
- ✅ **Delete** records with one click
- ✅ Persistent **SQLite** storage

## Quick Start

```bash
cd expense_tracker
pip install -r requirements.txt
python run.py
```

Then open **http://127.0.0.1:5000** in your browser.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | /api/transactions | List all (filter: `?type=income&month=2026-02`) |
| POST   | /api/transactions | Add new transaction |
| DELETE | /api/transactions/<id> | Delete by ID |
| GET    | /api/summary | Income / expense / balance totals + trend |
| GET    | /api/months  | Available months for dropdown |

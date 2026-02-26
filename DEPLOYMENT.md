# Expense Tracker Deployment Guide

## 1. Install Python (>=3.10)
Download and install Python from https://www.python.org/downloads/

## 2. Clone the Repository
```
git clone https://github.com/INDIRESH-P-L/INDIRESH-PL-PYTHONPROJECT.git
cd INDIRESH-PL-PYTHONPROJECT
```

## 3. Create Virtual Environment
```
python -m venv venv
venv\Scripts\activate   # On Windows
```

## 4. Install Dependencies
```
pip install -r expense_tracker/requirements.txt
```

## 5. Run the App with Waitress
```
python expense_tracker/run.py
```

## 6. (Optional) Configure Reverse Proxy
- Use Nginx or Apache to forward requests to http://127.0.0.1:5001
- Set up HTTPS for secure access

## 7. Access the App
- Open your browser and go to http://<server-ip>:5001

## 8. Share the URL with users

---
For advanced deployment (cloud, domain, HTTPS), ask for platform-specific instructions.

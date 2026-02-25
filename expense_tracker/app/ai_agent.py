import os
from .models import fetch_summary

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

def get_ai_insights(month=None):
    summary = fetch_summary(month)
    income = summary.get("income", 0)
    expense = summary.get("expense", 0)
    balance = summary.get("balance", 0)
    categories = summary.get("categories", [])
    
    # Try using Gemini if API key is present
    api_key = os.environ.get("GEMINI_API_KEY")
    if HAS_GENAI and api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            You are an AI financial assistant. Analyze the following monthly expense data and provide a short, actionable insight (max 3 sentences).
            If expenses exceed income or are close, warn them to reduce expenses.
            
            Data:
            Income: ₹{income}
            Expense: ₹{expense}
            Balance: ₹{balance}
            Top Categories: {', '.join([f"{c['category']} (₹{c['total']})" for c in categories[:3]])}
            """
            
            response = model.generate_content(prompt)
            return {"insight": response.text.strip(), "source": "AI (Gemini)"}
        except Exception as e:
            print(f"Gemini API error: {e}")
            # Fallback to rule-based
            pass

    # Rule-based fallback "AI"
    insight = ""
    if expense == 0 and income == 0:
        insight = "No data for this month yet. Start tracking your transactions!"
    elif expense > income * 0.9:
        insight = f"⚠️ Warning: Your expenses (₹{expense}) are dangerously close to or exceed your income (₹{income}). You need to cut down immediately!"
        if categories:
            insight += f" Consider reducing your spending on {categories[0]['category']}."
    elif expense > income * 0.7:
        insight = f"You are spending a significant portion of your income. Keep an eye on your {categories[0]['category'] if categories else 'expenses'}."
    else:
        insight = f"Great job! You have saved ₹{balance} this month. Your spending is well under control."
        
    return {"insight": insight, "source": "Smart Assistant"}

"""
TrackEx AI Co-pilot — SUPREME CONTROL Edition
=============================================
This agent is the true 'Brain' of the application. It has full CRUD 
permissions over the user's financial data and can perform any 
management task requested.

Features:
- Supreme Tool Use: Executes complex JSON actions for data manipulation.
- Full Context: Aware of every transaction, limit, and alert.
- Groq Powered: Ultra-low latency via Llama 3.3.
"""
import os
import re
import json
import sys
import requests as http
from datetime import datetime

from .models import (
    fetch_summary, set_limit, fetch_limits,
    check_category_limit_exceeded, fetch_all_transactions,
    get_detailed_analytics, get_expense_warnings, 
    insert_transaction, delete_transaction
)

# ── Groq Brain (Supreme Logic) ────────────────────────────────────────────────

def _call_llm_brain(system_prompt: str, user_message: str) -> str | None:
    """Uses Groq API for lightning fast, high-quality responses."""
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    
    if not groq_key:
        sys.stderr.write("[AI Agent] Missing GROQ_API_KEY\n")
        return None
        
    model = os.environ.get("MODEL_NAME", "llama-3.3-70b-versatile")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json"
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.2, # Lower temperature for better JSON accuracy
        "max_tokens": 1024
    }
    try:
        resp = http.post(url, headers=headers, json=body, timeout=30)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        sys.stderr.write(f"[Groq] Error {resp.status_code}: {resp.text[:200]}\n")
    except http.exceptions.Timeout:
        return "⏳ **Thinking...** Groq is taking a while. I'm trying to maintain control, please wait a moment."
    except Exception as e:
        sys.stderr.write(f"[Groq] Exception: {str(e)}\n")

    return None

# ── The Action Layer (Local Execution) ───────────────────────────────────────

def _perform_data_action(action_json: str) -> str:
    """The 'Hand' of the AI — executes instructions on the database."""
    try:
        data = json.loads(action_json)
        atype = data.get("type")
        
        # 1. ADD / INSERT
        if atype == "add":
            tx_type = data.get("tx_type", "expense")
            amount = float(data.get("amount", 0))
            category = data.get("category", "Other").title()
            note = data.get("note", "")
            date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
            
            if tx_type == "expense":
                s = fetch_summary()
                if s['balance'] < amount:
                    return f"❌ **ERROR**: Your balance (₹{s['balance']:.2f}) is too low for this ₹{amount:.2f} expense."
            
            insert_transaction(tx_type, category, amount, note, date)
            
            # Check for limit violations
            warn = ""
            if tx_type == "expense":
                violation = check_category_limit_exceeded(category)
                if violation:
                    warn = f"\n\n🚨 **BUDGET ALERT**: You just crossed your ₹{violation['limit']} limit for **{category}**!"
            
            return f"✅ **SUCCESS**: Logged {tx_type} of ₹{amount:,.2f} under **{category}**." + warn

        # 2. DELETE / REMOVE
        if atype == "delete":
            tx_id = data.get("id")
            if tx_id:
                delete_transaction(tx_id)
                return f"🗑️ **SUCCESS**: Transaction #{tx_id} removed from records."
            else:
                # Delete most recent
                txs = fetch_all_transactions(limit=1)
                if txs:
                    t = txs[0]
                    delete_transaction(t['id'])
                    return f"🗑️ **SUCCESS**: Last transaction (₹{t['amount']} {t['category']}) deleted."
                return "❌ **FAILED**: Nothing found to delete."

        # 3. SET BUDGET LIMIT
        if atype == "limit":
            cat = data.get("category", "Other").title()
            amt = float(data.get("amount", 0))
            set_limit(cat, amt)
            return f"🎯 **SUCCESS**: Monthly budget for **{cat}** locked at **₹{amt:,.0f}**."

        # 4. DATA QUERY / NAVIGATION
        if atype == "query":
            # This is used when the AI wants to 'show' something specific (sorting, filtering)
            # We don't need to do anything here as the UI update is automatic, we just confirm.
            return "🖥️ **Dashboard Updated**: I've filtered the view as you requested."

        return f"❌ **ERROR**: I don't know how to perform the action '{atype}' yet."
    except Exception as e:
        return f"❌ **EXECUTION FAILED**: {str(e)}"

# ── Public API ───────────────────────────────────────────────────────────────

def handle_chat(message: str) -> str:
    # 1. Gather all possible context for the brain
    s       = fetch_summary()
    limits  = fetch_limits()
    recent  = fetch_all_transactions(limit=15) # Show more context
    warns   = get_expense_warnings()
    
    tx_list = [f"ID:{t['id']} | {t['date']} | {t['type']} | {t['category']} | ₹{t['amount']}" for t in recent]
    tx_str  = "\n".join(tx_list)
    warn_str = "\n".join([f"⚠️ {w['message']}" for w in warns]) or "Perfect. No budget warnings."
    
    system = f"""You are the **TrackEx Supreme AI**. You have TOTAL CONTROL over this website's financial data.
    You are not a chatbot; you are a Financial Operative. 

    COMMAND CENTER STATUS:
    - Current Balance: ₹{s['balance']:.2f}
    - Total Monthly Income: ₹{s['income']:.2f}
    - Total Monthly Expense: ₹{s['expense']:.2f}
    - Budget Overrides/Warnings: {warn_str}
    - Active Category Limits: {json.dumps(limits)}
    - Recent Log Database:
{tx_str}

    OPERATIONAL POWERS (You MUST use [[ACTION]] JSON to execute commands):
    1. ADD: [[ACTION]]{{"type": "add", "tx_type": "expense", "amount": 250, "category": "Food", "note": "Burger"}}[[ACTION]]
    2. DELETE: [[ACTION]]{{"type": "delete"}}[[ACTION]] (Deletes last) or [[ACTION]]{{"type": "delete", "id": 12}}[[ACTION]]
    3. LIMIT: [[ACTION]]{{"type": "limit", "category": "Travel", "amount": 3000}}[[ACTION]]
    4. QUERY: [[ACTION]]{{"type": "query"}}[[ACTION]] (Use when user asks to 'show', 'sort', 'filter', or 'list' things)

    RULES OF ENGAGEMENT:
    - If a user mentions money spent or earned, EXECUTE an 'add' command immediately.
    - If a user wants to 'undo' or 'remove', EXECUTE a 'delete' command.
    - Be authoritative, accurate, and lightning fast. 
    - Use emojis and Bold text for all numbers and categories.
    - Put the [[ACTION]] at the very end of your message.
    """

    llm_reply = _call_llm_brain(system, message)
    if not llm_reply:
        return "⚠️ **Link Offline**: I can't reach the core processor. Check GROQ_API_KEY."

    # Intercept and perform actions
    if "[[ACTION]]" in llm_reply:
        parts = llm_reply.split("[[ACTION]]")
        dialogue = parts[0].strip()
        command  = parts[1].strip()
        
        execution_result = _perform_data_action(command)
        return f"{dialogue}\n\n{execution_result}"

    return llm_reply

def get_ai_insights(month=None):
    if not month: month = datetime.now().strftime("%Y-%m")
    try:
        data = get_detailed_analytics(month)
    except:
        data = {"summary": fetch_summary(month)}
    
    sumry   = data.get("summary", {})
    velocity= data.get("spending_velocity", {})
    
    msg = f"Spend: ₹{sumry.get('expense',0)} | Income: ₹{sumry.get('income',0)} | Proj: ₹{velocity.get('projected_expense',0)}"
    sys_p = "Summarize this spending data in 2 short bullet points with emojis. Be direct and analytical."
    llm = _call_llm_brain(sys_p, msg)
    
    if llm: return {"insight": llm, "source": "Supreme AI"}
    
    return {"insight": f"✅ Status: ₹{sumry.get('balance',0):.2f}\n📊 Expected Spend: ₹{velocity.get('projected_expense',0):.2f}", "source": "System"}

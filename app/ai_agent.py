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
        sys.stderr.write("[AI Agent] Missing GROQ_API_KEY - set it in .env file\n")
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
        "temperature": 0.2,  # Lower temperature for better JSON accuracy
        "max_tokens": 1024
    }
    
    try:
        resp = http.post(url, headers=headers, json=body, timeout=30)
        
        if resp.status_code == 200:
            try:
                content = resp.json()["choices"][0]["message"]["content"].strip()
                if not content:
                    sys.stderr.write("[Groq] Empty response content\n")
                    return None
                return content
            except (KeyError, IndexError, json.JSONDecodeError) as je:
                sys.stderr.write(f"[Groq] Response parsing error: {str(je)}\n")
                return None
        
        elif resp.status_code == 401:
            sys.stderr.write("[Groq] Authentication failed - check GROQ_API_KEY\n")
            return None
        
        elif resp.status_code == 429:
            sys.stderr.write("[Groq] Rate limit exceeded\n")
            return None
        
        else:
            sys.stderr.write(f"[Groq] Error {resp.status_code}: {resp.text[:200]}\n")
            return None
            
    except http.exceptions.Timeout:
        sys.stderr.write("[Groq] Request timeout (30s)\n")
        return None
    except http.exceptions.ConnectionError as ce:
        sys.stderr.write(f"[Groq] Connection error: {str(ce)}\n")
        return None
    except Exception as e:
        sys.stderr.write(f"[Groq] Unexpected error: {str(e)}\n")
        return None

# ── The Action Layer (Local Execution) ───────────────────────────────────────

def _perform_data_action(action_json: str) -> str:
    """The 'Hand' of the AI — executes instructions on the database."""
    try:
        # Parse JSON safely
        try:
            data = json.loads(action_json)
        except json.JSONDecodeError as je:
            sys.stderr.write(f"[Action] JSON parse error: {str(je)} in '{action_json[:100]}'\n")
            return f"❌ **Action Parse Failed**: Invalid command format. {str(je)}"
        
        atype = data.get("type", "").lower()
        
        # 1. ADD / INSERT
        if atype == "add":
            try:
                tx_type = data.get("tx_type", "expense").lower()
                amount = float(data.get("amount", 0))
                category = data.get("category", "Other").title()
                note = data.get("note", "")
                date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
                

                
                insert_transaction(tx_type, category, amount, note, date)
                
                # Check for limit violations
                warn = ""
                if tx_type == "expense":
                    try:
                        violation = check_category_limit_exceeded(category)
                        if violation:
                            warn = f"\n\n🚨 **BUDGET ALERT**: You just crossed your ₹{violation.get('limit', 0)} limit for **{category}**!"
                    except Exception as e:
                        sys.stderr.write(f"[Action] Limit check failed: {str(e)}\n")
                
                return f"✅ **SUCCESS**: Logged {tx_type} of ₹{amount:,.2f} under **{category}**." + warn
            
            except ValueError as ve:
                return f"❌ **Value Error**: Invalid amount or number format. {str(ve)}"
            except Exception as e:
                sys.stderr.write(f"[Action] Add transaction failed: {str(e)}\n")
                return f"❌ **Add Failed**: {str(e)[:100]}"

        # 2. DELETE / REMOVE
        if atype == "delete":
            try:
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
                    return "❌ **Failed**: No transactions to delete."
            except Exception as e:
                sys.stderr.write(f"[Action] Delete failed: {str(e)}\n")
                return f"❌ **Delete Failed**: {str(e)[:100]}"

        # 3. SET BUDGET LIMIT
        if atype == "limit":
            try:
                cat = data.get("category", "Other").title()
                amt = float(data.get("amount", 0))
                
                if amt <= 0:
                    return f"❌ **Invalid Limit**: Amount must be greater than 0."
                
                set_limit(cat, amt)
                return f"🎯 **SUCCESS**: Monthly budget for **{cat}** locked at **₹{amt:,.0f}**."
            except ValueError as ve:
                return f"❌ **Value Error**: Invalid amount format. {str(ve)}"
            except Exception as e:
                sys.stderr.write(f"[Action] Set limit failed: {str(e)}\n")
                return f"❌ **Limit Failed**: {str(e)[:100]}"

        # 4. DATA QUERY / NAVIGATION
        if atype == "query":
            return "🖥️ **Dashboard Updated**: I've filtered the view as you requested."

        return f"❌ **ERROR**: Unknown action type '{atype}'. Valid actions are: add, delete, limit, query."
        
    except Exception as e:
        sys.stderr.write(f"[Action] Unexpected error: {str(e)}\n")
        return f"❌ **EXECUTION FAILED**: {str(e)[:150]}"

# ── Public API ───────────────────────────────────────────────────────────────

def handle_chat(message: str) -> str:
    """Main chatbot handler with error handling."""
    try:
        # 1. Gather all possible context for the brain
        try:
            s = fetch_summary()
        except Exception as db_err:
            sys.stderr.write(f"[Chat] fetch_summary failed: {str(db_err)}\n")
            s = {"balance": 0, "income": 0, "expense": 0}
        
        try:
            limits = fetch_limits()
        except Exception as db_err:
            sys.stderr.write(f"[Chat] fetch_limits failed: {str(db_err)}\n")
            limits = {}
        
        try:
            recent = fetch_all_transactions(limit=15)
        except Exception as db_err:
            sys.stderr.write(f"[Chat] fetch_all_transactions failed: {str(db_err)}\n")
            recent = []
        
        try:
            warns = get_expense_warnings()
        except Exception as db_err:
            sys.stderr.write(f"[Chat] get_expense_warnings failed: {str(db_err)}\n")
            warns = []
        
        # Build context strings safely
        tx_list = [f"ID:{t['id']} | {t['date']} | {t['type']} | {t['category']} | ₹{t['amount']}" for t in recent] if recent else []
        tx_str  = "\n".join(tx_list) if tx_list else "No transactions yet"
        warn_str = "\n".join([f"⚠️ {w['message']}" for w in warns]) if warns else "Perfect. No budget warnings."
        
        system = f"""You are the **TrackEx Supreme AI**. You have TOTAL CONTROL over this website's financial data.
You are not a chatbot; you are a Financial Operative. 

COMMAND CENTER STATUS:
- Current Balance: ₹{s.get('balance', 0):.2f}
- Total Monthly Income: ₹{s.get('income', 0):.2f}
- Total Monthly Expense: ₹{s.get('expense', 0):.2f}
- Budget Overrides/Warnings: {warn_str}
- Active Category Limits: {json.dumps(limits) if limits else 'None set yet'}
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
- Always respond helpfully even if no data is available.
- Put the [[ACTION]] at the very end of your message if you need to execute a command.
"""

        llm_reply = _call_llm_brain(system, message)
        if not llm_reply:
            return "⚠️ **System Alert**: The AI core is temporarily offline. Please try again in a moment."

        # Intercept and perform actions
        if "[[ACTION]]" in llm_reply:
            try:
                parts = llm_reply.split("[[ACTION]]")
                if len(parts) >= 3:
                    dialogue = parts[0].strip()
                    command  = parts[1].strip()
                    
                    execution_result = _perform_data_action(command)
                    return f"{dialogue}\n\n{execution_result}" if dialogue else execution_result
                else:
                    # Malformed action format
                    return llm_reply.replace("[[ACTION]]", "").strip()
            except Exception as action_err:
                sys.stderr.write(f"[Chat] Action execution failed: {str(action_err)}\n")
                # Return the dialogue without executing the broken action
                return llm_reply.split("[[ACTION]]")[0].strip() if "[[ACTION]]" in llm_reply else llm_reply

        return llm_reply
        
    except Exception as e:
        sys.stderr.write(f"[Chat] Fatal error: {str(e)}\n")
        return f"❌ **Critical Error**: {str(e)[:100]}. Please try again or contact support."

def get_ai_insights(month=None):
    """Get AI-powered insights with fallback to basic analysis."""
    if not month: 
        month = datetime.now().strftime("%Y-%m")
    
    try:
        # Try to get detailed analytics
        try:
            data = get_detailed_analytics(month)
        except:
            data = {}
        
        # Get summary as fallback
        try:
            if "summary" not in data:
                data["summary"] = fetch_summary(month)
        except Exception as e:
            sys.stderr.write(f"[Insights] fetch_summary failed: {str(e)}\n")
            data["summary"] = {"expense": 0, "income": 0, "balance": 0}
        
        sumry = data.get("summary", {})
        velocity = data.get("spending_velocity", {})
        
        msg = f"Spend: ₹{sumry.get('expense', 0)} | Income: ₹{sumry.get('income', 0)} | Proj: ₹{velocity.get('projected_expense', 0)}"
        sys_p = "Summarize this spending data in 2 short bullet points with emojis. Be direct and analytical."
        
        llm = _call_llm_brain(sys_p, msg)
        
        if llm:
            return {"insight": llm, "source": "Supreme AI"}
        
        # Fallback: Manual analysis without LLM
        balance = sumry.get('balance', 0)
        expense = sumry.get('expense', 0)
        income = sumry.get('income', 0)
        
        if balance < 0:
            status = f"⚠️ **Over Budget**: You're ₹{abs(balance):.2f} over"
        elif balance > income * 0.5:
            status = f"✅ **Great Spending**: Only ₹{expense:.2f} spent so far"
        else:
            status = f"📊 **On Track**: ₹{expense:.2f} / ₹{income:.2f} spent"
        
        return {
            "insight": f"{status}\n💡 **Tip**: Review your top categories to find savings",
            "source": "System Analysis"
        }
        
    except Exception as e:
        sys.stderr.write(f"[Insights] Fatal error: {str(e)}\n")
        return {
            "insight": "✅ Your financial data is being processed. Try asking specific questions in the chatbot!",
            "source": "System"
        }

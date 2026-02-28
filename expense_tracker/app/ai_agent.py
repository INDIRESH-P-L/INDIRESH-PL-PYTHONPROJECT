import os
import re
from datetime import datetime
from .models import (
    fetch_summary, set_limit, fetch_limits, 
    check_category_limit_exceeded, fetch_all_transactions,
    fetch_ai_memory, store_ai_memory
)

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

def get_ai_insights(month=None):
    if not month:
        month = datetime.now().strftime("%Y-%m")
        
    summary = fetch_summary(month)
    income = summary.get("income", 0)
    expense = summary.get("expense", 0)
    balance = summary.get("balance", 0)
    categories = summary.get("categories", [])
    
    # Check for limit violations
    limits = fetch_limits()
    limit_warnings = []
    for cat_data in categories:
        cat_name = cat_data["category"]
        if cat_name in limits:
            limit = limits[cat_name]
            spent = cat_data["total"]
            if spent > limit:
                limit_warnings.append(f"⚠️ Limit Exceeded: You've spent ₹{spent} on {cat_name}, which is ₹{spent-limit} over your ₹{limit} limit!")
            elif spent > limit * 0.8:
                limit_warnings.append(f"⚠️ Budget Alert: You've spent ₹{spent} on {cat_name}, which is 80%+ of your ₹{limit} limit.")

    # Try using Gemini if API key is present
    api_key = os.environ.get("GEMINI_API_KEY")
    if HAS_GENAI and api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Enhanced Prompt with Memory
            memory = fetch_ai_memory()
            user_instructions = "; ".join(memory.get('instruction', [])) or "None"
            user_goals = "; ".join(memory.get('goal', [])) or "None"
            
            prompt = f"""
            You are 'Finance-AI', a permanent financial co-pilot.
            Month: {month}
            Stats: Income: ₹{income}, Expense: ₹{expense}, Balance: ₹{balance}
            Spending: {', '.join([f"{c['category']}: ₹{c['total']}" for c in categories])}
            Limit Alerts: {'; '.join(limit_warnings) if limit_warnings else 'None'}
            
            Persistent Context:
            - User Goals: {user_goals}
            - Style Preferences: {user_instructions}
            
            Instructions:
            1. Analyze deviations from typical patterns.
            2. If limits are hit, suggest specific budget cuts based on high-spend categories.
            3. Reference the user's specific goals in your advice.
            4. Keep the tone encouraging but firm on financial health.
            """
            
            response = model.generate_content(prompt)
            return {"insight": response.text.strip(), "source": "AI (Gemini)"}
        except Exception as e:
            print(f"Gemini API error: {e}")
            pass

    # Rule-based fallback "AI"
    insight = ""
    if expense == 0 and income == 0:
        insight = "No data for this month yet. Start tracking your transactions!"
    elif expense > income * 0.9:
        insight = f"⚠️ Warning: Your total expenses (₹{expense}) are dangerously close to or exceed your income (₹{income})."
    elif expense > income * 0.7:
        insight = f"You are spending a significant portion of your income. Balance is ₹{balance}."
    else:
        insight = f"Great job! You have saved ₹{balance} this month. Your spending is well under control."
    
    if limit_warnings:
        insight += "\n\n" + "\n".join(limit_warnings)
        
    return {"insight": insight, "source": "Smart Assistant"}


def handle_chat(message):
    try:
        message_lower = message.lower().strip()
        
        # Handle "Keep in mind" / "Remember this" (Training)
        train_match = re.search(r'(?:remember|keep\s+in\s+mind)\s+that\s+(.+)', message_lower)
        if train_match:
            instruction = train_match.group(1).strip()
            store_ai_memory('instruction', instruction)
            return f"🧠 **Instruction Learned!** I've updated my internal guidelines: *\"{instruction}\"*."

        # Handle Goal setting
        goal_match = re.search(r'(?:set\s+)?goal\s+(?:to\s+)?(.+)', message_lower)
        if goal_match:
            goal = goal_match.group(1).strip()
            store_ai_memory('goal', goal)
            return f"🎯 **Goal Saved!** I will focus on helping you achieve: *\"{goal}\"*."

        # Handle Set Limit (Restored)
        limit_match = re.search(r'(?:set\s+)?limit\s+(?:for\s+)?([\w\s]+?)\s+(?:to\s+)?(\d+(?:\.\d+)?)', message_lower)
        if limit_match:
            category = limit_match.group(1).strip().capitalize()
            amount = float(limit_match.group(2))
            set_limit(category, amount)
            return f"✅ **Limit Set!** I'll now monitor **{category}** expenses and warn you if you cross ₹{amount}."

        # 2. Use Gemini for general queries with FULL context (ONLY if available)
        api_key = os.environ.get("GEMINI_API_KEY")
        if HAS_GENAI and api_key:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                summary = fetch_summary()
                limits = fetch_limits()
                recent_tx = fetch_all_transactions(limit=15)
                tx_str = "\n".join([f"- {t['date']}: {t['category']} ({t['type']}) ₹{t['amount']} - {t['note']}" for t in recent_tx])
                
                # Fetch memory
                memory = fetch_ai_memory()
                user_instructions = "; ".join(memory.get('instruction', [])) or "None"
                user_goals = "; ".join(memory.get('goal', [])) or "None"

                prompt = f"""
                You are 'Finance-AI', a personal financial co-pilot with deep memory.
                
                Training & Preferences:
                - User Goals: {user_goals}
                - Behavioral Instructions: {user_instructions}
                
                Current Dashboard Context:
                - Balance: ₹{summary['balance']}
                - Monthly Income: ₹{summary['income']}
                - Monthly Expense: ₹{summary['expense']}
                - Category Budgets/Limits: {limits}
                - 15 Most Recent Transactions:
                {tx_str}
                
                Question: "{message}"
                
                Expert Persona Instructions:
                1. Always acknowledge user training/goals if relevant.
                2. If the user is nearing a limit or goal, mention it proactively.
                3. Use data-driven insights (e.g., "You spend X% of your income on Y").
                4. Be encouraging but precise.
                """
                response = model.generate_content(prompt)
                if response.candidates:
                    return response.text.strip()
                else:
                    return "I'm sorry, I cannot answer that specifically, but I can see you've spent ₹" + str(summary['expense']) + " this month."
            except Exception as e:
                print(f"Chat AI/Gemini error: {e}")
                # Fall through to step 3

        # 3. Rule-based fallbacks for when AI is offline or failed
        if any(w in message_lower for w in ["analyze", "summary", "report", "stats"]):
            return get_ai_insights()["insight"]
            
        if "limit" in message_lower or "budget" in message_lower:
            try:
                limits = fetch_limits()
                if not limits: return "You haven't set any limits yet. Set one by saying 'limit Food 5000'."
                reply = "Your monthly budgets:\n"
                for cat, val in limits.items():
                    reply += f"- {cat}: ₹{val}\n"
                return reply
            except:
                return "I couldn't fetch your limits right now."

        if any(w in message_lower for w in ["spent", "spending", "expense"]):
            try:
                summary = fetch_summary()
                reply = f"You've spent a total of ₹{summary['expense']} this month."
                if summary['categories']:
                    top = summary['categories'][0]
                    reply += f" Your biggest category is {top['category']} (₹{top['total']})."
                return reply
            except:
                pass

        if any(w in message_lower for w in ["balance", "income", "how much"]):
            try:
                summary = fetch_summary()
                return f"Your current balance is ₹{summary['balance']}. Total income: ₹{summary['income']}."
            except:
                pass

        if any(w in message_lower for w in ["save", "tip", "help", "advice"]):
            return "💡 **Tip**: Try the 50/30/20 rule! 50% for needs, 30% for wants, and 20% for savings. I can also help you set limits by saying 'limit [Category] [Amount]'."

        try:
            exp = fetch_summary()['expense']
            return f"I'm your Finance AI. You've spent ₹{exp} this month. I can analyze data, set budgets, or give financial tips. What's on your mind?"
        except:
            return "I am your Finance AI Co-pilot. I can help you track expenses and set limits. Try saying 'analyze my spending' or 'set limit Food 5000'."

    except Exception as e:
        print(f"Global handle_chat error: {e}")
        return "I'm having a bit of trouble processing that message. Please try again or ask for a summary!"

import os
import re
from datetime import datetime
from .models import (
    fetch_summary, set_limit, fetch_limits, 
    check_category_limit_exceeded, fetch_all_transactions,
    fetch_ai_memory, store_ai_memory, get_detailed_analytics,
    get_expense_warnings
)

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

def get_ai_insights(month=None):
    if not month:
        month = datetime.now().strftime("%Y-%m")
    
    # Get comprehensive analytics
    try:
        analytics = get_detailed_analytics(month)
    except:
        analytics = {"summary": fetch_summary(month)}
    
    summary = analytics.get("summary", {})
    income = summary.get("income", 0)
    expense = summary.get("expense", 0)
    balance = summary.get("balance", 0)
    categories = summary.get("categories", [])
    
    # Get warnings
    try:
        warnings = get_expense_warnings()
    except:
        warnings = []
    
    # Spending velocity info
    velocity = analytics.get("spending_velocity", {})
    daily_avg = velocity.get("daily_average", 0)
    days_elapsed = velocity.get("days_elapsed", 0)
    projected = velocity.get("projected_expense", 0)
    
    # Build warning list
    limit_warnings = [w["message"] for w in warnings if "message" in w]
    
    # Try using Gemini if API key is present
    api_key = os.environ.get("GEMINI_API_KEY")
    if HAS_GENAI and api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Enhanced Prompt with Full Analytics Context
            memory = fetch_ai_memory()
            user_instructions = "; ".join(memory.get('instruction', [])) or "None"
            user_goals = "; ".join(memory.get('goal', [])) or "None"
            
            # Format category spending
            cat_breakdown = "\n".join([f"  - {c['category']}: ₹{c['total']:.2f}" for c in categories[:10]])
            
            prompt = f"""
            You are 'Finance-AI', a permanent financial co-pilot providing detailed analytics.
            Month: {month}
            
            FINANCIAL SUMMARY:
            - Income: ₹{income:.2f}
            - Expenses: ₹{expense:.2f}
            - Balance: ₹{balance:.2f}
            - Daily Average Spending: ₹{daily_avg:.2f}
            - Days Elapsed: {days_elapsed}
            - Projected Month-End Expense: ₹{projected:.2f}
            
            TOP SPENDING CATEGORIES:
            {cat_breakdown}
            
            EXPENSE WARNINGS & ALERTS:
            {chr(10).join(limit_warnings) if limit_warnings else 'No active warnings'}
            
            PERSISTENT CONTEXT:
            - User Goals: {user_goals}
            - Behavioral Style: {user_instructions}
            
            PROVIDE ANALYSIS INCLUDING:
            1. **Current Status**: Summarize financial health clearly
            2. **Spending Pattern**: Analyze daily spending velocity and trends
            3. **Category Analysis**: Identify top spending areas and opportunities to save
            4. **Limit Status**: Detail any limit violations or warnings (🔴 EXCEEDED, 🟡 WARNING)
            5. **Projections**: Will expenses exceed income? Projected surplus/deficit?
            6. **Recommendations**: 3-5 specific, actionable suggestions for budget optimization
            7. **Action Items**: What should user do RIGHT NOW if any limits are exceeded?
            
            Keep response concise but comprehensive. Use emojis for clarity. Bold key numbers.
            """
            
            response = model.generate_content(prompt)
            return {"insight": response.text.strip(), "source": "AI (Gemini)"}
        except Exception as e:
            print(f"Gemini API error: {e}")
            pass
    
    # Enhanced rule-based fallback "AI" with detailed analytics
    insight = ""
    
    # Header
    if balance < 0:
        insight = f"🔴 **CRITICAL ALERT**: Your balance is **NEGATIVE (₹{abs(balance):.2f} deficit)**!\n\n"
    elif balance < income * 0.1:
        insight = f"🟡 **WARNING**: Low balance alert! Balance is only **₹{balance:.2f}**.\n\n"
    else:
        insight = f"✅ **Financial Status**: You have a balance of **₹{balance:.2f}**.\n\n"
    
    # Spending analysis
    if days_elapsed > 0:
        insight += f"📊 **Spending Analysis**:\n"
        insight += f"  • Daily Average: ₹{daily_avg:.2f}/day\n"
        insight += f"  • Days Remaining: {30 - days_elapsed} days\n"
        insight += f"  • Projected Month-End: ₹{projected:.2f}\n"
        
        if projected > income:
            overspend = projected - income
            insight += f"  • ⚠️ **PROJECTED OVERSPEND**: ₹{overspend:.2f}\n\n"
        else:
            saving = income - projected
            insight += f"  • ✅ **Projected Savings**: ₹{saving:.2f}\n\n"
    
    # Expense breakdown
    if categories:
        insight += f"🏷️ **Top Spending Categories**:\n"
        for i, c in enumerate(categories[:5], 1):
            pct = (c['total'] / expense * 100) if expense > 0 else 0
            insight += f"  {i}. {c['category']}: **₹{c['total']:.2f}** ({pct:.1f}%)\n"
        insight += "\n"
    
    # Alerts and warnings
    if limit_warnings:
        insight += "⚠️ **ACTIVE ALERTS**:\n"
        for warning in limit_warnings[:3]:  # Show top 3 warnings
            insight += f"  • {warning}\n"
        insight += "\n"
    
    # Recommendations
    if expense > income * 0.9:
        insight += "💡 **URGENT**: Your spending is dangerously close to your income. Reduce expenses immediately!\n"
    elif expense > income * 0.75:
        insight += "💡 **Recommendation**: Consider reducing discretionary spending in top categories.\n"
    else:
        insight += "💡 **Status**: Your spending is well-controlled. Continue monitoring!\n"
    
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
        if any(w in message_lower for w in ["analyze", "summary", "report", "stats", "analytics"]):
            insights = get_ai_insights()
            warnings = get_expense_warnings()
            
            response = insights["insight"] + "\n\n"
            
            if warnings:
                response += "🚨 **ACTIVE WARNINGS**:\n"
                for w in warnings[:5]:
                    if "message" in w:
                        response += f"  • {w['message']}\n"
            
            return response
            
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

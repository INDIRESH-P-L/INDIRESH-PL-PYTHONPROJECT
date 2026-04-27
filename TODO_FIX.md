# Fix Plan: Cannot Add / Calculate Expenses

## Critical Blocking Issues
- [x] 1. Fix CSRF blocking API writes (`app/__init__.py`) — exempted `/api/*` blueprint
- [x] 2. Sync VALID_CATEGORIES with frontend (`app/routes.py`) — added all frontend categories
- [x] 3. Remove balance check trap for expenses (`app/routes.py`) — expenses now allowed even with zero income
- [x] 4. Fix silent API failures in frontend (`app/static/js/app.js`) — improved error handling, 401 redirect, network error toasts
- [x] 5. Fix AI agent balance check & categories (`app/ai_agent.py`) — removed balance trap

## Testing
- [ ] 6. Run app and verify add/calculate works


# Development guidance

Use Python 3.11+, Streamlit, SQLite, and pytest. Keep modules small and readable.
Use the existing checkout; do not create worktrees unless requested.
Run `python -m pytest` after behavioral changes.
Keep all fictional opportunities explicitly labeled DEMO, including in the UI.
Tavily discovery is authorized only through explicit user actions. Keep searches basic, cached, and limited.
Do not implement email delivery, user accounts, or scheduling without a new task.
Keep discovered records separate from demo fixtures. Never infer verified facts from search snippets.
Mock Tavily in tests; tests must not require credentials or make live API calls.
Never log API exception payloads or credentials.
Never commit API keys, .env files, local databases, or user profiles.
Keep README setup instructions and Codex assistance disclosure accurate.

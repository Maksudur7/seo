import json
from config import HISTORY_FILE

def load_history():
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(history_item):
    history = load_history()
    # Check duplicate ID
    if any(item.get("id") == history_item.get("id") for item in history):
        return
    history.insert(0, history_item)
    history = history[:200]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

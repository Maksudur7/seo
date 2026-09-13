import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

CONFIG_FILE = DATA_DIR / "config.json"
SITE_INDEX_FILE = DATA_DIR / "site_index.json"
HISTORY_FILE = DATA_DIR / "history.json"

DEFAULT_CONFIG = {
    "gemini_api_key": "",
    "target_website_url": "",
    "keywords": ["convert pdf", "pdf to word", "file converter", "convert image", "pdf editor", "compress pdf"],
    "google_search_api_key": "",
    "google_search_cx": "",
    "telegram": {
        "bot_token": "",
        "chat_id": ""
    },
    "threads": {
        "access_token": "",
        "user_id": ""
    },
    "automation_active": False,
    "scan_interval_minutes": 15
}

def load_config():
    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                if k not in config:
                    config[k] = v
            return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return DEFAULT_CONFIG

def save_config(config_data):
    current = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                current = json.load(f)
        except Exception:
            pass

    for k, v in config_data.items():
        if isinstance(v, dict) and k in current and isinstance(current[k], dict):
            current[k].update(v)
        else:
            current[k] = v

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=4, ensure_ascii=False)

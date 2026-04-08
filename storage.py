import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class Storage:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self._data = self._load()

    def _load(self) -> Dict:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load storage: {e}")
        return {}

    def _save(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def _ensure_chat(self, chat_id: str):
        if chat_id not in self._data:
            self._data[chat_id] = {
                "urls": [],
                "seen": {},
                "alert_count": 0
            }

    def add_url(self, chat_id: str, url: str) -> bool:
        self._ensure_chat(chat_id)
        # Check if already exists
        for entry in self._data[chat_id]["urls"]:
            if entry["url"] == url:
                return False
        self._data[chat_id]["urls"].append({
            "url": url,
            "added": datetime.utcnow().isoformat(),
            "last_checked": None
        })
        self._save()
        return True

    def remove_url(self, chat_id: str, url: str) -> bool:
        self._ensure_chat(chat_id)
        before = len(self._data[chat_id]["urls"])
        self._data[chat_id]["urls"] = [
            e for e in self._data[chat_id]["urls"] if e["url"] != url
        ]
        changed = len(self._data[chat_id]["urls"]) < before
        if changed:
            # Clean up seen posts for this URL
            self._data[chat_id]["seen"].pop(url, None)
            self._save()
        return changed

    def get_urls(self, chat_id: str) -> List[Dict]:
        self._ensure_chat(chat_id)
        return self._data[chat_id]["urls"]

    def get_all_chats(self) -> List[str]:
        return list(self._data.keys())

    def is_seen(self, chat_id: str, url: str, post_id: str) -> bool:
        self._ensure_chat(chat_id)
        seen = self._data[chat_id]["seen"]
        return url in seen and post_id in seen[url]

    def mark_seen(self, chat_id: str, url: str, post_id: str):
        self._ensure_chat(chat_id)
        if url not in self._data[chat_id]["seen"]:
            self._data[chat_id]["seen"][url] = []
        if post_id not in self._data[chat_id]["seen"][url]:
            self._data[chat_id]["seen"][url].append(post_id)
            # Keep only last 500 seen per URL
            self._data[chat_id]["seen"][url] = self._data[chat_id]["seen"][url][-500:]
        self._save()

    def update_last_checked(self, chat_id: str, url: str):
        self._ensure_chat(chat_id)
        for entry in self._data[chat_id]["urls"]:
            if entry["url"] == url:
                entry["last_checked"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                break
        self._save()

    def increment_alerts(self, chat_id: str):
        self._ensure_chat(chat_id)
        self._data[chat_id]["alert_count"] = self._data[chat_id].get("alert_count", 0) + 1
        self._save()

    def get_alert_count(self, chat_id: str) -> int:
        self._ensure_chat(chat_id)
        return self._data[chat_id].get("alert_count", 0)

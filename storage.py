import os
import logging
from datetime import datetime
from typing import List, Dict, Optional
from pymongo import MongoClient

logger = logging.getLogger(__name__)

class Storage:
    def __init__(self):
        uri = os.getenv("MONGODB_URI", "mongodb+srv://n8168397_db_user:0YLcfeY1OCj5H1gT@cluster0babynametracker.oomvguu.mongodb.net/?appName=Cluster0Babynametracker")
        # Ensure we don't connect immediately and hang infinitely if the dummy URI is used
        if "<username>" in uri:
            self.client = None
            logger.warning("MONGODB_URI contains placeholder! Ensure you set up MongoDB Atlas.")
        else:
            try:
                self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
                # Test connection
                self.client.admin.command('ping')
                logger.info("✅ Connected to MongoDB Atlas")
            except Exception as e:
                self.client = None
                logger.error(f"❌ Failed to connect to MongoDB: {e}")

    @property
    def chats(self):
        if not self.client:
            return None
        return self.client.baby_tracker.chats

    def add_url(self, chat_id: str, url: str, username: str = None, first_name: str = None) -> bool:
        if not self.chats is not None:
            logger.warning("Storage not fully configured (No MongoDB Client).")
            return False

        chat = self.chats.find_one({"_id": chat_id})
        if chat:
            for entry in chat.get("urls", []):
                if entry["url"] == url:
                    return False
        
        update_doc = {
            "$push": {
                "urls": {
                    "url": url, 
                    "added": datetime.utcnow().isoformat(), 
                    "last_checked": None
                }
            }
        }
        
        # Adding metadata on the chat user for easy identification
        set_doc = {}
        if username:
            set_doc["username"] = username
        if first_name:
            set_doc["first_name"] = first_name
        
        if set_doc:
            update_doc["$set"] = set_doc
            
        self.chats.update_one(
            {"_id": chat_id},
            update_doc,
            upsert=True
        )
        return True

    def remove_url(self, chat_id: str, url: str) -> bool:
        if not self.chats is not None: return False
        
        result = self.chats.update_one(
            {"_id": chat_id},
            {"$pull": {"urls": {"url": url}}}
        )
        if result.modified_count > 0:
            # Also clean up seen posts using MongoDB hash of the url as key is safer
            url_key = str(hash(url))
            self.chats.update_one(
                {"_id": chat_id},
                {"$unset": {f"seen.{url_key}": ""}}
            )
            return True
        return False

    def get_urls(self, chat_id: str) -> List[Dict]:
        if not self.chats is not None: return []
        chat = self.chats.find_one({"_id": chat_id})
        if chat:
            return chat.get("urls", [])
        return []

    def get_all_chats(self) -> List[str]:
        if not self.chats is not None: return []
        return [chat["_id"] for chat in self.chats.find({}, {"_id": 1})]

    def is_seen(self, chat_id: str, url: str, post_id: str) -> bool:
        if not self.chats is not None: return False
        
        chat = self.chats.find_one({"_id": chat_id})
        if not chat: return False
        
        url_key = str(hash(url))
        seen_list = chat.get("seen", {}).get(url_key, [])
        return post_id in seen_list

    def mark_seen(self, chat_id: str, url: str, post_id: str):
        if not self.chats is not None: return
        
        url_key = str(hash(url))
        # Add to array, keep last 500
        self.chats.update_one(
            {"_id": chat_id},
            {"$push": {
                f"seen.{url_key}": {
                    "$each": [post_id],
                    "$slice": -500
                }
            }},
            upsert=True
        )

    def update_last_checked(self, chat_id: str, url: str):
        if not self.chats is not None: return
        
        self.chats.update_one(
            {"_id": chat_id, "urls.url": url},
            {"$set": {"urls.$.last_checked": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}}
        )

    def increment_alerts(self, chat_id: str):
        if not self.chats is not None: return
        
        self.chats.update_one(
            {"_id": chat_id},
            {"$inc": {"alert_count": 1}},
            upsert=True
        )

    def get_alert_count(self, chat_id: str) -> int:
        if not self.chats is not None: return 0
        chat = self.chats.find_one({"_id": chat_id})
        if chat:
            return chat.get("alert_count", 0)
        return 0

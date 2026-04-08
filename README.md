# 👶 Baby Name Tracker Telegram Bot

A Telegram bot that monitors Facebook, X (Twitter), and Instagram profiles/posts for baby name announcements and birth mentions — perfect for **memecoin narrative hunters** tracking influencers who might name their baby after a token.

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
cd baby-tracker-bot
pip install -r requirements.txt
```

### 2. Create Your Telegram Bot

1. Open Telegram → search **@BotFather**
2. Send `/newbot` → follow prompts
3. Copy the **bot token** you receive

### 3. Configure

```bash
cp .env.example .env
# Edit .env and paste your token:
# TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
```

### 4. Run

```bash
python bot.py
```

---

## 📱 Bot Commands

| Command | Description |
|--------|-------------|
| `/add <url>` | Start tracking a profile or post URL |
| `/list` | Show all tracked URLs |
| `/remove <url>` | Stop tracking a URL |
| `/check` | Force-check all URLs immediately |
| `/status` | Show bot stats |

### Example

```
/add https://www.facebook.com/people/ขาหมู-แอนด์เดอะแก๊ง/100069015466568/
/add https://www.instagram.com/username/
/add https://x.com/username
```

---

## 🔔 Alert Format

When a baby mention is detected, you receive:

```
🚨 BABY MENTION DETECTED!

🔵 Platform: Facebook
📅 Time: 2024-03-15 10:23 UTC
🔗 View Post

🏷️ Possible Baby Names:
  • Luna
  • Solana

🔍 Keywords: ลูก, เกิด, ชื่อ

📝 Translated Post:
"Just welcomed our baby girl Luna into the world..."

🎯 Confidence: 85%
```

---

## ⚙️ How It Works

```
Every N minutes:
  For each tracked URL:
    1. Scrape latest posts
    2. Translate to English (Thai/JP/KR/ZH supported)
    3. Detect baby keywords + NLP patterns
    4. Extract possible baby names
    5. Alert if new baby content found
```

### Supported Languages
- 🇬🇧 English
- 🇹🇭 Thai (ภาษาไทย)
- 🇯🇵 Japanese (日本語)
- 🇰🇷 Korean (한국어)
- 🇨🇳 Chinese (中文)

---

## 🛠️ Platform Notes

### Facebook
Uses `facebook-scraper` library. Works best with **public pages**.
- Profiles: `/people/Name/ID/` ✅
- Pages: `/pagename/` ✅
- Private profiles: ❌

### Instagram
Uses `instaloader`. Works with **public accounts**.
- Public profiles ✅
- Private accounts ❌

### X / Twitter
Uses `snscrape` or public **Nitter** instances.
- Public accounts ✅
- Rate-limited accounts: use nitter fallback ✅

---

## 🔧 Optional Enhancements

### Better Name Extraction (spaCy NER)
```bash
pip install spacy
python -m spacy download en_core_web_sm
```

### Twitter/X via snscrape
```bash
pip install git+https://github.com/JustAnotherArchivist/snscrape.git
```

---

## 🐋 Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
```

```bash
docker build -t baby-tracker .
docker run -d --env-file .env baby-tracker
```

---

## 📁 Project Structure

```
baby-tracker-bot/
├── bot.py          # Main Telegram bot + command handlers
├── scraper.py      # Facebook / Instagram / X scrapers
├── detector.py     # Baby keyword detection + translation + name extraction
├── storage.py      # JSON-based persistent storage
├── requirements.txt
├── .env.example
└── data/
    └── tracked.json  # Auto-created, stores URLs + seen posts
```

---

## ⚠️ Disclaimer

This bot scrapes public social media data. Use responsibly and in accordance with each platform's Terms of Service.

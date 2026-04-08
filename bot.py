import os
import json
import asyncio
import logging
import hashlib
from datetime import datetime
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from scraper import SocialMediaScraper
from detector import BabyDetector
from storage import Storage

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8778673482:AAGNWVgveSJ4rbDXR5AErRGMTBAeIbO0CKk")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))  # 5 minutes default

storage = Storage()
scraper = SocialMediaScraper()
detector = BabyDetector()


# ─── COMMANDS ───────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "👶 *Baby Name Tracker Bot*\n\n"
        "Track Facebook, X (Twitter) & Instagram posts for baby name mentions "
        "— perfect for catching new memecoin narratives!\n\n"
        "*Commands:*\n"
        "`/add <url>` — Start tracking a profile/post URL\n"
        "`/list` — Show all tracked URLs\n"
        "`/remove <url>` — Stop tracking a URL\n"
        "`/check` — Force-check all tracked URLs now\n"
        "`/status` — Bot status & stats\n\n"
        "I'll alert you the moment a baby name or birth announcement appears! 🍼"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def add_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a URL.\nUsage: `/add <url>`", parse_mode="Markdown"
        )
        return

    url = context.args[0].strip()
    chat_id = str(update.effective_chat.id)

    if not any(domain in url for domain in ["facebook.com", "twitter.com", "x.com", "instagram.com"]):
        await update.message.reply_text(
            "⚠️ Only Facebook, X (Twitter), and Instagram URLs are supported."
        )
        return

    username = update.effective_user.username
    first_name = update.effective_user.first_name

    if storage.add_url(chat_id, url, username=username, first_name=first_name):
        platform = scraper.detect_platform(url)
        await update.message.reply_text(
            f"✅ Now tracking *{platform}* URL:\n`{url}`\n\n"
            f"Checking every {CHECK_INTERVAL // 60} minute(s). I'll alert you on any baby name mention! 👶",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("⚠️ This URL is already being tracked.")


async def list_urls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    urls = storage.get_urls(chat_id)

    if not urls:
        await update.message.reply_text(
            "📭 No URLs tracked yet.\nUse `/add <url>` to start.", parse_mode="Markdown"
        )
        return

    lines = ["📋 *Tracked URLs:*\n"]
    for i, entry in enumerate(urls, 1):
        platform = scraper.detect_platform(entry["url"])
        emoji = {"Facebook": "🔵", "Instagram": "📸", "X/Twitter": "🐦"}.get(platform, "🌐")
        lines.append(f"{i}. {emoji} `{entry['url'][:60]}...`")
        if entry.get("last_checked"):
            lines.append(f"   _Last checked: {entry['last_checked']}_")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def remove_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: `/remove <url>`", parse_mode="Markdown"
        )
        return

    url = context.args[0].strip()
    chat_id = str(update.effective_chat.id)

    if storage.remove_url(chat_id, url):
        await update.message.reply_text(f"🗑️ Removed: `{url}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ URL not found in your tracking list.")


async def check_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    urls = storage.get_urls(chat_id)

    if not urls:
        await update.message.reply_text("No URLs tracked. Use `/add <url>` first.", parse_mode="Markdown")
        return

    msg = await update.message.reply_text(f"🔍 Checking {len(urls)} URL(s)...")
    found = await run_checks(context.application, chat_id=chat_id)
    await msg.edit_text(f"✅ Check complete. Found {found} new baby mention(s).")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    urls = storage.get_urls(chat_id)
    total_alerts = storage.get_alert_count(chat_id)

    await update.message.reply_text(
        f"🤖 *Bot Status*\n\n"
        f"📡 Tracked URLs: `{len(urls)}`\n"
        f"🔔 Total alerts sent: `{total_alerts}`\n"
        f"⏱ Check interval: every `{CHECK_INTERVAL // 60}` minute(s)\n"
        f"🕐 Server time: `{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}`",
        parse_mode="Markdown"
    )


# ─── BACKGROUND CHECKER ──────────────────────────────────────────────────────

async def run_checks(app: Application, chat_id: Optional[str] = None) -> int:
    """Check all tracked URLs (or just one chat's URLs). Returns count of alerts sent."""
    all_chats = storage.get_all_chats() if chat_id is None else [chat_id]
    alerts_sent = 0

    for cid in all_chats:
        urls = storage.get_urls(cid)
        for entry in urls:
            url = entry["url"]
            try:
                posts = await scraper.fetch_posts(url)
                for post in posts:
                    post_id = hashlib.md5(post["text"].encode()).hexdigest()
                    if storage.is_seen(cid, url, post_id):
                        continue

                    result = detector.analyze(post["text"])
                    if result["is_baby_related"]:
                        storage.mark_seen(cid, url, post_id)
                        storage.increment_alerts(cid)
                        await send_alert(app, cid, url, post, result)
                        alerts_sent += 1

                storage.update_last_checked(cid, url)

            except Exception as e:
                logger.error(f"Error checking {url}: {e}")

    return alerts_sent


async def send_alert(app, chat_id, url, post, result):
    platform = scraper.detect_platform(url)
    emoji = {"Facebook": "🔵", "Instagram": "📸", "X/Twitter": "🐦"}.get(platform, "🌐")

    names_str = ""
    if result.get("baby_names"):
        names_str = "\n\n🏷️ *Possible Baby Names:*\n" + "\n".join(
            f"  • `{name}`" for name in result["baby_names"]
        )

    keywords_str = ""
    if result.get("keywords_found"):
        keywords_str = "\n🔍 Keywords: " + ", ".join(f"`{k}`" for k in result["keywords_found"])

    message = (
        f"🚨 *BABY MENTION DETECTED!*\n\n"
        f"{emoji} *Platform:* {platform}\n"
        f"📅 *Time:* {post.get('time', 'Unknown')}\n"
        f"🔗 [View Post]({url})\n"
        f"{names_str}"
        f"{keywords_str}\n\n"
        f"📝 *Translated Post:*\n_{result['translated_text']}_\n\n"
        f"🎯 *Confidence:* {result['confidence']}%"
    )

    keyboard = [[InlineKeyboardButton("🔗 View Original Post", url=url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await app.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="Markdown",
            reply_markup=reply_markup,
            disable_web_page_preview=False
        )
    except Exception as e:
        logger.error(f"Failed to send alert to {chat_id}: {e}")


async def periodic_check(app: Application):
    """Background task that runs checks on an interval."""
    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        logger.info("Running periodic check...")
        try:
            count = await run_checks(app)
            if count:
                logger.info(f"Sent {count} alert(s)")
        except Exception as e:
            logger.error(f"Periodic check error: {e}")


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    os.makedirs("data", exist_ok=True)

    async def post_init(application: Application):
        asyncio.create_task(periodic_check(application))

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_url))
    app.add_handler(CommandHandler("list", list_urls))
    app.add_handler(CommandHandler("remove", remove_url))
    app.add_handler(CommandHandler("check", check_now))
    app.add_handler(CommandHandler("status", status))

    from keep_alive import keep_alive
    keep_alive()

    logger.info("🤖 Baby Tracker Bot starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

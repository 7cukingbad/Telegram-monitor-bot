"""
main.py — Telegram Group Monitor Bot

Monitors messages from specific users/bots inside a private group topic.
Sends real-time Telegram notifications based on configurable rules.

Rules:
  mode = "all"    → forward every message from the target
  mode = "filter" → only notify when conditions are met (e.g. Market Cap < 1M)

Setup:
  1. Fill in config.py with your credentials and targets
  2. Run: python get_ids.py  (to find group/topic/user IDs)
  3. Run: python main.py
"""

import asyncio
import logging
import re
from datetime import datetime

from telethon import TelegramClient, events
from telethon.tl.types import (
    MessageMediaPhoto,
    MessageMediaDocument,
    MessageMediaWebPage,
)
import httpx

from config import (
    API_ID, API_HASH, PHONE,
    BOT_TOKEN, NOTIFY_CHAT_ID,
    SOURCE_GROUP, TOPIC_ID,
    TARGETS,
)

# ============================================================
#  LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# Build a lookup dict: sender_id → target config
TARGET_MAP = {t["id"]: t for t in TARGETS}


# ============================================================
#  HELPERS
# ============================================================
def parse_marketcap(text: str, keyword: str):
    """
    Extract the market cap value from a message containing 'You are first @ X'.
    Supports formats: 660.3K, 1.6M, 500K, 1,234K
    Returns float (USD) or None if not found.
    """
    if keyword not in text:
        return None
    match = re.search(r"You are first\s*@\s*([\d,.]+)\s*([KkMm]?)", text)
    if not match:
        return None
    try:
        number = float(match.group(1).replace(",", ""))
        suffix = match.group(2).upper()
        if suffix == "K":
            number *= 1_000
        elif suffix == "M":
            number *= 1_000_000
        return number
    except ValueError:
        return None


def extract_dexscreener_link(text: str):
    """Extract the first Dexscreener URL from a message."""
    match = re.search(r"https://dexscreener\.com/[^\s\)\]]+", text)
    return match.group(0) if match else None


# ============================================================
#  SEND NOTIFICATION
# ============================================================
async def send_notify(text: str, photo_bytes: bytes = None):
    """Send a text message (with optional photo) to the notification bot."""
    base_url = f"https://api.telegram.org/bot{BOT_TOKEN}"
    async with httpx.AsyncClient() as http:
        if photo_bytes:
            resp = await http.post(
                f"{base_url}/sendPhoto",
                data={"chat_id": NOTIFY_CHAT_ID, "caption": text, "parse_mode": "HTML"},
                files={"photo": ("photo.jpg", photo_bytes, "image/jpeg")},
                timeout=30,
            )
        else:
            resp = await http.post(
                f"{base_url}/sendMessage",
                json={
                    "chat_id": NOTIFY_CHAT_ID,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False,
                },
                timeout=30,
            )
        if resp.status_code != 200:
            log.error(f"Failed to send notification: {resp.text}")
        else:
            log.info("✅ Notification sent successfully")


# ============================================================
#  HANDLERS
# ============================================================
async def handle_all(event, client, target: dict):
    """Forward every message from the target to the notification bot."""
    msg = event.message
    name = target["name"]
    time_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # Detect media type
    media_label = ""
    if isinstance(msg.media, MessageMediaPhoto):
        media_label = "📷 [Photo]"
    elif isinstance(msg.media, MessageMediaDocument):
        media_label = "📎 [File/Video/GIF]"
    elif isinstance(msg.media, MessageMediaWebPage):
        media_label = "🔗 [Link Preview]"
    elif msg.media:
        media_label = "📦 [Media]"

    content = msg.text or ""
    if not content and media_label:
        content = media_label
    elif media_label:
        content = f"{media_label}\n{content}"

    notify_text = (
        f"🔔 <b>NEW CALL</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"👤 <b>{name}</b>\n"
        f"🕐 {time_str}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{content}"
    )

    # Download photo if present
    photo_bytes = None
    if isinstance(msg.media, MessageMediaPhoto):
        try:
            photo_bytes = await client.download_media(msg.media, bytes)
        except Exception as e:
            log.warning(f"Could not download photo: {e}")

    log.info(f"📨 [ALL] {name}: {content[:80]}...")
    await send_notify(notify_text, photo_bytes)


async def handle_filter(event, target: dict):
    """Notify only when the message meets the configured filter conditions."""
    msg = event.message
    text = msg.text or ""
    name = target["name"]
    f = target.get("filter", {})
    filter_type = f.get("type")

    if filter_type == "marketcap":
        keyword   = f.get("keyword", "You are first")
        max_value = f.get("max_value", 1_000_000)

        # Parse market cap from message
        mc = parse_marketcap(text, keyword)
        if mc is None:
            return

        log.info(f"💰 [{name}] Market cap detected: ${mc:,.0f}")

        # Skip if above threshold
        if mc >= max_value:
            log.info(f"❌ [{name}] MC ${mc:,.0f} >= ${max_value:,}, skipping")
            return

        # Below threshold → send alert
        dex_link  = extract_dexscreener_link(text) or "Link not found"
        time_str  = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        label     = f"{max_value/1_000_000:.0f}M" if max_value >= 1_000_000 else f"{max_value/1_000:.0f}K"

        notify_text = (
            f"🚨 <b>GEM ALERT! MC &lt; {label}</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"💰 MC     : <b>${mc:,.0f}</b>\n"
            f"🕐 {time_str}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🔗 {dex_link}"
        )

        log.info(f"🚨 [{name}] MC ${mc:,.0f} < ${max_value:,} → Sending alert!")
        await send_notify(notify_text)


# ============================================================
#  GROUP ENTITY LOADER
# ============================================================
async def get_group_entity(client, source_group):
    """
    Load dialogs first to ensure Telethon can resolve private group IDs.
    Falls back to iterating dialogs if get_entity() fails.
    """
    log.info("📋 Loading chat list...")
    await client.get_dialogs()

    # Try standard get_entity first
    try:
        return await client.get_entity(source_group)
    except Exception:
        pass

    # Fallback: search dialogs by numeric ID
    try:
        group_id_str = str(source_group)
        channel_id = (
            int(group_id_str[4:]) if group_id_str.startswith("-100")
            else abs(int(group_id_str))
        )
        async for dialog in client.iter_dialogs():
            if dialog.entity.id == channel_id:
                log.info(f"✅ Found group via dialogs: {dialog.name}")
                return dialog.entity
        raise ValueError(f"Group ID not found: {source_group}")
    except Exception as e:
        raise RuntimeError(f"Could not connect to group: {e}")


# ============================================================
#  MAIN
# ============================================================
async def main():
    client = TelegramClient("session_monitor", API_ID, API_HASH)
    await client.start(phone=PHONE)
    log.info("✅ Logged in to Telegram successfully")

    group_entity = await get_group_entity(client, SOURCE_GROUP)
    group_id = group_entity.id

    log.info(f"📡 Group  : {group_entity.title} (ID: {group_id})")
    log.info(f"📂 Topic  : {TOPIC_ID}")
    for t in TARGETS:
        mode_str = "all messages" if t["mode"] == "all" else f"filter MC < {t['filter']['max_value']:,}"
        log.info(f"🎯 {t['name']} (ID: {t['id']}) → {mode_str}")

    # Build startup notification
    target_lines = ""
    for t in TARGETS:
        if t["mode"] == "all":
            target_lines += f"🎯 {t['name']} → all messages\n"
        else:
            mv = t["filter"]["max_value"]
            label = f"{mv/1_000_000:.0f}M" if mv >= 1_000_000 else f"{mv/1_000:.0f}K"
            target_lines += f"🤖 {t['name']} → MC &lt; {label}\n"

    await send_notify(
        f"🟢 <b>Bot started!</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📡 Group : {group_entity.title}\n"
        f"📂 Topic  : ID {TOPIC_ID}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{target_lines}"
        f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    )

    # --------------------------------------------------------
    #  LISTEN FOR NEW MESSAGES
    # --------------------------------------------------------
    @client.on(events.NewMessage(chats=group_id))
    async def handler(event):
        msg = event.message

        # Filter by topic ID
        if msg.reply_to:
            msg_topic_id = msg.reply_to.reply_to_top_id or msg.reply_to.reply_to_msg_id
        else:
            msg_topic_id = 1  # General topic (no sub-topics)

        if msg_topic_id != TOPIC_ID:
            return

        # Match sender against configured targets
        target = TARGET_MAP.get(msg.sender_id)
        if not target:
            return

        if target["mode"] == "all":
            await handle_all(event, client, target)
        elif target["mode"] == "filter":
            await handle_filter(event, target)

    log.info("👂 Listening for messages... (Ctrl+C to stop)")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())

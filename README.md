# Telegram Group Monitor Bot

A Python bot that monitors messages from specific users or bots inside a **private Telegram group topic** and sends real-time notifications to your Telegram bot.

## Features

- ✅ Works with **private groups** (uses your own Telegram account via Telethon)
- ✅ Monitors a **specific topic/sub** inside a group
- ✅ **Multiple targets** — monitor as many users/bots as you want
- ✅ Two modes per target:
  - `all` — forward every message from the target
  - `filter` — notify only when conditions are met (e.g. Market Cap < 1M)
- ✅ Extracts **Dexscreener links** from CA-check bot messages
- ✅ Supports **photos** forwarding

## How It Works

```
Private Group (Topic X)
  → Target user/bot sends a message
    → Bot checks sender ID + topic ID
      → Applies mode rules (all / filter)
        → Sends notification to your Telegram bot
```

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/telegram-monitor-bot
cd telegram-monitor-bot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Get your credentials

| Credential | Where to get it |
|---|---|
| `API_ID` / `API_HASH` | https://my.telegram.org → API development tools |
| `BOT_TOKEN` | [@BotFather](https://t.me/BotFather) → `/newbot` |
| `NOTIFY_CHAT_ID` | [@userinfobot](https://t.me/userinfobot) → your personal ID |
| `SOURCE_GROUP` | Telegram Web URL: `web.telegram.org/a/#-1002721004353_18` → `-1002721004353` |
| `TOPIC_ID` | Same URL above → number after `_` (e.g. `18`) |
| Target user/bot IDs | Forward their message to [@userinfobot](https://t.me/userinfobot) |

### 4. Configure

Copy and fill in `config.py`:

```python
API_ID   = 12345678
API_HASH = "your_api_hash"
PHONE    = "+1234567890"

BOT_TOKEN      = "your_bot_token"
NOTIFY_CHAT_ID = 123456789

SOURCE_GROUP = -1002721004353
TOPIC_ID     = 18

TARGETS = [
    {
        "id": 111111111,       # User ID
        "name": "Main Caller",
        "mode": "all",         # Forward all messages
    },
    {
        "id": 222222222,       # Bot ID
        "name": "CA Check Bot",
        "mode": "filter",
        "filter": {
            "type": "marketcap",
            "keyword": "You are first",
            "max_value": 1_000_000,  # Alert when MC < 1M
        },
    },
]
```

### 5. Find IDs (optional helper)

```bash
python get_ids.py
```

This will list all topics and recent senders in your group.

### 6. Run the bot

```bash
python main.py
```

On first run, Telegram will send you an OTP — enter it in the terminal.
A `session_monitor.session` file will be created — **do not delete it**.

### 7. Run in background (recommended)

```bash
npm install -g pm2
pm2 start main.py --interpreter python
pm2 save
```

Check status:
```bash
pm2 status
pm2 logs
```

## Notification Examples

**New call (mode: all):**
```
🔔 NEW CALL
━━━━━━━━━━━━━━━━
👤 Main Caller
🕐 23/04/2026 00:32:18
━━━━━━━━━━━━━━━━
[message content]
```

**Gem alert (mode: filter, MC < 1M):**
```
🚨 GEM ALERT! MC < 1M
━━━━━━━━━━━━━━━━
💰 MC : $56,500
🕐 23/04/2026 00:32:18
━━━━━━━━━━━━━━━━
🔗 https://dexscreener.com/ethereum/0x...
```

## Adding / Removing Targets

Only edit `config.py` — never touch `main.py`.

**Add a new user:**
```python
{
    "id": 333333333,
    "name": "Another Caller",
    "mode": "all",
},
```

**Add a new bot with 500K threshold:**
```python
{
    "id": 444444444,
    "name": "Another CA Bot",
    "mode": "filter",
    "filter": {
        "type": "marketcap",
        "keyword": "You are first",
        "max_value": 500_000,
    },
},
```

After editing `config.py`, restart the bot:
```bash
pm2 restart main
```

## Important Notes

- **Never share** your `API_ID`, `API_HASH`, `BOT_TOKEN`, or `.session` file publicly
- Add `*.session` and `config.py` to `.gitignore` before pushing to GitHub
- The bot runs under **your Telegram account** — the group sees you as a normal member

## .gitignore

```
config.py
*.session
*.session-journal
__pycache__/
*.pyc
```

"""
get_ids.py — Helper script to find Group ID, Topic IDs, and User IDs

Run this BEFORE main.py to discover the IDs you need to fill in config.py.
Make sure SOURCE_GROUP in config.py is set to a valid group you are a member of.
"""

from telethon.sync import TelegramClient
from config import API_ID, API_HASH, PHONE, SOURCE_GROUP

print("=" * 55)
print("  Telegram Monitor Bot — ID Finder")
print("=" * 55)

with TelegramClient("session_helper", API_ID, API_HASH) as client:
    client.start(phone=PHONE)

    # --- Load group ---
    print(f"\n📡 Connecting to group: {SOURCE_GROUP}")
    print("📋 Loading chat list (required for private groups)...")
    client.get_dialogs()

    try:
        entity = client.get_entity(SOURCE_GROUP)
    except Exception:
        # Fallback: search dialogs
        group_id_str = str(SOURCE_GROUP)
        channel_id = (
            int(group_id_str[4:]) if group_id_str.startswith("-100")
            else abs(int(group_id_str))
        )
        entity = None
        for dialog in client.iter_dialogs():
            if dialog.entity.id == channel_id:
                entity = dialog.entity
                break
        if not entity:
            print(f"\n❌ Could not find group with ID: {SOURCE_GROUP}")
            print("   Make sure you are a member of the group and the ID is correct.")
            exit(1)

    print(f"\n✅ Group  : {entity.title}")
    print(f"   Group ID: {entity.id}")

    # --- List topics ---
    print("\n📋 Topics in this group:")
    print("-" * 45)
    try:
        from telethon.tl.functions.channels import GetForumTopicsRequest
        result = client(GetForumTopicsRequest(
            channel=entity,
            offset_date=0,
            offset_id=0,
            offset_topic=0,
            limit=100,
            q=""
        ))
        if result.topics:
            for topic in result.topics:
                print(f"  Topic ID: {topic.id:<10} | Name: {topic.title}")
        else:
            print("  No topics found (group may not use sub-topics)")
    except Exception as e:
        print(f"  ⚠️  Could not fetch topics: {e}")

    # --- Recent senders ---
    print("\n👥 Recent senders (last 20 messages):")
    print("-" * 45)
    messages = client.get_messages(entity, limit=20)
    seen = {}
    for msg in messages:
        if not msg.sender_id or msg.sender_id in seen:
            continue
        try:
            sender = client.get_entity(msg.sender_id)
            first    = getattr(sender, "first_name", "") or ""
            last     = getattr(sender, "last_name", "") or ""
            username = getattr(sender, "username", None)
            display  = f"{first} {last}".strip()
            if username:
                display += f" (@{username})"
            seen[msg.sender_id] = display
            print(f"  User ID: {msg.sender_id:<15} | {display}")
        except Exception:
            seen[msg.sender_id] = "???"

    print("\n✅ Done! Fill TOPIC_ID and target IDs into config.py, then run main.py")
    print("=" * 55)

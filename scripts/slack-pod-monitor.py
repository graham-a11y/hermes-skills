#!/usr/bin/env python3
"""
Slack Pod Monitor — scans all Slack channels the user is in for messages from
non-@stryker-digital.com participants that are past the 1-hour SLA.

Usage: SLACK_USER_TOKEN=xoxp-... python3 slack-pod-monitor.py
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone

SLACK_TOKEN = os.environ.get("SLACK_USER_TOKEN", "")
SLA_HOURS = 1.0
STALE_AFTER_SECONDS = SLA_HOURS * 3600
DOMAIN = "stryker-digital.com"


def slack_api(url, params=None):
    """Call Slack API with the user token."""
    headers = {
        "Authorization": f"Bearer {SLACK_TOKEN}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    if params:
        # Filter out None values
        clean_params = {k: v for k, v in params.items() if v is not None}
        qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in clean_params.items())
        full_url = f"{url}?{qs}"
    else:
        full_url = url

    req = urllib.request.Request(full_url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"ok": False, "error": body}


def get_all_users():
    """Get all workspace users with their email domains."""
    users = {}
    cursor = None
    while True:
        params = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        data = slack_api("https://slack.com/api/users.list", params)
        if not data.get("ok"):
            print(f"ERROR: users.list failed: {data.get('error', 'unknown')}", file=sys.stderr)
            sys.exit(1)
        for member in data.get("members", []):
            uid = member.get("id")
            profile = member.get("profile", {})
            email = profile.get("email", "")
            domain = email.split("@")[-1] if "@" in email else ""
            users[uid] = {
                "name": member.get("real_name", member.get("name", "")),
                "display_name": profile.get("display_name", ""),
                "domain": domain,
                "email": email,
            }
        cursor = data.get("response_metadata", {}).get("next_cursor", "")
        if not cursor:
            break
    return users


def get_all_channels():
    """Get all non-archived public + private channels the user is in."""
    channels = []
    cursor = None
    while True:
        params = {
            "limit": 200,
            "types": "public_channel,private_channel",
            "exclude_archived": True,
        }
        if cursor:
            params["cursor"] = cursor
        data = slack_api("https://slack.com/api/conversations.list", params)
        if not data.get("ok"):
            print(f"ERROR: conversations.list failed: {data.get('error', 'unknown')}", file=sys.stderr)
            sys.exit(1)
        channels.extend(data.get("channels", []))
        cursor = data.get("response_metadata", {}).get("next_cursor", "")
        if not cursor:
            break
    return channels


def get_recent_messages(channel_id, limit=5):
    """Get the most recent messages in a channel."""
    params = {"channel": channel_id, "limit": limit}
    data = slack_api("https://slack.com/api/conversations.history", params)
    if not data.get("ok"):
        return None
    return data.get("messages", [])


def get_thread_replies(channel_id, thread_ts):
    """Get replies in a thread to check if anyone replied."""
    params = {"channel": channel_id, "ts": thread_ts, "limit": 10}
    data = slack_api("https://slack.com/api/conversations.replies", params)
    if not data.get("ok"):
        return []
    return data.get("messages", [])


def resolve_sender(msg, users):
    """Try to find who sent a message — could be user, bot, or unknown."""
    user_id = msg.get("user", "")
    if user_id and user_id in users:
        return users[user_id]

    # Check if it's a bot message with a username
    bot_id = msg.get("bot_id", "")
    username = msg.get("username", "")
    if username:
        return {"name": username, "domain": "", "email": f"bot: {username}"}

    # App/user profile fallback
    profile = msg.get("profile", {}) if isinstance(msg.get("profile"), dict) else {}
    if profile.get("real_name"):
        return {"name": profile["real_name"], "domain": "", "email": profile.get("email", "unknown")}

    return {"name": user_id or bot_id or "unknown", "domain": "", "email": "unknown"}


# ── Debug: log what the script sees for specific channels ────────
DEBUG_CHANNELS = []  # set channels like ["302cleanit"] to debug
EXCLUDED_NAMES = ["viktor", "victor"]


def is_thanks_message(text):
    """Check if a message is just a thank-you (not needing a reply)."""
    clean = text.lower().strip()
    for ch in "!.,?🙏👍😊🙌🎉✨❤️💪👏✅😄😁😀🤗🙂":
        clean = clean.replace(ch, "")
    clean = clean.strip()
    thanks_patterns = {
        "thanks", "thank you", "thankyou", "ty", "thx", "cheers",
        "thank you!", "thanks!", "thanks all", "thanks everyone",
        "thank you all", "thank you everyone", "thx!",
        "thanks much", "thanks a lot", "thank you very much",
        "much appreciated", "appreciate it", "appreciated",
        "great thanks", "ok thanks", "ok thank you",
        "sounds good thanks", "perfect thanks", "awesome thanks",
        "got it thanks", "got it thank you",
    }
    return clean in thanks_patterns


def is_excluded_sender(sender):
    """Check if a sender should be excluded by name."""
    name = (sender.get("name", "") + " " +
            sender.get("display_name", "") + " " +
            sender.get("email", "")).lower()
    for excluded in EXCLUDED_NAMES:
        if excluded in name:
            return True
    return False


def main():
    token = os.environ.get("SLACK_USER_TOKEN")
    if not token:
        print("ERROR: SLACK_USER_TOKEN environment variable not set", file=sys.stderr)
        return 1
    if not token.startswith("xoxp-") and not token.startswith("xoxb-"):
        print(f"WARNING: token starts with '{token[:5]}...' — expected xoxp- or xoxb-", file=sys.stderr)

    print("🔍 Discovering employees @stryker-digital.com...")
    users = get_all_users()
    internal_ids = set()
    for uid, info in users.items():
        if info["domain"] == DOMAIN:
            internal_ids.add(uid)
    print(f"✓ {len(internal_ids)} employees found")

    print("🔍 Discovering channels...")
    channels = get_all_channels()
    total = len(channels)
    print(f"✓ {total} channels found")

    stale = []
    skipped_dead = 0
    skipped_archived = 0
    now = time.time()
    rate_limit_delay = 0  # no delay — user tokens have generous rate limits

    # ── Load track-from timestamp ───────────────────────────────
    # Only messages newer than this get SLA-tracked.
    # Reset by writing the current timestamp to the file.
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    TRACK_FROM_FILE = os.path.join(SCRIPT_DIR, "slack-pod-monitor.track_from")
    track_from = 0.0
    if os.path.exists(TRACK_FROM_FILE):
        try:
            with open(TRACK_FROM_FILE) as f:
                track_from = float(f.read().strip())
        except (ValueError, OSError):
            pass

    for i, ch in enumerate(channels):
        name = ch.get("name", "unknown")
        cid = ch.get("id")

        if ch.get("is_archived"):
            skipped_archived += 1
            continue

        messages = get_recent_messages(cid)
        time.sleep(rate_limit_delay)

        if not messages:
            skipped_dead += 1
            continue

        # ── Debug: dump all messages + response checks for watched channels
        debug = name in DEBUG_CHANNELS

        # Messages come newest-first. Reverse to process oldest→newest
        # so we find the oldest unanswered client message first.
        if debug:
            print(f"\n🐛 DEBUG #{name} — {len(messages)} recent messages:", file=sys.stderr)
            for mi, dm in enumerate(messages):
                dts = dm.get("ts", "?")
                duser = dm.get("user", "?")
                dname = users.get(duser, {}).get("name", duser) if duser != "?" else "?"
                dtext = (dm.get("text", "") or "")[:80].replace("\n", " ")
                dbot = "🤖" if dm.get("bot_id") or dm.get("subtype") == "bot_message" else ""
                dthread = "🧵" if dm.get("reply_count", 0) > 0 else ""
                dreact = len(dm.get("reactions", []))
                dkind = "internal" if duser in internal_ids else ("external" if duser else "?")
                print(f"  [{mi}] {dname} ({dkind}){dbot}{dthread} react={dreact}: «{dtext}»", file=sys.stderr)
        found_stale = False
        for msg in reversed(messages):
            if found_stale:
                break

            # ── Skip thread replies (handled separately below) ──
            if msg.get("thread_ts") and msg.get("thread_ts") != msg.get("ts"):
                continue

            # ── Skip bot/automation and join/leave system messages ──
            if msg.get("bot_id") or msg.get("subtype") == "bot_message":
                continue
            subtype = msg.get("subtype", "")
            if subtype in ("channel_join", "channel_leave"):
                continue

            # Resolve sender
            sender = resolve_sender(msg, users)
            user_id = msg.get("user", "")

            if not user_id:
                continue

            # Slackbot (USLACKBOT) messages are automated — never need response
            if user_id == "USLACKBOT":
                continue

            if user_id in internal_ids:
                continue

            if is_excluded_sender(sender):
                continue

            # Check message age against SLA
            ts = float(msg.get("ts", 0))
            age = now - ts

            # Skip messages older than the track-from reset point
            if ts < track_from:
                continue

            if age < STALE_AFTER_SECONDS:
                continue

            # Format the message text
            text = msg.get("text", "")
            if not text.strip():
                blocks = msg.get("blocks", [])
                if blocks:
                    for block in blocks:
                        for elem in block.get("elements", []):
                            if isinstance(elem, dict) and elem.get("type") == "text":
                                text = elem.get("text", "")
                                break
            if is_thanks_message(text):
                continue

            msg_ts = float(msg.get("ts", 0))

            # ── Check for a proper internal response ────────────
            if debug:
                sender_name = sender.get("name", "?")
                print(f"  🐛 Checking external msg from {sender_name}: «{text[:60]}» (age={age/3600:.1f}h)", file=sys.stderr)

            # 1) Check newer messages in the channel for a text reply from internal
            has_internal_response = False
            for later_msg in messages:
                later_ts = float(later_msg.get("ts", 0))
                if later_ts <= msg_ts:
                    continue  # not newer
                later_user = later_msg.get("user", "")
                if later_user and later_user in internal_ids:
                    later_text = later_msg.get("text", "")
                    # An internal user replying at all counts as handled — even if
                    # they're saying "thanks" or closing the thread.
                    has_internal_response = True
                    if debug:
                        lname = users.get(later_user, {}).get("name", later_user)
                        print(f"    ✓ channel reply from {lname} (internal): «{later_text[:50]}»", file=sys.stderr)
                    break
                elif debug and later_user:
                    lname = users.get(later_user, {}).get("name", later_user)
                    ldom = users.get(later_user, {}).get("domain", "?")
                    later_text_s = (later_msg.get("text", "") or "")[:40]
                    print(f"    ✗ later msg from {lname} (domain={ldom}) — NOT internal: «{later_text_s}»", file=sys.stderr)

            if has_internal_response:
                continue

            # 2) Check thread replies for internal response
            if msg.get("reply_count", 0) > 0:
                thread_ts = msg.get("thread_ts", msg.get("ts"))
                replies = get_thread_replies(cid, thread_ts)
                has_thread_reply = False
                for reply in replies:
                    if reply.get("ts") == msg.get("ts"):
                        continue  # skip parent
                    reply_user = reply.get("user", "")
                    if reply_user and reply_user in internal_ids:
                        has_thread_reply = True
                        break
                if debug:
                    thread_users = [users.get(r.get("user",""),{}).get("name","?") for r in replies if r.get("ts") != msg.get("ts")]
                    print(f"    🧵 thread replies ({len(replies)-1}): {thread_users} — internal_reply={has_thread_reply}", file=sys.stderr)
                if has_thread_reply:
                    continue
            elif debug:
                print(f"    🧵 no thread (reply_count=0)", file=sys.stderr)

            # 3) Check for emoji reactions from internal users —
            #    a ✅ reaction means "handled", counts as a response
            reacted = msg.get("reactions", [])
            has_internal_reaction = False
            for reaction in reacted:
                for uid in reaction.get("users", []):
                    if uid in internal_ids:
                        has_internal_reaction = True
                        break
                if has_internal_reaction:
                    break
            if debug:
                react_names = [r.get("name","?") for r in reacted]
                print(f"    😀 reactions: {react_names} — internal_reaction={has_internal_reaction}", file=sys.stderr)
            if has_internal_reaction:
                continue

            if debug:
                print(f"    🚩 FLAGGED — no internal reply, no thread reply, no internal reaction", file=sys.stderr)

            # Truncate text for display
            if len(text) > 120:
                text = text[:117] + "..."

            age_hrs = round(age / 3600, 1)

            stale.append({
                "channel": f"#{name}",
                "age_hrs": age_hrs,
                "sender_name": sender.get("name", user_id or "unknown"),
                "text": text,
            })
            found_stale = True

    # Sort by age (oldest first)
    stale.sort(key=lambda x: x["age_hrs"], reverse=True)

    # ── Report ──────────────────────────────────────────────────
    now_dt = datetime.now(timezone.utc)
    sla_str = f"{SLA_HOURS:.1f}h"

    print(f"\n🔔 Slack Pod Monitor — {len(stale)} stale channel(s)")
    print(f"_SLA: {sla_str} | Scanned: {total} channels | Employees: {len(internal_ids)} | Skipped archived: {skipped_archived} | Skipped dead: {skipped_dead}_")

    if stale:
        print()
        for s in stale:
            print(f"• {s['channel']}")
            print(f"  ⏰ {s['age_hrs']}h old ({s['sender_name']})")
            print(f"  💬 {s['text']}")
    else:
        print("\n✅ All channels within SLA — nothing to report.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

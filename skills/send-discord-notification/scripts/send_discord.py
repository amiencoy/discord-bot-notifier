#!/usr/bin/env python3
"""Send one notification as a Discord bot; standard library only."""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--message")
    source.add_argument("--message-stdin", action="store_true")
    parser.add_argument("--channel-id", default=os.environ.get("DISCORD_CHANNEL_ID"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    content = sys.stdin.read() if args.message_stdin else args.message
    if not content or not content.strip():
        parser.error("message must not be empty")
    if len(content) > 2000:
        parser.error("message exceeds Discord's 2000-character content limit")
    if not args.dry_run and (not args.channel_id or not re.fullmatch(r"[0-9]{15,22}", args.channel_id)):
        parser.error("set DISCORD_CHANNEL_ID or pass a numeric --channel-id")
    payload = {"content": content, "allowed_mentions": {"parse": []}}
    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False))
        return 0
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        parser.error("set DISCORD_BOT_TOKEN in the execution environment")
    url = f"https://discord.com/api/v10/channels/{args.channel_id}/messages"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bot {token}", "Content-Type": "application/json", "User-Agent": "DiscordBot (private-notifier, 0.1.0)"},
        method="POST",
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                result = json.load(response)
                if not result.get("id"):
                    print("Discord response contained no message ID; delivery unverified", file=sys.stderr)
                    return 1
                print(json.dumps({"status": "sent", "channel_id": args.channel_id, "message_id": result["id"]}))
                return 0
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < 2:
                try:
                    data = json.loads(exc.read().decode("utf-8"))
                    delay = float(data.get("retry_after", exc.headers.get("Retry-After", "1")))
                except (ValueError, TypeError, json.JSONDecodeError):
                    delay = 1.0
                time.sleep(min(max(delay, 0.1), 30.0))
                continue
            print(f"Discord rejected message (HTTP {exc.code}); delivery not confirmed", file=sys.stderr)
            return 1
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"Network error ({type(exc).__name__}); delivery unverified, check channel before retrying", file=sys.stderr)
            return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

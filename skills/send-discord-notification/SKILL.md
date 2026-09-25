---
name: send-discord-notification
description: Draft and send a notification through a configured Discord bot into a Discord channel. Use when the user requests a Discord alert, status update, delivery, or a notification about a task result; also use to prepare and troubleshoot bot notification setup.
---

# Discord bot notification

1. Identify the event, recipient channel, and desired urgency from the request. Keep a notification concise: status/title, essential result, and a useful action or link if supplied. State uncertainty clearly. Never invent completed work or success.
2. Use the bundled `scripts/send_discord.py` with Python 3. The environment running the script needs `DISCORD_BOT_TOKEN` and `DISCORD_CHANNEL_ID`; an explicit `--channel-id` overrides the environment. Treat a bot token as a secret. Do not ask the user to paste it into chat, put it in a command line, print it, store it in a plugin file, or include it in a notification. Explain that they can set it privately in their execution environment. The bot must be installed in the server and have permission to view and send messages in that channel.
3. Prepare a preview with `python3 <skill-dir>/scripts/send_discord.py --dry-run --message '...'`. For dynamic or untrusted message text, send it on standard input with `--message-stdin`, avoiding shell interpolation. Never include raw sensitive data from task outputs without user intent. The sender suppresses mentions by default. Explicit mentions need the user's request plus a deliberate sender change; do not sneak in `@everyone`, `@here`, or role pings.
4. If the request authorizes sending, and the runtime can execute the bundled script with outbound access, call the script with `--message-stdin`. A request to notify is authorization to send that notification. If configuration, runtime execution, or destination is missing, prepare the message and give the exact missing setup step. Do not claim delivery until the sender returns a Discord message ID. On errors, report the status without leaking the token.
5. Requests for later or recurring notification require an actual scheduler/automation with a configured bot delivery path. Create one only when an available integration supports it; this skill alone runs on demand and is not a background service. Do not imply that a future trigger or continuous monitoring exists solely because a message draft was prepared.

Example, with credentials already configured in the execution environment:

```bash
printf '%s' '✅ Lophiarch v2.2.2 released — registry tag verified.' | python3 scripts/send_discord.py --message-stdin
```

The script deliberately posts to one configured channel and returns a message ID only after Discord accepts the message. For different channels, specify an explicit numeric `--channel-id` and verify the destination before sending.

# Discord Bot Notifier

A small [Agent Plugins 1.0](https://agent-plugins.org/) plugin that helps an assistant draft and send a Discord notification with **your own bot**. It includes a Python sender with no third-party dependencies.

> The repository is public; the bot token and channel ID are yours. No credential is bundled, and nothing sends automatically until you configure and run it.

## What it does

- Drafts a concise status, result, or alert for a Discord channel.
- Sends one message through Discord's bot API and reports its message ID when accepted.
- Disables all `@everyone`, role, and user mentions by default.
- Honors Discord's rate limit response with bounded retries.
- Offers a `--dry-run` preview without credentials or network access.

This is an **outbound notifier**, not a conversational Discord bot. It does not read incoming messages, monitor events, run in the background, or schedule recurring alerts. To notify on a future event, connect a trusted scheduler or automation to the sender.

## Prerequisites

- Python 3.9 or later in the environment that runs the bundled script.
- A Discord application with a bot, installed in your server.
- A text channel in that server where the bot has **View Channel** and **Send Messages** permissions.
- Outbound access to `discord.com` from the execution environment.

## Set up your bot

1. In the [Discord Developer Portal](https://discord.com/developers/applications), create an application and add a bot. Keep its token secret.
2. Invite the bot to your server with the `bot` scope and the permissions above. Do not use a personal account token.
3. Enable **Developer Mode** in Discord, right-click the destination channel, and select **Copy Channel ID**.
4. Put `DISCORD_BOT_TOKEN` and `DISCORD_CHANNEL_ID` in the secret/environment settings of the **machine or automation that will run the Python script**. Never commit a token, paste it into chat, or put it in command arguments or logs. The channel ID is an identifier, while the bot token is a secret.

The plugin cannot retrieve your token from Discord or automatically install the bot in a server. Each user provides their own configuration.

## Run it

From the repository root, first preview the payload:

```bash
python3 skills/send-discord-notification/scripts/send_discord.py \
  --dry-run --message '✅ Deployment completed'
```

Once the environment variables are configured, send a message:

```bash
printf '%s' '✅ Deployment completed' | \
  python3 skills/send-discord-notification/scripts/send_discord.py --message-stdin
```

A successful send prints JSON containing `status`, `channel_id`, and `message_id`. If the request times out, delivery is unverified; check the channel before retrying to avoid duplicates. The sender accepts a different destination with `--channel-id 123456789012345678`, after you verify that the bot has access to it. Messages are limited to 2,000 characters.

For scripted notifications, pipe the already prepared text into `--message-stdin`. Avoid constructing shell commands from untrusted message text.

## Use it as a plugin

The repository root holds `plugin.json` and the `send-discord-notification` skill. Install it in a client that supports the Agent Plugins format, or invoke the script directly from your own workflow. The skill guides an assistant to preview, send, and verify one notification when the runtime has script execution and network access. Installing the plugin alone does not provide a persistent bot process or a configured Discord connection.

## Repository layout

```text
plugin.json
skills/send-discord-notification/SKILL.md
skills/send-discord-notification/scripts/send_discord.py
```

## Security

The sender only contacts Discord's `api/v10/channels/{channel_id}/messages` endpoint. It does not print the token. Restrict who can set the bot token, rotate it if exposed, and grant the bot only the channel permissions it needs. Review notification contents before sending sensitive material.

## License

Apache-2.0. See [LICENSE](LICENSE).

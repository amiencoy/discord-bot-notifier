# Discord Bot Notifier

A provider-agnostic Discord chatbot for opt-in AI model alerts and slash-command conversations. Each server operator brings their own Discord bot, provider keys, and model IDs. The repository also includes an [Agent Plugins 1.0](https://agent-plugins.org/) skill and the original one-shot notifier script.

**Supported model families:** GPT (OpenAI), Claude, Gemini, Mistral, Grok, Llama (local OpenAI-compatible endpoint), and a general Local / OpenAI-compatible endpoint. Mistral and Grok use their OpenAI-compatible chat endpoints; Claude and Gemini use their native APIs. A model ID is an exact value from your provider, not a name this project guesses.

## Quick start

1. Create a bot in the [Discord Developer Portal](https://discord.com/developers/applications) and invite it to a server with the `bot` and `applications.commands` scopes. Grant **View Channel** and **Send Messages** in the target channel. No Message Content intent is needed for slash commands.
2. Clone the repository, create a Python 3.10+ virtual environment, and install dependencies:

   ```bash
   python3 -m venv .venv
   . .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   ```

3. Privately fill `DISCORD_BOT_TOKEN` in `.env`. For fast slash-command registration, set `DISCORD_GUILD_ID` to your test server ID. Set `DISCORD_ALERT_CHANNEL_ID` to the channel where alerts should be posted. Never commit `.env` or send keys through Discord.
4. Run `python3 -m bot.app`. Keep the process running for slash commands and alerts.
5. In the server, run `/addmodel`. Select a model family, enter its **exact model ID**, and optionally its local/compatible base URL. The bot sends an **ephemeral template** to copy into `.env`. Fill API keys on the bot host and restart the bot. `/addmodel` does not receive or store keys.
6. Run `/modelstatus`, `/turnon model:<provider>`, `/testmodel model:<provider>`, and `/ask model:<provider> prompt:<your test>`. The test calls the AI and returns its answer via Discord. Model status turns green when its required environment configuration is present; last test status shows whether a request succeeded. Green does not by itself prove connectivity.

For a locally hosted model, use an OpenAI-compatible server such as one listening at `http://127.0.0.1:11434/v1`. The server must be reachable **from the machine running the bot**. `127.0.0.1` points to that machine, not to the Discord user's device. Local keys are optional; configure `MODEL_LLAMA_API_KEY` or `MODEL_LOCAL_API_KEY` if the local server requires authentication.

## Commands

| Command | Purpose | Permission |
| --- | --- | --- |
| `/addmodel` | Choose a provider, fill a model ID, get an `.env` template privately | Manage Server |
| `/modelstatus` | Show whether each family was added, on/off, and last request status | Server member |
| `/turnon model` | Activate one configured family in this server | Manage Server |
| `/turnoff model` | Stop requests to one family in this server | Manage Server |
| `/alerts model event enabled` | Choose which alert event to send for one family | Manage Server |
| `/alertstatus model` | Show the selected alert events | Server member |
| `/testmodel model` | Test Discord → AI → Discord with an ephemeral response | Manage Server |
| `/ask model prompt` | Ask the model and post its response in the channel | Manage Server |

Alert events are `test_success`, `test_failure`, `request_failure`, and `recovered`. They are **off by default**. Set `DISCORD_ALERT_CHANNEL_ID`, then enable the events you want with `/alerts`. Alerts fire when bot commands produce those events; this release does not poll provider uptime in the background. Model switches, alert choices, and last request results are stored per server in SQLite (`DISCORD_STATE_DB`). Credentials and model IDs stay in environment settings, never in SQLite.

`/ask` is restricted to Manage Server to limit unwanted provider charges. Bot replies suppress all mentions, including mentions returned by AI. A provider error is reported without echoing the API key or the provider's response body. The bot does not let an AI autonomously call Discord tools; it handles a user's command, calls the chosen provider, and sends the response back.

## Environment variable mapping

| Family | Required `.env` values | Default API style |
| --- | --- | --- |
| GPT | `MODEL_GPT_ID`, `MODEL_GPT_API_KEY` | OpenAI chat completions |
| Claude | `MODEL_CLAUDE_ID`, `MODEL_CLAUDE_API_KEY` | Anthropic Messages |
| Gemini | `MODEL_GEMINI_ID`, `MODEL_GEMINI_API_KEY` | Gemini generateContent |
| Mistral | `MODEL_MISTRAL_ID`, `MODEL_MISTRAL_API_KEY` | OpenAI-compatible chat completions |
| Grok | `MODEL_GROK_ID`, `MODEL_GROK_API_KEY` | OpenAI-compatible chat completions |
| Llama | `MODEL_LLAMA_ID`, `MODEL_LLAMA_BASE_URL` | Local OpenAI-compatible chat completions |
| Local / OpenAI-compatible | `MODEL_LOCAL_ID`, `MODEL_LOCAL_BASE_URL` | Custom OpenAI-compatible chat completions |

You can optionally set `MODEL_<FAMILY>_BASE_URL` to override any default endpoint, and `MODEL_LLAMA_API_KEY` or `MODEL_LOCAL_API_KEY` for authenticated local hosts. Use HTTPS for remote providers. One model ID per family is supported in this release. Restart the bot after editing `.env`; `/addmodel` prepares the template but does not modify the bot host.

## Standalone notifier

The original sender remains available for a one-off Discord alert, even without the chatbot runtime:

```bash
python3 skills/send-discord-notification/scripts/send_discord.py --dry-run --message '✅ Job completed'
printf '%s' '✅ Job completed' | python3 skills/send-discord-notification/scripts/send_discord.py --message-stdin
```

It reads `DISCORD_BOT_TOKEN` and `DISCORD_CHANNEL_ID` from the process environment. It does not load `.env` itself. A successful send returns a Discord message ID; after a network timeout, verify the channel before retrying to avoid duplicates.

## Plugin and source layout

- `plugin.json` and `skills/send-discord-notification/` provide the assistant workflow and one-off sender.
- `bot/` contains slash commands, model configuration, API adapters, and SQLite state.
- `tests/` checks provider routing, templates, and persisted switches without contacting external services.

Installing the ChatGPT plugin does not start a persistent Discord process. Host and run `bot.app` yourself to receive slash commands. Nothing includes provider keys or a Discord bot token.

## Security and limits

Keep `.env` private, rotate exposed tokens, and grant the bot only the necessary server permissions. A customized base URL is operator-controlled and makes the bot send the selected prompt and optional credential to that server. Review that destination before configuring it. Provider requests have a 25-second timeout. The bot returns up to 1,800 characters in `/ask` and does not maintain conversation history. It uses an exact model ID supplied by the operator, so provider availability and charges depend on that account.

Licensed under [Apache-2.0](LICENSE).

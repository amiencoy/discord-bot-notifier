"""Discord slash-command interface. No Message Content privileged intent needed."""
import os
import logging

import discord
from discord import app_commands
from dotenv import load_dotenv

from .config import CATALOG, is_configured, template
from .providers import ProviderError, generate
from .store import EVENTS, Store

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
if not TOKEN:
    raise SystemExit("Set DISCORD_BOT_TOKEN privately in .env or the environment.")
store = Store(os.getenv("DISCORD_STATE_DB", "./data/state.sqlite3"))
choices = [app_commands.Choice(name=p.label, value=p.key) for p in CATALOG.values()]
event_choices = [app_commands.Choice(name=e.replace("_", " ").title(), value=e) for e in EVENTS]

class Notifier(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default(), allowed_mentions=discord.AllowedMentions.none())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        guild_id = os.getenv("DISCORD_GUILD_ID")
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

bot = Notifier()

def guild_id(interaction):
    if interaction.guild_id is None:
        raise ValueError("This command is only available in a server.")
    return interaction.guild_id

async def emit(guild, provider, event, message):
    if not store.alert(guild, provider, event):
        return
    channel_id = os.getenv("DISCORD_ALERT_CHANNEL_ID", "")
    if not channel_id.isdigit():
        logger.warning("Alert enabled but DISCORD_ALERT_CHANNEL_ID is missing")
        return
    try:
        channel = bot.get_channel(int(channel_id))
        if channel is None:
            channel = await bot.fetch_channel(int(channel_id))
        if getattr(channel, "guild", None) is None or channel.guild.id != guild:
            logger.warning("Alert channel is not in the command's guild")
            return
        await channel.send(message[:1900], allowed_mentions=discord.AllowedMentions.none())
    except discord.DiscordException:
        logger.exception("Failed to deliver a Discord alert")

class AddModelModal(discord.ui.Modal, title="Configure a model"):
    model_id = discord.ui.TextInput(label="Exact provider model ID", placeholder="Copy the model ID from your provider dashboard", max_length=150)
    base_url = discord.ui.TextInput(label="Base URL (local / compatible only)", required=False, placeholder="http://127.0.0.1:11434/v1", max_length=300)

    def __init__(self, provider):
        super().__init__()
        self.provider = provider

    async def on_submit(self, interaction):
        try:
            snippet = template(self.provider, str(self.model_id), str(self.base_url))
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        p = CATALOG[self.provider]
        await interaction.response.send_message(
            f"**{p.label}** — copy this template into `.env` on the bot host, replace placeholders locally, then restart the bot:\n```dotenv\n{snippet}\n```\n"
            f"Don't send API keys in Discord. Run `/modelstatus`, `/turnon {self.provider}`, then `/testmodel {self.provider}`. "
            "Finally send `/ask` to check that a Discord request reaches the AI and its answer returns here.",
            ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

class ProviderSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Choose a provider / model family", options=[discord.SelectOption(label=p.label, value=p.key) for p in CATALOG.values()])

    async def callback(self, interaction):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Manage Server permission required.", ephemeral=True)
            return
        await interaction.response.send_modal(AddModelModal(self.values[0]))

class ProviderView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(ProviderSelect())

@bot.tree.command(name="addmodel", description="Choose a provider and get a private .env template")
@app_commands.checks.has_permissions(manage_guild=True)
async def addmodel(interaction: discord.Interaction):
    guild_id(interaction)
    await interaction.response.send_message("Choose a provider. API keys belong in your bot host's `.env`, never in chat.", view=ProviderView(), ephemeral=True)

@bot.tree.command(name="modelstatus", description="See configured, active, and tested model status")
async def modelstatus(interaction: discord.Interaction):
    guild = guild_id(interaction)
    lines = []
    for key, p in CATALOG.items():
        if not is_configured(key):
            lines.append(f"⚪ **{p.label}** — model hasn't been added")
        else:
            active = "on" if store.enabled(guild, key) else "off"
            lines.append(f"🟢 **{p.label}** — added · {active} · {store.health_status(guild, key)}")
    await interaction.response.send_message("\n".join(lines), ephemeral=True)

@bot.tree.command(name="turnon", description="Enable an added model in this server")
@app_commands.choices(model=choices)
@app_commands.checks.has_permissions(manage_guild=True)
async def turnon(interaction: discord.Interaction, model: app_commands.Choice[str]):
    guild = guild_id(interaction)
    if not is_configured(model.value):
        await interaction.response.send_message("model hasn't been added — run `/addmodel`, update `.env` on the bot host, and restart.", ephemeral=True)
        return
    store.turn(guild, model.value, True)
    await interaction.response.send_message(f"🟢 {model.name} is on. Run `/testmodel` to check connectivity.", ephemeral=True)

@bot.tree.command(name="turnoff", description="Disable a model in this server")
@app_commands.choices(model=choices)
@app_commands.checks.has_permissions(manage_guild=True)
async def turnoff(interaction: discord.Interaction, model: app_commands.Choice[str]):
    store.turn(guild_id(interaction), model.value, False)
    await interaction.response.send_message(f"⚪ {model.name} is off.", ephemeral=True)

@bot.tree.command(name="alerts", description="Turn a selected model alert on or off")
@app_commands.choices(model=choices, event=event_choices)
@app_commands.checks.has_permissions(manage_guild=True)
async def alerts(interaction: discord.Interaction, model: app_commands.Choice[str], event: app_commands.Choice[str], enabled: bool):
    guild = guild_id(interaction)
    if enabled and not os.getenv("DISCORD_ALERT_CHANNEL_ID", "").isdigit():
        await interaction.response.send_message("Set DISCORD_ALERT_CHANNEL_ID on the bot host before enabling alerts.", ephemeral=True)
        return
    store.alert(guild, model.value, event.value, enabled)
    await interaction.response.send_message(f"{model.name}: {event.name} alert {'on' if enabled else 'off'}.", ephemeral=True)

@bot.tree.command(name="alertstatus", description="See enabled alert types for a model")
@app_commands.choices(model=choices)
async def alertstatus(interaction: discord.Interaction, model: app_commands.Choice[str]):
    guild = guild_id(interaction)
    items = [f"{'🟢' if store.alert(guild, model.value, event) else '⚪'} {event.replace('_', ' ')}" for event in EVENTS]
    await interaction.response.send_message(f"**{model.name} alerts**\n" + "\n".join(items), ephemeral=True)

async def request(interaction, key, prompt, is_test):
    guild = guild_id(interaction)
    if not is_configured(key) or not store.enabled(guild, key):
        await interaction.response.send_message("Model is missing or off. Check `/modelstatus`.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=is_test, thinking=True)
    try:
        answer = await generate(key, prompt)
    except (ProviderError, ValueError) as exc:
        store.outcome(guild, key, False)
        event = "test_failure" if is_test else "request_failure"
        await emit(guild, key, event, f"🔴 {CATALOG[key].label} {event.replace('_', ' ')}: {exc}")
        await interaction.followup.send(f"🔴 {CATALOG[key].label}: {exc}", ephemeral=True)
        return
    recovered = store.outcome(guild, key, True)
    if recovered:
        await emit(guild, key, "recovered", f"🟢 {CATALOG[key].label} recovered after a failed request.")
    if is_test:
        await emit(guild, key, "test_success", f"🟢 {CATALOG[key].label} passed a connection test.")
        await interaction.followup.send(f"🟢 AI responded through the bot: {answer[:1400]}", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
    else:
        await interaction.followup.send(f"**{CATALOG[key].label}**: {answer[:1800]}", allowed_mentions=discord.AllowedMentions.none())

@bot.tree.command(name="testmodel", description="Test Discord to AI to Discord round trip")
@app_commands.choices(model=choices)
@app_commands.checks.has_permissions(manage_guild=True)
async def testmodel(interaction: discord.Interaction, model: app_commands.Choice[str]):
    await request(interaction, model.value, "Reply briefly: connection OK.", True)

@bot.tree.command(name="ask", description="Ask an enabled AI model")
@app_commands.choices(model=choices)
@app_commands.checks.has_permissions(manage_guild=True)
async def ask(interaction: discord.Interaction, model: app_commands.Choice[str], prompt: str):
    if len(prompt) > 1500:
        await interaction.response.send_message("Prompt is too long (max 1500 characters).", ephemeral=True)
        return
    await request(interaction, model.value, prompt, False)

@bot.tree.error
async def on_app_command_error(interaction, error):
    message = "Manage Server permission required." if isinstance(error, app_commands.MissingPermissions) else "Command failed; check the bot logs."
    logger.error("Command failed: %s", type(error).__name__)
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)

def main():
    bot.run(TOKEN, log_handler=None)

if __name__ == "__main__":
    main()

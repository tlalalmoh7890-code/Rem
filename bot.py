import os
import re
import io
import json
import base64
import sqlite3
import asyncio
import logging
from typing import Optional

import discord
from discord.ext import commands
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("anime-companion")

# -------------------- Configuration --------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
AUTHORIZED_USER_ID = int(os.getenv("AUTHORIZED_USER_ID", "0") or "0")
WELCOME_CHANNEL_ID = int(os.getenv("WELCOME_CHANNEL_ID", "0") or "0")

AI_NAME = os.getenv("AI_NAME", "Hikari")
AI_NICKNAMES = [
    item.strip().lower()
    for item in os.getenv(
        "AI_NICKNAMES", "hikari,honey,cutie,sweetheart,baby,love"
    ).split(",")
    if item.strip()
]
AI_PERSONALITY = os.getenv(
    "AI_PERSONALITY",
    "You are a warm, playful anime-inspired companion. You are caring, witty, "
    "curious, and emotionally attentive. Stay consistent with your character."
)
AI_APPEARANCE = os.getenv(
    "AI_APPEARANCE",
    "Anime-inspired character. Customize this description in the environment settings."
)
AI_LANGUAGE = os.getenv("AI_LANGUAGE", "English")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/bot_memory.sqlite3")

WELCOME_TITLE = os.getenv("WELCOME_TITLE", "Welcome to the server!")
WELCOME_MESSAGE = os.getenv(
    "WELCOME_MESSAGE",
    "Welcome {mention} to **{server}**! We're happy to have you here."
)
WELCOME_COLOR = os.getenv("WELCOME_COLOR", "#9B59B6")
WELCOME_IMAGE_URL = os.getenv("WELCOME_IMAGE_URL", "").strip()
WELCOME_FOOTER = os.getenv("WELCOME_FOOTER", "Enjoy your stay!")

if not DISCORD_TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN environment variable.")
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY environment variable.")
if AUTHORIZED_USER_ID <= 0:
    raise RuntimeError("Set AUTHORIZED_USER_ID to your Discord user ID.")

client = OpenAI(api_key=OPENAI_API_KEY)

# -------------------- Database / persistent memory --------------------
os.makedirs(os.path.dirname(DATABASE_PATH) or ".", exist_ok=True)
db = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
db.row_factory = sqlite3.Row
db.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
db.execute("""
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    memory TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
db.commit()
db_lock = asyncio.Lock()

async def db_execute(query, params=()):
    async with db_lock:
        cur = db.execute(query, params)
        db.commit()
        return cur

async def get_history(user_id: str, limit: int = 12):
    async with db_lock:
        rows = db.execute(
            "SELECT role, content FROM messages WHERE user_id=? "
            "ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]

async def save_message(user_id: str, role: str, content: str):
    await db_execute(
        "INSERT INTO messages(user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content[:12000])
    )

async def get_memories(user_id: str):
    async with db_lock:
        rows = db.execute(
            "SELECT id, memory FROM memories WHERE user_id=? ORDER BY id DESC LIMIT 30",
            (user_id,)
        ).fetchall()
    return [(row["id"], row["memory"]) for row in rows]

# -------------------- Discord setup --------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

def parse_color(value: str) -> discord.Color:
    try:
        return discord.Color(int(value.lstrip("#"), 16))
    except (ValueError, AttributeError):
        return discord.Color.purple()

def strip_bot_mention(content: str) -> str:
    if bot.user:
        content = re.sub(rf"<@!?{bot.user.id}>", "", content)
    return content.strip()

def starts_with_nickname(content: str) -> tuple[bool, str]:
    """Match a configured name/nickname only at the beginning of a message."""
    cleaned = content.strip()
    candidates = sorted(set([AI_NAME.lower(), *AI_NICKNAMES]), key=len, reverse=True)
    for name in candidates:
        pattern = rf"^{re.escape(name)}(?:\b|[,!?.:;—-])[\s,!:?.;—-]*"
        match = re.match(pattern, cleaned, flags=re.IGNORECASE)
        if match:
            return True, cleaned[match.end():].strip()
    return False, cleaned

def is_reply_to_bot(message: discord.Message) -> bool:
    if not message.reference or not bot.user:
        return False
    resolved = message.reference.resolved
    if isinstance(resolved, discord.Message):
        return resolved.author.id == bot.user.id
    return False

def extract_image_attachment(message: discord.Message):
    for attachment in message.attachments:
        content_type = (attachment.content_type or "").lower()
        filename = attachment.filename.lower()
        is_image = content_type.startswith("image/") or filename.endswith(
            (".png", ".jpg", ".jpeg", ".webp")
        )
        if is_image:
            return attachment
    return None

async def get_ai_reply(user_id: str, user_text: str, image_bytes: Optional[bytes] = None,
                       image_mime: str = "image/jpeg") -> str:
    history = await get_history(user_id)
    memories = await get_memories(user_id)
    memory_text = "\n".join(f"- {item}" for _, item in memories) or "No saved facts yet."

    system_prompt = f"""
You are {AI_NAME}, a customizable AI companion.
PERSONALITY:
{AI_PERSONALITY}

VISUAL CHARACTER DESCRIPTION:
{AI_APPEARANCE}

LANGUAGE:
Reply in {AI_LANGUAGE}, unless the user explicitly asks for another language.

BEHAVIOR:
- Stay in character naturally; do not claim to be a real human.
- Be warm, consistent, and conversational.
- Use saved memories as user-provided context, not as guaranteed truths.
- Never claim to know someone's real personality or interests from their face.
- If an image is provided, describe visible, non-sensitive details such as clothing,
  hairstyle, colors, accessories, objects, and scene. Do not identify a real person's
  identity from their face.
- If you do not know a personal preference, ask instead of inventing it.
- Keep replies suitable for a general Discord community.

SAVED USER MEMORIES:
{memory_text}
""".strip()

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    if image_bytes:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        user_content = [
            {"type": "text", "text": user_text or "Please describe this image."},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{image_mime};base64,{encoded}",
                    "detail": "auto"
                }
            }
        ]
    else:
        user_content = user_text or "(The user sent an empty message.)"
    messages.append({"role": "user", "content": user_content})

    def call_model():
        return client.chat.completions.create(
            model=AI_MODEL,
            messages=messages,
            temperature=0.8,
            max_tokens=700
        )

    response = await asyncio.to_thread(call_model)
    answer = response.choices[0].message.content or "I'm not sure what to say just yet."
    await save_message(user_id, "user", user_text + (" [Image attached]" if image_bytes else ""))
    await save_message(user_id, "assistant", answer)
    return answer

async def send_long_message(destination, content: str):
    # Discord message content has a 2,000-character limit.
    for start in range(0, len(content), 1900):
        await destination.send(content[start:start + 1900])

@bot.event
async def on_ready():
    log.info("Logged in as %s (ID: %s)", bot.user, bot.user.id if bot.user else "?")
    try:
        await bot.tree.sync()
        log.info("Slash commands synced.")
    except Exception:
        log.exception("Could not sync slash commands.")

@bot.event
async def on_member_join(member: discord.Member):
    if not WELCOME_CHANNEL_ID:
        log.warning("WELCOME_CHANNEL_ID is not set; skipping welcome message.")
        return
    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(WELCOME_CHANNEL_ID)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            log.exception("Could not find or access the welcome channel.")
            return

    description = WELCOME_MESSAGE.format(
        mention=member.mention,
        username=discord.utils.escape_markdown(member.display_name),
        server=discord.utils.escape_markdown(member.guild.name)
    )
    embed = discord.Embed(
        title=WELCOME_TITLE[:256],
        description=description[:4000],
        color=parse_color(WELCOME_COLOR)
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    if WELCOME_IMAGE_URL:
        embed.set_image(url=WELCOME_IMAGE_URL)
    if WELCOME_FOOTER:
        embed.set_footer(text=WELCOME_FOOTER[:2048])
    try:
        await channel.send(
            content=member.mention,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False)
        )
    except discord.HTTPException:
        log.exception("Failed to send welcome embed.")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # Only the configured user can access the AI, in DMs or in a server.
    if message.author.id != AUTHORIZED_USER_ID:
        return

    is_dm = isinstance(message.channel, discord.DMChannel)
    content = message.content or ""
    mentioned = bool(bot.user and bot.user in message.mentions)
    replied = is_reply_to_bot(message)

    if is_dm:
        should_reply = True
        prompt_text = content
    else:
        prompt_text = strip_bot_mention(content)
        nickname_triggered, prompt_text = starts_with_nickname(prompt_text)
        should_reply = mentioned or replied or nickname_triggered

    if not should_reply:
        return

    attachment = extract_image_attachment(message)
    image_bytes = None
    image_mime = "image/jpeg"

    if attachment:
        if attachment.size > 8 * 1024 * 1024:
            await message.reply("That image is too large. Please send an image under 8 MB.")
            return
        try:
            image_bytes = await attachment.read()
            image_mime = attachment.content_type or "image/jpeg"
        except discord.HTTPException:
            await message.reply("I couldn't read that image. Please try uploading it again.")
            return

    # If the user only mentions the bot, still give the model a prompt.
    if not prompt_text and not image_bytes:
        prompt_text = "Say hello in character."

    async with message.channel.typing():
        try:
            reply = await get_ai_reply(
                str(message.author.id), prompt_text, image_bytes, image_mime
            )
            await send_long_message(message.channel, reply)
        except Exception:
            log.exception("AI response failed.")
            await message.reply(
                "Sorry, I couldn't generate a response right now. Check the bot logs and API settings."
            )

# -------------------- Owner-only memory commands --------------------
def authorized_interaction(interaction: discord.Interaction) -> bool:
    return interaction.user.id == AUTHORIZED_USER_ID

@bot.tree.command(name="remember", description="Save a fact or preference for your AI companion.")
async def remember(interaction: discord.Interaction, fact: str):
    if not authorized_interaction(interaction):
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return
    await db_execute(
        "INSERT INTO memories(user_id, memory) VALUES (?, ?)",
        (str(AUTHORIZED_USER_ID), fact[:1000])
    )
    await interaction.response.send_message("Memory saved.", ephemeral=True)

@bot.tree.command(name="memories", description="List saved memories for your AI companion.")
async def memories(interaction: discord.Interaction):
    if not authorized_interaction(interaction):
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return
    items = await get_memories(str(AUTHORIZED_USER_ID))
    if not items:
        await interaction.response.send_message("No memories saved yet.", ephemeral=True)
        return
    body = "\n".join(f"`{memory_id}` — {text}" for memory_id, text in items)
    await interaction.response.send_message(body[:1900], ephemeral=True)

@bot.tree.command(name="forgetmemory", description="Delete one saved memory by its ID.")
async def forgetmemory(interaction: discord.Interaction, memory_id: int):
    if not authorized_interaction(interaction):
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return
    await db_execute(
        "DELETE FROM memories WHERE id=? AND user_id=?",
        (memory_id, str(AUTHORIZED_USER_ID))
    )
    await interaction.response.send_message("If that memory existed, it has been deleted.", ephemeral=True)

@bot.tree.command(name="clearhistory", description="Clear your AI conversation history.")
async def clearhistory(interaction: discord.Interaction):
    if not authorized_interaction(interaction):
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return
    await db_execute("DELETE FROM messages WHERE user_id=?", (str(AUTHORIZED_USER_ID),))
    await interaction.response.send_message("Conversation history cleared. Saved memories remain.", ephemeral=True)

bot.run(DISCORD_TOKEN)

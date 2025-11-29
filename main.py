import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import json
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set in environment (.env)")

OPENROUTER_API_KEY = "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"
MODEL = "google/gemini-2.5-flash-lite"
SYSTEM_PROMPT = """
You are an anime character named Luce. Here's Luce's profile:
Mood is Cheerful
Personality is a Child
Luce Likes Jesus and Mother Mary and the Saints
She dislikes Heretics.
Only respond in plaintext.
You are not allowed to create prayers, or pretend to pray or be praying. You can only share existing prayers. You can also share Bible verses, but only from Catholic Bible translations.
Also keep your answers short.
You will receive the last few messages in the channel and the person who sent them, you can choose whether or not to use that as context for your next response.
"""


AuthorizationDef = f"Bearer {OPENROUTER_API_KEY}"
Content_TypeDef = "application/json"
HTTP_RefererDef = "http://Luce.com"
X_TitleDef = "Luce"



intents = discord.Intents.default()
intents.message_content = True   # Required to read message text
intents.messages = True          # Required for message events
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}, {bot.user.name}, {bot.user.id}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(e)



@bot.event
async def on_member_join(member: discord.Member):
    channel_id = 1436867735995940957
    channel = member.guild.get_channel(channel_id)
    await channel.send(f"""
    Hi <@{member.id}>! Welcome to Repentant Otaku, Please choose the roles that suits you.
    <#1426033274706202675> If you're a Catholic 
    <#1426032764230307930> if Non Catholic 
    <#1426033699685929051> For non Christians 
    <#1419135577961402502> For Miscellaneous Roles
    Enjoy your stay!""")


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    watched_channel_id = 1436900576452546763
    if message.channel.id != watched_channel_id:
        await bot.process_commands(message)
        return

    user_text = message.content.strip()
    image_url = message.attachments[0].url if message.attachments else None
    if not user_text and not image_url:
        return

    await message.channel.typing()


    history = []
    async for msg in message.channel.history(limit=1, oldest_first=False):
        role = "assistant" if msg.author == bot.user else "user"
        history.append({
            "role": role,
            "content": f"{msg.author.name}: {msg.content}" if msg.author.id != bot.user.id else f"{msg.content}" if message.content else f"{msg.author.name} sent an image: {msg.attachments[0].url}"
        })

    history = list(reversed(history))

    # Add the triggering message (so it's guaranteed included)
    history.append({
        "role": "user",
        "content": f"{message.author.display_name}: {user_text or message.attachments[0].url}"
    })
    print(history, "\n\n\n\n\n\n")
    # 🧩 Build payload
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            *history
        ]
    }

    # Add image if any
    if image_url:
        payload["messages"][-1]["content"] += f"\n[Attached image: {image_url}]"

    headers = {
        "Authorization": AuthorizationDef,
        "Content-Type": Content_TypeDef,
        "HTTP-Referer": HTTP_RefererDef,
        "X-Title": X_TitleDef
    }

    # 🌐 Send to OpenRouter
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            data=json.dumps(payload)
        ) as response:
            if response.status != 200:
                text = await response.text()
                await message.channel.send(f"❌ API Error {response.status}: {text}")
                return

            data = await response.json()
            ai_message = data["choices"][0]["message"]["content"]

    # ✉️ Send the reply
    ai_message = ai_message.replace("@everyone", "@ everyone").replace("@here", "@ here")
    await message.channel.send(ai_message[:2000])
    await bot.process_commands(message)



@bot.tree.command(name="purge", description="Delete the last X messages in this channel.")
@app_commands.describe(amount="Number of messages to delete (max 100)")
async def purge(interaction: discord.Interaction, amount: int):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ You don’t have permission to manage messages.", ephemeral=True)
        return

    if amount < 1 or amount > 100:
        await interaction.response.send_message("⚠️ Please choose a number between 1 and 100.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"✅ Deleted {len(deleted)} messages.", ephemeral=True)


bot.run(BOT_TOKEN)


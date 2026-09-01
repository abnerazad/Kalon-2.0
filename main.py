import asyncio
import os
from threading import Thread
from flask import Flask
import discord
from discord.ext import commands

# --- FLASK WEB SERVER WORKAROUND ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    # Render provides a PORT environment variable dynamically
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# --- DISCORD BOT CODE ---
# Read variables securely from Render's Environment settings
VOICE_CHANNEL_ID = int(os.environ.get("VOICE_CHANNEL_ID", 0))
BOT_TOKEN = os.environ.get("BOT_TOKEN")

class PersistentVoiceBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        super().__init__(command_prefix="!", intents=intents)
        self.keep_alive_task = None

    async def on_ready(self):
        print(f"Logged in as {self.user.name}")
        if not self.keep_alive_task:
            self.keep_alive_task = self.loop.create_task(self.maintain_voice_connection())

    async def maintain_voice_connection(self):
        await self.wait_until_ready()
        channel = self.get_channel(VOICE_CHANNEL_ID)
        
        if not channel:
            print("Error: VOICE_CHANNEL_ID is invalid or missing.")
            return

        while not self.is_closed():
            try:
                guild = channel.guild
                voice_client = discord.utils.get(self.voice_clients, guild=guild)

                if not voice_client or not voice_client.is_connected():
                    await channel.connect(reconnect=True, self_deaf=True)
                elif voice_client.channel.id != VOICE_CHANNEL_ID:
                    await voice_client.move_to(channel)
            except Exception as e:
                print(f"Voice loop error: {e}")
            
            await asyncio.sleep(120)

    async def on_voice_state_update(self, member, before, after):
        if member.id == self.user.id:
            if before.channel is not None and after.channel is None:
                channel = self.get_channel(VOICE_CHANNEL_ID)
                if channel:
                    try:
                        await channel.connect(reconnect=True, self_deaf=True)
                    except Exception as e:
                        print(f"Voice state loop error: {e}")




# --- STARTUP ---
if __name__ == "__main__":
    keep_alive() # Starts the web server in the background
    bot = PersistentVoiceBot()
    bot.run(BOT_TOKEN)

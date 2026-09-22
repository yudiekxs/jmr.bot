import os
import asyncio
from telethon import TelegramClient, events

API_ID = int(os.environ.get("API_ID", "123456"))
API_HASH = os.environ.get("API_HASH", "YOUR_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TOKEN")

client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply('Bot running!')

async def main():
    print("Bot started")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())

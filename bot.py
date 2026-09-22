import os
import asyncio
from telethon import TelegramClient, events

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

client = TelegramClient('bot_session', API_ID, API_HASH, connection_retries=10)

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply('Bot running!')

async def main():
    print("Connecting...")
    await client.start(bot_token=BOT_TOKEN)
    print("Bot started")
    await client.run_until_disconnected()

if __name__ == '__main__':
    while True:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}, reconnecting in 10s...")
            asyncio.sleep(10)

import os
import asyncio
import random
from telethon import TelegramClient, events, Button
from telethon.tl.functions.messages import SendMessageRequest

# 环境变量（Secrets）
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# 机器人客户端（用于菜单交互）
bot = TelegramClient('bot_session', API_ID, API_HASH)
# 主号客户端（用于实际发消息，登录后复用）
user = None

# 状态存储（简易内存，重启会丢，适合测试）
STATE = {
    "target": None,      # 目标群组/用户
    "numbers": [],       # 选中的号码（或联系人）
    "messages": [],      # 多条内容
    "running": False,
    "login_step": 0,
}

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    if STATE["login_step"] == 0:
        await event.reply(
            "🤖 主菜单\n\n"
            "1️⃣ 先登录主号（发消息用）\n"
            "2️⃣ 选目标\n"
            "3️⃣ 选号/联系人\n"
            "4️⃣ 设多条内容\n"
            "5️⃣ 开始狂发\n\n"
            "发送 /login 开始登录主号",
            buttons=[
                [Button.inline("① 登录主号", b"login")],
                [Button.inline("② 选目标", b"target")],
                [Button.inline("③ 选号", b"numbers")],
                [Button.inline("④ 设内容", b"msgs")],
                [Button.inline("⑤ 狂发", b"run")],
            ]
        )
    else:
        await event.reply("继续登录流程... 发送 /login 重新来")

@bot.on(events.NewMessage(pattern='/login'))
async def login(event):
    STATE["login_step"] = 1
    await event.reply("📲 发送你的手机号（含国家码，如 +86138xxxx）")
    STATE["login_step"] = 2

@bot.on(events.NewMessage)
async def handler(event):
    text = event.text.strip()
    if text.startswith('/'):
        return

    # 登录流程
    if STATE["login_step"] == 2:
        STATE["phone"] = text
        global user
        user = TelegramClient('user_session', API_ID, API_HASH)
        await user.connect()
        try:
            sent = await user.send_code_request(text)
            STATE["login_step"] = 3
            await event.reply("✅ 验证码已发，发送你收到的验证码")
        except Exception as e:
            await event.reply(f"❌ 发验证码失败: {e}")
            STATE["login_step"] = 0
        return

    if STATE["login_step"] == 3:
        try:
            await user.sign_in(code=text)
            STATE["login_step"] = 0
            await event.reply("✅ 主号登录成功！返回 /start")
        except Exception as e:
            await event.reply(f"❌ 登录失败: {e}")
        return

    # 选目标
    if text == "目标":
        STATE["login_step"] = 10
        await event.reply("发送目标（群组链接/@用户名/ID）")
        return
    if STATE["login_step"] == 10:
        STATE["target"] = text
        STATE["login_step"] = 0
        await event.reply(f"✅ 目标: {text}")

    # 选号
    if text == "选号":
        STATE["login_step"] = 20
        await event.reply("发送号码/联系人（每行一个，或发 全部）")
        return
    if STATE["login_step"] == 20:
        STATE["numbers"] = [x.strip() for x in text.split('\n') if x.strip()]
        STATE["login_step"] = 0
        await event.reply(f"✅ 已选 {len(STATE['numbers'])} 个")

    # 设内容
    if text == "内容":
        STATE["login_step"] = 30
        await event.reply("发送多条内容（每行一条，发完发 完成）")
        STATE["messages"] = []
        return
    if STATE["login_step"] == 30:
        if text == "完成":
            STATE["login_step"] = 0
            await event.reply(f"✅ 已设 {len(STATE['messages'])} 条")
        else:
            STATE["messages"].append(text)
            await event.reply(f"已加: {text}（继续或发 完成）")
        return

@bot.on(events.CallbackQuery)
async def buttons(event):
    data = event.data.decode()
    if data == "login":
        await event.edit("发送 /login 开始")
    elif data == "target":
        await event.edit("发送: 目标")
        STATE["login_step"] = 10
    elif data == "numbers":
        await event.edit("发送: 选号")
        STATE["login_step"] = 20
    elif data == "msgs":
        await event.edit("发送: 内容")
        STATE["login_step"] = 30
    elif data == "run":
        if not user:
            await event.edit("❌ 先登录主号")
            return
        if not STATE["target"]:
            await event.edit("❌ 先选目标")
            return
        if not STATE["messages"]:
            await event.edit("❌ 先设内容")
            return
        STATE["running"] = True
        await event.edit("🚀 开始狂发（发 /stop 停止）")
        asyncio.create_task(spam_loop())

async def spam_loop():
    while STATE["running"]:
        msg = random.choice(STATE["messages"])
        try:
            if STATE["numbers"]:
                for num in STATE["numbers"]:
                    await user(SendMessageRequest(num, msg))
                    await asyncio.sleep(random.uniform(2, 5))
            else:
                await user(SendMessageRequest(STATE["target"], msg))
            await asyncio.sleep(random.uniform(3, 8))
        except Exception as e:
            print(f"发送失败: {e}")
            await asyncio.sleep(10)

@bot.on(events.NewMessage(pattern='/stop'))
async def stop(event):
    STATE["running"] = False
    await event.reply("🛑 已停止")

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    print("Bot started")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    while True:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}, reconnecting...")
            asyncio.sleep(10)

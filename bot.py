# -*- coding: utf-8 -*-
import os
import asyncio
import logging
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, FloodWaitError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== 从 GitHub Secrets 读取 =====
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

STATE = {}

def get_st(uid):
    if uid not in STATE:
        STATE[uid] = {
            "clients": {}, "messages": [], "step": None,
            "code_input": "", "pw_input": "", "running": False,
            "text": "1", "target": None, "interval": 1, "rounds": 0, "selected": [],
            "phone": "", "name": "", "client": None,
            "spam_tasks": {},
            "spam_stats": {},
        }
    return STATE[uid]

def main_menu():
    return [
        [Button.inline("➕ 登录账号", b"login"), Button.inline("📒 已登录账号", b"list")],
        [Button.inline("📤 选择发送账号", b"select"), Button.inline("🎯 设目标", b"target")],
        [Button.inline("✏️ 单条内容", b"text"), Button.inline("📝 多条内容", b"messages")],
        [Button.inline("⏱ 设间隔", b"interval"), Button.inline("🔢 设轮数", b"rounds")],
        [Button.inline("🚀 立即狂发", b"run"), Button.inline("🛑 停止", b"stop")],
    ]

def code_keyboard(val):
    return [
        [Button.inline("1", b"1"), Button.inline("2", b"2"), Button.inline("3", b"3"), Button.inline("❌删", b"del")],
        [Button.inline("4", b"4"), Button.inline("5", b"5"), Button.inline("6", b"6")],
        [Button.inline("7", b"7"), Button.inline("8", b"8"), Button.inline("9", b"9")],
        [Button.inline("🔄重来", b"reset"), Button.inline("0", b"0"), Button.inline("✅确认", b"ok")],
        [Button.inline("🔙 主菜单", b"home")],
    ]

async def show_main(event, st):
    try:
        await event.edit("🔧 主菜单：", buttons=main_menu())
    except:
        await event.respond("🔧 主菜单：", buttons=main_menu())
    st["step"] = None
    st["code_input"] = ""
    st["pw_input"] = ""

bot = TelegramClient("bot_panel", API_ID, API_HASH)

@bot.on(events.NewMessage(pattern="/start"))
async def cmd_start(event):
    st = get_st(event.sender_id)
    st["step"] = None
    await event.respond("👋 控制面板（各看各号）", buttons=main_menu())

@bot.on(events.CallbackQuery())
async def cb(event):
    uid = event.sender_id
    st = get_st(uid)
    d = event.data.decode()

    if d in ("1","2","3","4","5","6","7","8","9","0","del","reset","ok"):
        step = st.get("step")
        if step not in ("code", "password"):
            await event.answer()
            return
        key = "code_input" if step == "code" else "pw_input"
        val = st.get(key, "")

        if d == "del":
            val = val[:-1]
        elif d == "reset":
            val = ""
        elif d == "ok":
            if step == "code":
                try:
                    await st["client"].sign_in(st["phone"], code=val)
                    st["clients"][st["name"]] = st["client"]
                    st["step"] = None
                    st["code_input"] = ""
                    await event.edit("✅ 登录成功！", buttons=main_menu())
                    await event.answer()
                    return
                except SessionPasswordNeededError:
                    st["step"] = "password"
                    st["pw_input"] = ""
                    await event.edit("🔐 需2FA，点按钮输入数字密码：", buttons=code_keyboard(""))
                    await event.answer()
                    return
                except PhoneCodeInvalidError:
                    val = ""
                    st["code_input"] = ""
                    await event.edit("❌ 验证码错，重来：", buttons=code_keyboard(""))
                    await event.answer()
                    return
                except Exception as e:
                    await event.edit(f"❌ {e}", buttons=main_menu())
                    await event.answer()
                    return
            else:
                try:
                    await st["client"].sign_in(password=val)
                    st["clients"][st["name"]] = st["client"]
                    st["step"] = None
                    st["pw_input"] = ""
                    await event.edit("✅ 登录成功（2FA）！", buttons=main_menu())
                    await event.answer()
                    return
                except Exception as e:
                    val = ""
                    st["pw_input"] = ""
                    await event.edit(f"❌ 2FA密码错：{e}\n重来：", buttons=code_keyboard(""))
                    await event.answer()
                    return
        else:
            if len(val) >= 6:
                await event.answer("最多6位", alert=True)
                return
            val += d
        st[key] = val
        kb = code_keyboard(val)
        display = "•" * len(val) if step == "password" else val
        label = "验证码" if step == "code" else "2FA密码"
        await event.edit(f"{label}：{display or '空'}", buttons=kb)
        await event.answer()
        return

    if d == "home":
        await show_main(event, st)
        await event.answer()
        return

    if d == "login":
        st["step"] = "phone"
        await event.edit("📱 发手机号（带国家码）：\n例：+8613800000000", buttons=[Button.inline("🔙 主菜单", b"home")])
        await event.answer()

    elif d == "list":
        if not st["clients"]:
            await event.edit("你还没登录任何账号", buttons=main_menu())
        else:
            txt = "\n".join(f"• {n}" for n in st["clients"])
            await event.edit(f"你的账号：\n{txt}", buttons=main_menu())
        await event.answer()

    elif d == "select":
        if not st["clients"]:
            await event.answer("先登录账号！", alert=True)
            return
        kb = []
        for n in st["clients"]:
            mark = "✅" if n in st["selected"] else "⬜"
            kb.append([Button.inline(f"{mark} {n}", f"sel|{n}".encode())])
        kb.append([Button.inline("🔙 完成返回", b"back")])
        kb.append([Button.inline("🔙 主菜单", b"home")])
        await event.edit("点账号勾选/取消：", buttons=kb)
        await event.answer()

    elif d.startswith("sel|"):
        n = d.split("|", 1)[1]
        if n in st["selected"]: st["selected"].remove(n)
        else: st["selected"].append(n)
        kb = []
        for n2 in st["clients"]:
            mark = "✅" if n2 in st["selected"] else "⬜"
            kb.append([Button.inline(f"{mark} {n2}", f"sel|{n2}".encode())])
        kb.append([Button.inline("🔙 完成返回", b"back")])
        kb.append([Button.inline("🔙 主菜单", b"home")])
        await event.edit(f"已选 {len(st['selected'])} 个", buttons=kb)
        await event.answer()

    elif d == "back":
        await show_main(event, st)
        await event.answer()

    elif d == "target":
        st["step"] = "target"
        await event.edit("🎯 发目标：@用户名 / https://t.me/xxx", buttons=[Button.inline("🔙 主菜单", b"home")])
        await event.answer()

    elif d == "text":
        st["step"] = "text"
        await event.edit("✏️ 发单条内容：", buttons=[Button.inline("🔙 主菜单", b"home")])
        await event.answer()

    elif d == "messages":
        st["step"] = "messages"
        st["messages"] = []
        await event.edit("📝 一行一条内容，发完打 /done", buttons=[Button.inline("🔙 主菜单", b"home")])
        await event.answer()

    elif d == "interval":
        cur = st.get("interval", 1)
        await event.edit(f"当前间隔：{cur}秒\n选择新间隔：", buttons=[
            [Button.inline("0秒(狂暴)", b"iv_0")],
            [Button.inline("1秒", b"iv_1")],
            [Button.inline("3秒", b"iv_3")],
            [Button.inline("5秒", b"iv_5")],
            [Button.inline("🔙 主菜单", b"home")],
        ])
        await event.answer()

    elif d.startswith("iv_"):
        val = int(d.split("_", 1)[1])
        st["interval"] = val
        await show_main(event, st)
        await event.answer()

    elif d == "rounds":
        st["step"] = "rounds"
        cur = st.get("rounds", 0)
        await event.edit(f"当前：{cur}（0=无限循环）\n发数字：", buttons=[Button.inline("🔙 主菜单", b"home")])
        await event.answer()

    elif d == "run":
        if not st["clients"]:
            await event.answer("先登录账号！", alert=True)
            return
        if not st.get("target"):
            await event.answer("先设目标！", alert=True)
            return

        msgs = st.get("messages", [])
        if not msgs:
            msgs = [st.get("text", "1")]

        sel = st["selected"] or list(st["clients"].keys())[:1]
        st["running"] = True
        st["spam_stats"] = {}
        st["spam_tasks"] = {}

        for n in sel:
            st["spam_stats"][n] = {"count": 0, "running": True}
            c = st["clients"][n]
            task = asyncio.create_task(
                spammer(uid, n, c, st["target"], msgs, st.get("interval", 1), st.get("rounds", 0))
            )
            st["spam_tasks"][n] = task

        round_txt = f"{st['rounds']}轮" if st.get("rounds", 0) > 0 else "无限循环"
        await event.edit(
            f"🚀 狂发中\n发送账号：{len(sel)}个\n目标：{st['target']}\n内容数：{len(msgs)}\n间隔：{st['interval']}秒\n轮数：{round_txt}",
            buttons=[[Button.inline("🛑 停止", b"stop")], [Button.inline("📊 进度", b"progress")]]
        )
        await event.answer()

    elif d == "progress":
        stats = st.get("spam_stats", {})
        if not stats:
            await event.answer("暂无进度", alert=True)
            return
        txt = "\n".join(f"• {n}: {s['count']}条" for n, s in stats.items())
        await event.answer(txt, alert=True)

    elif d == "stop":
        st["running"] = False
        for n, s in st.get("spam_stats", {}).items():
            s["running"] = False
        for n, task in st.get("spam_tasks", {}).items():
            task.cancel()
        await show_main(event, st)
        await event.answer()

    else:
        await event.answer()

@bot.on(events.NewMessage())
async def chat(event):
    uid = event.sender_id
    st = get_st(uid)
    msg = event.message.text.strip()

    if msg == "/done":
        if st.get("step") == "messages":
            count = len(st.get("messages", []))
            st["step"] = None
            try:
                await event.delete()
            except:
                pass
            if count == 0:
                await event.respond("❌ 没存到内容，已回主菜单", buttons=main_menu())
            else:
                await event.respond(f"✅ 已存 {count} 条，已回主菜单", buttons=main_menu())
            return
        else:
            st["step"] = None
            await event.respond("🔧 主菜单：", buttons=main_menu())
            return

    if msg.startswith("/"):
        return

    step = st.get("step")

    if step == "phone":
        st["phone"] = msg
        st["name"] = f"acc_{uid}_{msg}"
        client = TelegramClient(st["name"], API_ID, API_HASH)
        await client.connect()
        try:
            await client.send_code_request(msg)
            st["client"] = client
            st["step"] = "code"
            st["code_input"] = ""
            await event.respond("📲 验证码已发，点按钮输入：", buttons=code_keyboard(""))
        except Exception as e:
            await event.respond(f"❌ {e}", buttons=main_menu())
            st["step"] = None
        return

    if step == "target":
        st["target"] = msg
        st["step"] = None
        await event.respond(f"✅ 目标：{msg}", buttons=main_menu())
        return

    if step == "text":
        st["text"] = msg
        st["messages"] = [msg]
        st["step"] = None
        await event.respond(f"✅ 单条内容：{msg}", buttons=main_menu())
        return

    if step == "messages":
        st.setdefault("messages", []).append(msg)
        n = len(st["messages"])
        await event.respond(f"✅ 第{n}条已存\n继续发，完事 /done")
        return

    if step == "rounds":
        try:
            v = int(msg)
            if v < 0: raise ValueError
            st["rounds"] = v
            st["step"] = None
            txt = f"{v}轮" if v > 0 else "无限循环"
            await event.respond(f"✅ 轮数：{txt}", buttons=main_menu())
        except ValueError:
            await event.respond("❌ 发数字，0=无限")
        return

async def spammer(uid, name, client, target, messages, interval, rounds):
    st = STATE.get(uid, {})
    i = 0
    count = 0
    per = len(messages)
    stats = st.get("spam_stats", {}).get(name, {"count": 0, "running": True})

    while st.get("running") and stats.get("running", True):
        text = messages[i % per]
        try:
            await client.send_message(target, text)
            count += 1
            i += 1
            stats["count"] = count
            if count % 10 == 0:
                logger.info(f"[{name}] 已发{count}条")
        except FloodWaitError as e:
            logger.error(f"[{name}] 限流{e.seconds}秒，自动停止")
            st["spam_stats"][name]["running"] = False
            try:
                await client.send_message("me", f"⚠️ [{name}] 被限流 {e.seconds}秒，已自动停止。")
            except:
                pass
            break
        except Exception as e:
            logger.error(f"[{name}] 出错: {e}")
            await asyncio.sleep(2)
            continue

        if rounds > 0 and count >= rounds * per:
            st["spam_stats"][name]["running"] = False
            break

        if interval > 0:
            await asyncio.sleep(interval)

    st["spam_stats"][name]["running"] = False
    st["spam_stats"][name]["count"] = count
    logger.info(f"[{name}] 结束，共{count}条")

# ===== 断线重连外壳 =====
async def main():
    await bot.start(bot_token=BOT_TOKEN)
    print("Bot 启动，限流自动停止+进度查看")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"断开: {e}，10秒后重连...")
            asyncio.sleep(10)

"""
MIT License

Copyright (c) 2023 TheHamkerCat

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import asyncio
import os
import subprocess
import time

import psutil
from pyrogram import filters, types
from pyrogram.errors import FloodWait
from pyrogram.types import ChatPermissions, InlineKeyboardMarkup

from wbb import (
    BOT_ID,
    GBAN_LOG_GROUP_ID,
    FMUTE_LOG_GROUP_ID,
    SUDOERS,
    USERBOT_USERNAME,
    app,
    bot_start_time,
)
from wbb.core.decorators.errors import capture_err
from wbb.utils import formatter
from wbb.utils.dbfunctions import (
    add_gban_user,
    get_served_chats,
    is_gbanned_user,
    remove_gban_user,
    get_served_users,
    add_fmute_user,
    is_fmuted_user,
    remove_fmute_user,
)
from wbb.utils.functions import extract_user, extract_user_and_reason, restart

__MODULE__ = "Sudoers"
__HELP__ = """
/stats - Để kiểm tra trạng thái hệ thống.

/gstats - Để kiểm tra số liệu thống kê toàn cầu của Bot.

/bf - Để cấm người dùng trên toàn cầu.

/ubf - Bỏ cấm người dùng trên toàn cầu.

/m - Tắt tiếng người dùng trên toàn cầu.

/um - Để bật tiếng người dùng trên toàn cầu.

/clean_db - Làm sạch cơ sở dữ liệu.

/broadcast - Để phát tin nhắn cho tất cả các nhóm.

/ubroadcast - Để phát một tin nhắn tới tất cả người dùng.

/update - Để cập nhật và khởi động lại bot

/eval - Thực thi mã Python

/sh - Thực thi mã Shell
"""


# Stats Module


async def bot_sys_stats():
    bot_uptime = int(time.time() - bot_start_time)
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    process = psutil.Process(os.getpid())
    stats = f"""
{USERBOT_USERNAME} @COIHAYCOC
------------------
UPTIME: {formatter.get_readable_time(bot_uptime)}
BOT: {round(process.memory_info()[0] / 1024 ** 2)} MB
CPU: {cpu}%
RAM: {mem}%
DISK: {disk}%
"""
    return stats


# Gban


@app.on_message(filters.command("bf") & SUDOERS)
@capture_err
async def ban_globally(_, message):
    user_id, reason = await extract_user_and_reason(message)
    user = await app.get_users(user_id)
    from_user = message.from_user

    if not user_id:
        return await message.reply_text("Tôi không thể tìm thấy người dùng này.")
    if not reason:
        return await message.reply("Không có lý do cung cấp.")

    if user_id in [from_user.id, BOT_ID] or user_id in SUDOERS:
        return await message.reply_text("ITôi không thể cấm người dùng này.")

    served_chats = await get_served_chats()
    m = await message.reply_text(
        f"**Đang cấm {user.mention} trên toàn hệ thống!**"
        + f" **Hành động này sẽ mất khoảng {len(served_chats)} giây.**"
    )
    await add_gban_user(user_id)
    number_of_chats = 0
    for served_chat in served_chats:
        try:
            await app.ban_chat_member(served_chat["chat_id"], user.id)
            number_of_chats += 1
            await asyncio.sleep(1)
        except FloodWait as e:
            await asyncio.sleep(int(e.value))
        except Exception:
            pass
    try:
        await app.send_message(
            user.id,
            f"Xin chào, Bạn đã bị cấm trên toàn hệ thống bởi {from_user.mention},"
            f" Bạn có thể khiếu nại lệnh cấm này bằng cách nói chuyện với {from_user.mention}.",
        )
    except Exception:
        pass
    await m.edit(f"Đã cấm {user.mention} trên toàn hệ thống!")
    ban_text = f"""
__**Người dùng bị cấm trên toàn hệ thống**__
**Tại:** {message.chat.title} [`{message.chat.id}`]
**Quản trị viên:** {from_user.mention}
**Người dùng bị cấm:** {user.mention}
**ID người dùng bị cấm:** `{user_id}`
**Lý do:** __{reason}__
**Số nhóm:** `{number_of_chats}`"""
    try:
        m2 = await app.send_message(
            GBAN_LOG_GROUP_ID,
            text=ban_text,
            disable_web_page_preview=True,
        )
        await m.edit(
            f"""Đã cấm {user.mention} trên toàn hệ thống bởi {from_user.mention}!!!""",
            disable_web_page_preview=True,
        )
    except Exception:
        await message.reply_text(
            "Đã cấm người này trên toàn hệ thống, nhưng hành động này không được ghi lại, hãy thêm tôi vào nhóm quản lý"
        )


# Ungban


@app.on_message(filters.command("ubf") & SUDOERS)
@capture_err
async def unban_globally(_, message):
    user_id = await extract_user(message)
    if not user_id:
        return await message.reply_text("Tôi không thể tìm thấy người dùng này.")
    user = await app.get_users(user_id)

    is_gbanned = await is_gbanned_user(user.id)
    if not is_gbanned:
        await message.reply_text("Tôi không nhớ đã cấm người này trên toàn hệ thống.")
    else:
        await remove_gban_user(user.id)
        await message.chat.unban_member(user_id)
        await message.reply_text(f"Đã bỏ cấm {user.mention}.'")



# Broadcast


@app.on_message(filters.command("up") & SUDOERS)
@capture_err
async def broadcast_message(_, message):
    sleep_time = 0.1
    text = message.reply_to_message.text.markdown
    reply_message = message.reply_to_message

    reply_markup = None
    if reply_message.reply_markup:
        reply_markup = InlineKeyboardMarkup(reply_message.reply_markup.inline_keyboard)
    sent = 0
    schats = await get_served_chats()
    chats = [int(chat["chat_id"]) for chat in schats]
    m = await message.reply_text(
        f"Broadcast in progress, will take {len(chats) * sleep_time} seconds."
    )
    for i in chats:
        try:
            await app.send_message(
                i,
                text=text,
                reply_markup=reply_markup,
            )
            await asyncio.sleep(sleep_time)
            sent += 1
        except FloodWait as e:
            await asyncio.sleep(int(e.value))
        except Exception:
            pass
    await m.edit(f"**Broadcasted Message In {sent} Chats.**")


# Update


@app.on_message(filters.command("update") & SUDOERS)
async def update_restart(_, message):
    try:
        out = subprocess.check_output(["git", "pull"]).decode("UTF-8")
        if "Already up to date." in str(out):
            return await message.reply_text("Nó đã được cập nhật!")
        await message.reply_text(f"```{out}```")
    except Exception as e:
        return await message.reply_text(str(e))
    m = await message.reply_text("**Đã cập nhật với nhánh mặc định, đang khởi động lại.**")
    await restart(m)


@app.on_message(filters.command("uup") & SUDOERS)
@capture_err
async def broadcast_message(_, message):
    sleep_time = 0.1
    sent = 0
    schats = await get_served_users()
    chats = [int(chat["user_id"]) for chat in schats]
    text = message.reply_to_message.text.markdown
    reply_message = message.reply_to_message

    reply_markup = None
    if reply_message.reply_markup:
        reply_markup = InlineKeyboardMarkup(reply_message.reply_markup.inline_keyboard)

    m = await message.reply_text(
        f"Broadcast in progress, will take {len(chats) * sleep_time} seconds."
    )

    for i in chats:
        try:
            await app.send_message(
                i,
                text=text,
                reply_markup=reply_markup,
            )
            await asyncio.sleep(sleep_time)
            sent += 1
        except FloodWait as e:
            await asyncio.sleep(int(e.value))
        except Exception:
            pass
    await m.edit(f"**Broadcasted Message to {sent} Users.**")

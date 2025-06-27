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
import re
from contextlib import suppress
from time import time

from pyrogram import filters
from pyrogram.enums import ChatMembersFilter, ChatType, MessageEntityType
from pyrogram.errors import FloodWait
from pyrogram.types import (
    CallbackQuery,
    ChatMemberUpdated,
    ChatPermissions,
    ChatPrivileges,
    Message,
)

from wbb import BOT_ID, SUDOERS, app, app2, log
from wbb.core.decorators.errors import capture_err
from wbb.core.keyboard import ikb
from wbb.utils.dbfunctions import (
    add_warn,
    get_warn,
    int_to_alpha,
    remove_warns,
    save_filter,
)
from wbb.utils.functions import (
    extract_user,
    extract_user_and_reason,
    time_converter,
    get_urls_from_text,
)
from wbb import FMUTE_LOG_GROUP_ID
from wbb import XAC_NHAN
from wbb.utils.dbfunctions import (
    get_served_chats,
    add_fmute_user,
    is_fmuted_user,
    remove_fmute_user,
    add_active_user,
    is_actived_user,
    remove_active_user,
)
from datetime import datetime, timedelta
import pytz
from wbb.core.decorators.permissions import adminsOnly

vietnam_timezone = pytz.timezone(
    'Asia/Ho_Chi_Minh')  # Define the Vietnam timezone
# Get the current time in Vietnam timezone
current_time_vietnam = datetime.now(
    tz=vietnam_timezone).strftime("%Y-%m-%d %H:%M:%S")

admins_in_chat = {}

async def refresh_admin_cache(chat_id: int):
    global admins_in_chat
    admins = [
        member.user.id
        async for member in app.get_chat_members(
            chat_id, filter=ChatMembersFilter.ADMINISTRATORS
        )
    ]
    admins_in_chat[chat_id] = {
        "last_updated_at": time(),
        "data": admins,
    }
    log.info(f"⚙️ Đã làm mới cache admin cho nhóm {chat_id}")
    return admins

@app.on_message(filters.command("reload") & filters.group)
@adminsOnly("can_manage_chat")
async def force_refresh_admin_cache(_, message: Message):
    chat_id = message.chat.id
    await refresh_admin_cache(chat_id)
    await message.reply_text("✅ Cache admin đã được làm mới.")


# Admin cache reload

@app.on_chat_member_updated()
async def admin_cache_func(_, cmu: ChatMemberUpdated):
    chat_id = cmu.chat.id
    async for member in app.get_chat_members(chat_id):
        pass 
    await refresh_admin_cache(cmu.chat.id)


@app.on_message(filters.text & ~filters.private, group=69)
async def url_bio(_, message):
    user = message.from_user
    chat_id = message.chat.id
    keyboard = ikb({"🚨  Mở chat  🚨": "https://t.me/boost?c=1707112470"})
    try:
        bio = (await app.get_chat(user.id)).bio
    except FloodWait as e:
        await asyncio.sleep(e.value)
        bio = (await app.get_chat(user.id)).bio

    link = f"t.me/"
    vietnam_time = datetime.utcnow() + timedelta(hours=7)
    timestamp_vietnam = vietnam_time.strftime('%H:%M:%S %d-%m-%Y')

    if not bio or not user:
        return
    mods = await admins(chat_id)
    if user.id in mods or user.id in SUDOERS:
        return

    #if is_fmuted:
        #return

    #if is_actived:
        #return

    check = get_urls_from_text(bio)
    if not check:
        return
        #await message.reply_text(f"Ê !!! [{user.mention}](tg://openmessage?user_id={user.id})  @{user.username} có link ở bio. Đã khóa mõm nó.")
        #await message.chat.restrict_member(user.id, permissions=ChatPermissions())
    served_chats = await get_served_chats()
    m = await message.reply_text(
        f"**Đang cấm chat {user.mention} trên toàn hệ thống!**"
        + f" **Hành động này sẽ mất khoảng {len(served_chats)} giây.**"
    )
    await add_fmute_user(user.id)
    number_of_chats = 0
    for served_chat in served_chats:
        try:
            await app.restrict_chat_member(served_chat["chat_id"], user.id, permissions=ChatPermissions())
            number_of_chats += 1
            await asyncio.sleep(1)
        except FloodWait as e:
            await asyncio.sleep(int(e.value))
        except Exception:
            log.error(f"Lỗi khi cấm chat ở nhóm {served_chat['chat_id']}: {e}")
            pass

    try:
        await app.send_message(
            user.id,
            f"Xin chào {user.mention}, Bạn đã bị cấm chat toàn hệ thống tại nhóm {message.chat.title} do gắn link ở bio."
            f" Bạn hãy nhắn tin cho admin để mở chat."
        )
    except Exception:
        log.error(f"Lỗi khi nhắn tin đến {user.id}: {e}")
        pass
    
    
    await m.edit(f"Đã cấm chat {user.mention} toàn hệ thống!")
    mute_text = f"""
__**Người dùng bị cấm chat do link bio toàn hệ thống**__
**Tại nhóm:** {message.chat.title} [`{message.chat.id}`]
**Người dùng bị cấm chat:** {user.mention} @{user.username}
**ID người dùng bị cấm chat:** `{user.id}`
**Link bio:** __{bio}__
**Lúc:** __{timestamp_vietnam}__
**Số nhóm:** `{number_of_chats}`"""
    try:
        m2 = await app.send_message(
            FMUTE_LOG_GROUP_ID,
            text=mute_text,
            disable_web_page_preview=True,
        )
        await m.edit(
f"""**🔥Người dùng [{user.mention}](tg://openmessage?user_id={user.id})  @{user.username} đã bị 🚫khóa mõm tất cả nhóm trong hệ thống.**
**Lý do: có link ở bio  💬💬💬.**""", reply_markup=keyboard)
            #f"""**Đã cấm chat {user.mention} @{username2} trên toàn hệ thống!!!\n Gửi voice cho {reason or from_user.mention}  để được mỡ chat  💬💬💬**""",
    except Exception:
        await message.reply_text(
            "Người dùng bị cấm chat, nhưng hành động cấm chat này không được ghi lại, hãy thêm tôi vào nhóm quản lý"
        )

#@app.on_message(filters.command("reloadaa"))
@app.on_chat_member_updated(filters.group, group=69)
@capture_err
async def link_bio(_, user: ChatMemberUpdated):
    if not (
        user.new_chat_member
        and not user.old_chat_member
    ):
        return

    chat_id = user.chat.id
    user1 = user.new_chat_member.user if user.new_chat_member else user.from_user
    keyboard = ikb({"🚨  Mở chat  🚨": "https://t.me/boost?c=1707112470"})
    link = f"t.me/"
    is_fmuted = await is_fmuted_user(user1.id)
    is_actived = await is_actived_user(user1.id)
    vietnam_time = datetime.utcnow() + timedelta(hours=7)
    timestamp_vietnam = vietnam_time.strftime('%H:%M:%S %d-%m-%Y')
    
    if user1.id in SUDOERS:
        return

    if is_fmuted:
        return

    if is_actived:
        return

    try:
        bio = (await app.get_chat(user1.id)).bio
    except FloodWait as e:
        await asyncio.sleep(e.value)  # đợi đúng số giây Telegram yêu cầu
        bio = (await app.get_chat(user1.id)).bio  # thử lại sau khi đã đợi

    if not bio or not user:
        return

    check = get_urls_from_text(bio)
    if not check:
        return
    
    served_chats = await get_served_chats()
    m = await app.send_message(
        chat_id,
        f"**Đang cấm chat {user1.mention} trên toàn hệ thống!**"
        + f" **Hành động này sẽ mất khoảng {len(served_chats)} giây.**"
    )
    #await app.restrict_chat_member(chat_id, user1.id, permissions=ChatPermissions())
    
    number_of_chats = 0
    for served_chat in served_chats:
        try:
            await app.restrict_chat_member(served_chat["chat_id"], user1.id, permissions=ChatPermissions())
            number_of_chats += 1
            await asyncio.sleep(1)
        except FloodWait as e:
            await asyncio.sleep(int(e.value))
        except Exception:
            log.error(f"Lỗi khi cấm chat ở nhóm {served_chat['chat_id']}: {e}")
            pass
    
    
    await m.edit(f"Đã cấm chat {user1.mention} toàn hệ thống!")
    mute_text = f"""
__**Người dùng bị cấm chat do link bio toàn hệ thống**__
**Tại nhóm:** {user.chat.title} [`{user.chat.id}`]
**Người dùng bị cấm chat:** {user1.mention} @{user1.username}
**ID người dùng bị cấm chat:** `{user1.id}`
**Link bio:** __{bio}__
**Lúc:** __{timestamp_vietnam}__
**Số nhóm:** `{number_of_chats}`"""
    try:
        m2 = await app.send_message(
            FMUTE_LOG_GROUP_ID,
            text=mute_text,
            disable_web_page_preview=True,
        )
        await m.edit(
f"""**🔥Người dùng [{user1.mention}](tg://openmessage?user_id={user1.id})  @{user1.username} đã bị 🚫khóa mõm tất cả nhóm trong hệ thống.**
**Lý do: có link ở bio  💬💬💬.**""", reply_markup=keyboard)
            #f"""**Đã cấm chat {user.mention} @{username2} trên toàn hệ thống!!!\n Gửi voice cho {reason or from_user.mention}  để được mỡ chat  💬💬💬**""",
    except Exception:
        await app.send_message(
            "Người dùng bị cấm chat, nhưng hành động cấm chat này không được ghi lại, hãy thêm tôi vào nhóm quản lý"
        )
    await add_fmute_user(user1.id)
    await asyncio.sleep(10) 

# Fmute
'''@app.on_message(filters.command("fm") & ~filters.private)
@adminsOnly("can_restrict_members")
@capture_err
async def mute_globally(_, message: Message):
    await refresh_admin_cache(message.chat.id)
    user_id, reason = await extract_user_and_reason(message)
    chat_id = message.chat.id
    user = await app.get_users(user_id)
    from_user = message.from_user
    is_fmuted = await is_fmuted_user(user.id)
    is_actived = await is_actived_user(user.id)
    vietnam_time = datetime.utcnow() + timedelta(hours=7)
    timestamp_vietnam = vietnam_time.strftime('%H:%M:%S %d-%m-%Y')
    keyboard = ikb({"🚨  Mở chat  🚨": "https://t.me/boost?c=1707112470"})

    if not user_id:
        return await message.reply_text("Tôi không thể tìm thấy người dùng đó.")

    if user_id in [from_user.id, BOT_ID] or user_id in SUDOERS or user_id in (await list_admins(message.chat.id)):
        return await message.reply_text(f"Mod mỏ hỗn {user.mention} đã bị khóa mõm.")
    
    if is_fmuted:
        muted = await message.reply_text(f"**Người có id {user_id} đã bị cấm chat và đang đợi admin xác nhận .**")
        await asyncio.sleep(10)
        await app.delete_messages(
            chat_id=message.chat.id,
            message_ids=muted.id,
            revoke=True,)
        return

    if is_actived:
        actived = await message.reply_text(f"**Người có id {user_id} đã được xác nhận.**")
        await asyncio.sleep(10)
        await app.delete_messages(
            chat_id=message.chat.id,
            message_ids=actived.id,
            revoke=True,)
        return 

    #await app.get_chat_member(chat_id, user_id)
    username1 = from_user.username
    username2 = user.username
    
    if not username1:
        return await message.reply_text("Vui lòng đặt username hoặc tag admin khác để check voice người này.")
        
    served_chats = await get_served_chats()
    m = await message.reply_text(
        f"**Đang cấm chat {user.mention} trên toàn hệ thống!**"
        + f" **Hành động này sẽ mất khoảng {len(served_chats)} giây.**"
    )
    await add_fmute_user(user_id)
    number_of_chats = 0
    for served_chat in served_chats:
        try:
            await app.restrict_chat_member(served_chat["chat_id"], user.id, permissions=ChatPermissions())
            number_of_chats += 1
            await asyncio.sleep(1)
        except FloodWait as e:
            await asyncio.sleep(int(e.value))
        except Exception:
            log.error(f"Lỗi khi cấm chat ở nhóm {served_chat['chat_id']}: {e}")
            pass
    try:
        await app.send_message(user.id, f"Xin chào {user.mention}, bạn đã bị cấm chat toàn hệ thống tại nhóm {message.chat.title} với lý do: {reason}, bạn hãy nhắn tin cho admin {from_user.mention} t.me/{username1} để mở chat.")
    except Exception:
        log.error(f"Lỗi khi nhắn tin đến {user.id}: {e}")
        pass
    #await app2.send_message(user.id, f"Xin chào, bạn đã bị cấm chat tại nhóm {message.chat.title} với lý do: {reason}, bạn hãy nhắn tin cho admin {from_user.mention} @{username1} để mở chat.")
    await m.edit(f"Đã cấm chat {user.mention} toàn hệ thống!")
    mute_text = f"""
__**Người dùng bị fmute toàn hệ thống **__
**Tại nhóm:** {message.chat.title} [`{message.chat.id}`]
**Quản trị viên:** {from_user.mention} @{username1}
**Người dùng bị cấm chat:** {user.mention} @{username2}
**ID người dùng bị cấm chat:** `{user_id}`
**Lý do:** __{reason}__
**Lúc:** __{timestamp_vietnam}__
**Số nhóm:** `{number_of_chats}`"""
    try:
        m2 = await app.send_message(
            FMUTE_LOG_GROUP_ID,
            text=mute_text,
            disable_web_page_preview=True,
        )
        lydo_text = f"""
**🔥Người dùng {user.mention} @{username2} đã bị đeo rọ mõm 👙.**
**Bởi: {from_user.mention} @{username1}.**
**Lý do: __{reason}__.**"""
        await m.edit(
            text=lydo_text,
            reply_markup=keyboard,
        )
    except Exception:
        await message.reply_text(
            "Người dùng bị cấm chat, nhưng hành động cấm chat này không được ghi lại, hãy thêm tôi vào nhóm quản lý"
        )
    #if message.reply_to_message:
        #await message.reply_to_message.delete()


# Fmute check voice


@app.on_message(filters.command("m") & ~filters.private)
@adminsOnly("can_restrict_members")
@capture_err
async def mute_globally(_, message: Message):
    await refresh_admin_cache(message.chat.id)

    link2 = f"tg://openmessage?user_id="
    link = f"t.me/"
    user_id, reason = await extract_user_and_reason(message)
    chat_id = message.chat.id
    #await app.get_chat_member(chat_id, user_id)
    user = await app.get_users(user_id)
    from_user = message.from_user
    is_fmuted = await is_fmuted_user(user.id)
    is_actived = await is_actived_user(user.id)
    vietnam_time = datetime.utcnow() + timedelta(hours=7)
    timestamp_vietnam = vietnam_time.strftime('%H:%M:%S %d-%m-%Y')
    

    if not user_id:
        return await message.reply_text("Tôi không thể tìm thấy người dùng đó.")

    if user_id in [from_user.id, BOT_ID] or user_id in SUDOERS or user_id in (await list_admins(message.chat.id)):
        return await message.reply_text(f"Mod mỏ hỗn {user.mention} đã bị khóa mõm.")
    
    if is_fmuted:
        fmuted = await message.reply_text(f"**Người có id {user_id} đã bị cấm chat và đang đợi admin xác nhận .**")
        await asyncio.sleep(10)
        await app.delete_messages(
            chat_id=message.chat.id,
            message_ids=fmuted.id,
            revoke=True,)
        return 

    if is_actived:
        actived = await message.reply_text(f"**Người có id {user_id} đã được xác nhận.**")
        await asyncio.sleep(10)
        await app.delete_messages(
            chat_id=message.chat.id,
            message_ids=actived.id,
            revoke=True,)
        return 

    
    username1 = from_user.username
    username2 = user.username   
    if not username1:
        return await message.reply_text("Vui lòng đặt username hoặc tag admin khác để check voice người này.")
        
    served_chats = await get_served_chats()
    m = await message.reply_text(
        f"**Đang cấm chat {user.mention} trên toàn hệ thống!**"
        + f" **Hành động này sẽ mất khoảng {len(served_chats)} giây.**"
    )
    await add_fmute_user(user_id)
    number_of_chats = 0
    for served_chat in served_chats:
        try:
            await app.restrict_chat_member(served_chat["chat_id"], user.id, permissions=ChatPermissions())
            number_of_chats += 1
            await asyncio.sleep(1)
        except FloodWait as e:
            await asyncio.sleep(int(e.value))
        except Exception:
            log.error(f"Lỗi khi cấm chat ở nhóm {served_chat['chat_id']}: {e}")
            pass

    try:
        await app.send_message(
            user.id,
            f"Xin chào {user.mention}, Bạn đã bị cấm chat toàn hệ thống tại nhóm {message.chat.title}."
            f" Bạn hãy nhắn tin cho admin {reason or link + username1} để mở chat."
        )
    except Exception:
        log.error(f"Lỗi khi nhắn tin đến {user.id}: {e}")
        pass
    
    
    await m.edit(f"Đã cấm chat {user.mention} toàn hệ thống!")
    mute_text = f"""
__**Người dùng bị cấm chat toàn hệ thống**__
**Tại nhóm:** {message.chat.title} [`{message.chat.id}`]
**Quản trị viên:** {from_user.mention} @{username1}
**Người dùng bị cấm chat:** {user.mention} @{username2}
**ID người dùng bị cấm chat:** `{user_id}`
**Lý do (admin check):** __{reason}__
**Lúc:** __{timestamp_vietnam}__
**Số nhóm:** `{number_of_chats}`"""
    try:
        m2 = await app.send_message(
            FMUTE_LOG_GROUP_ID,
            text=mute_text,
            disable_web_page_preview=True,
        )
        await m.edit(
f"""**🔥Người dùng [{user.mention}](tg://openmessage?user_id={user_id})  @{username2} đã bị 🚫cấm chat tất cả nhóm trong hệ thống.**
**Bởi: [{from_user.mention}](tg://openmessage?user_id={from_user.id})  @{username1}.**
**Lý do: Gửi voice cho {reason or link + username1} để được mở chat  💬💬💬.**""")
            #f"""**Đã cấm chat {user.mention} @{username2} trên toàn hệ thống!!!\n Gửi voice cho {reason or from_user.mention}  để được mỡ chat  💬💬💬**""",
    except Exception:
        await message.reply_text(
            "Người dùng bị cấm chat, nhưng hành động cấm chat này không được ghi lại, hãy thêm tôi vào nhóm quản lý"
        )
    #if message.reply_to_message:
        #await message.reply_to_message.delete()


#sfmute

@app.on_message(filters.command("sm") & ~filters.private)
@adminsOnly("can_restrict_members")
@capture_err
async def mute_globally(_, message: Message):
    await refresh_admin_cache(message.chat.id)

    user_id, reason = await extract_user_and_reason(message)
    chat_id = message.chat.id
    await app.get_chat_member(chat_id, user_id)
    #user = await app.get_users(user_id)
    from_user = message.from_user
    is_fmuted = await is_fmuted_user(user.id)
    is_actived = await is_actived_user(user.id)
    vietnam_time = datetime.utcnow() + timedelta(hours=7)
    timestamp_vietnam = vietnam_time.strftime('%H:%M:%S %d-%m-%Y')

    if not user_id:
        return await message.reply_text("Tôi không thể tìm thấy người dùng đó.")

    if user_id in [from_user.id, BOT_ID] or user_id in SUDOERS:
        return await message.reply_text("Tôi không thể cấm chat người dùng đó.")
    
    if is_fmuted:
        fmuted = await message.reply_text(f"**Người này id {user_id} đã bị cấm chat và đang đợi admin xác nhận .**")
        await asyncio.sleep(10)
        await app.delete_messages(
            chat_id=message.chat.id,
            message_ids=fmuted.id,
            revoke=True,)
        return 
        
    if is_actived:
        actived = await message.reply_text(f"**Người này id {user_id} đã được xác nhận.**")
        await asyncio.sleep(10)
        await app.delete_messages(
            chat_id=message.chat.id,
            message_ids=actived.id,
            revoke=True,)
        return 

    user = await app.get_users(user_id)  
    served_chats = await get_served_chats()
    await add_fmute_user(user_id)
    number_of_chats = 0
    for served_chat in served_chats:
        try:
            await app.restrict_chat_member(served_chat["chat_id"], user.id, permissions=ChatPermissions())
            number_of_chats += 1
            await asyncio.sleep(1)
        except FloodWait as e:
            await asyncio.sleep(int(e.value))
        except Exception:
            log.error(f"Lỗi khi cấm chat ở nhóm {served_chat['chat_id']}: {e}")
            pass
        
    
    mute_text = f"""
__**Người dùng bị cấm chat toàn hệ thống bằng chế độ im lặng**__
**Tại nhóm :** {message.chat.title} [`{message.chat.id}`]
**Quản trị viên:** {from_user.mention} @{from_user.username}
**Người dùng bị cấm chat:** {user.mention} @{user.username}
**ID người dùng bị cấm chat:** `{user_id}`
**Lý do:** __{reason}__
**Lúc:** __{timestamp_vietnam}__
**Số nhóm:** `{number_of_chats}`"""
    try:
        m2 = await app.send_message(
            FMUTE_LOG_GROUP_ID,
            text=mute_text,
            disable_web_page_preview=True,
        )
    except Exception:
        log.error(f"Lỗi khi gửi tin nhắn đến nhóm log {FMUTE_LOG_GROUP_ID}: {e}")
        pass

    #if message.reply_to_message:
        #await message.reply_to_message.delete()


#out
@app.on_message(filters.command("out") & ~filters.private)
#@adminsOnly("can_restrict_members")
async def out(_, message: Message):
    user_id = await extract_user(message)
    if not user_id:
        return await message.reply_text("Tôi không thể tìm thấy người dùng đó.")
    #await message.chat.unban_member(user_id)
    umention = (await app.get_users(user_id)).mention
    await message.reply_text(f"{umention} đã rời khỏi nhóm")

# Unfmute


@app.on_message(filters.command("um") & ~filters.private)
@adminsOnly("can_restrict_members")
@capture_err
async def unmute_globally(_, message: Message):
    await refresh_admin_cache(message.chat.id)

    user_id, reason = await extract_user_and_reason(message)
    chat_id = message.chat.id
    from_user = message.from_user
    vietnam_time = datetime.utcnow() + timedelta(hours=7)
    timestamp_vietnam = vietnam_time.strftime('%H:%M:%S %d-%m-%Y')
    await app.get_chat_member(chat_id, user_id)
    if not user_id:
        return await message.reply_text("Tôi không thể tìm thấy người dùng đó.")
    user = await app.get_users(user_id)

    is_fmuted = await is_fmuted_user(user.id)
    if not is_fmuted:
        await message.reply_text("Tôi không nhớ đã cấm chat họ.")
    else:
        #await remove_fmute_user(user.id)
        #await message.chat.unban_member(user_id)
        #await message.reply_text(f"{user.mention} unmuted.'")
        served_chats = await get_served_chats()
        m = await message.reply_text(
            f"**Đang xác nhận {user.mention} trong hệ thống!**"
            + f" **Hành động này sẽ mất khoảng {len(served_chats)} giây.**"
        )
        await add_active_user(user.id)
        await remove_fmute_user(user.id)
        number_of_chats = 0
        for served_chat in served_chats:
            try:
                await app.unban_chat_member(served_chat["chat_id"], user.id)
                number_of_chats += 1
                await asyncio.sleep(1)
            except FloodWait as e:
                await asyncio.sleep(int(e.value))
            except Exception:
                FMUTE_LOG_GROUP_ID
                log.error(f"Lỗi khi cấm chat ở nhóm {served_chat['chat_id']}: {e}")
                pass
        try:
            await app.send_message(
                user.id,
                f"Xin chào {user.mention}, Bạn đã được {from_user.mention} t.me/{from_user.username} bỏ cấm chat trên toàn hệ thống,"
                + " Hãy tham gia trò chuyện tại https://t.me/addlist/8LaQNjuIknljYmNh .",
            )
        except Exception:
            log.error(f"Lỗi khi nhắn tin đến {user.id}: {e}")
            pass
        await m.edit(f"Đã xác nhận {user.mention} trên toàn hệ thống!")
        mute_text = f"""
__**Người dùng được xác nhận**__
**Tại nhóm :** {message.chat.title} [`{message.chat.id}`]
**Quản trị viên:** {from_user.mention} @{from_user.username}
**Mở chat người dùng:** {user.mention} @{user.username}
**ID người dùng đã mở chat:** `{user_id}`
**Note:** __{reason or 'None.'}__
**Lúc:** __{timestamp_vietnam}__
**Số nhóm:** `{number_of_chats}`"""
        try:
            m2 = await app.send_message(
                FMUTE_LOG_GROUP_ID,
                text=mute_text,
                disable_web_page_preview=True,
            )
            m3 = await app.send_message(
                XAC_NHAN,
                text=mute_text,
                disable_web_page_preview=True,
            )
            await m.edit(
                f"Đã xác nhận {user.mention} trên toàn hệ thống!\n Bởi: {from_user.mention}",
                disable_web_page_preview=True,
            )
        except Exception:
            await message.reply_text(
                "Người dùng đã được xác nhận, nhưng hành động này không được ghi lại, hãy thêm tôi vào nhóm quản lý"
            )


#huyxacnhan
@app.on_message(filters.command("huy") & SUDOERS)
@adminsOnly("can_restrict_members")
@capture_err
async def huyxacnhan(_, message):
    await refresh_admin_cache(message.chat.id)

    user_id, reason = await extract_user_and_reason(message)
    from_user = message.from_user
    vietnam_time = datetime.utcnow() + timedelta(hours=7)
    timestamp_vietnam = vietnam_time.strftime('%H:%M:%S %d-%m-%Y')
    if not user_id:
        return await message.reply_text("Tôi không thể tìm thấy người dùng này.")
    user = await app.get_users(user_id)

    is_actived = await is_actived_user(user.id)
    if not is_actived:
        return await message.reply_text("Tôi không nhớ đã xác nhận người này trên hệ thống.")
    else:
        await remove_active_user(user.id)
        await message.reply_text(f"Đã huỷ xác nhận {user.mention}. ")
    await app.send_message(
                FMUTE_LOG_GROUP_ID,
                f"""
__**Người dùng đã bị hủy xác nhận**__
**Tại nhóm :** {message.chat.title} [`{message.chat.id}`]
**Quản trị viên:** {from_user.mention} @{from_user.username}
**Hủy xác nhận người dùng:** {user.mention} @{user.username}
**ID người dùng bị hủy xác nhận:** `{user_id}`
**Note:** __{reason or 'None.'}__
**Lúc:** __{timestamp_vietnam}__""",
                disable_web_page_preview=True,
            )
    await app.send_message(
                XAC_NHAN,
                f"""
__**Người dùng đã bị hủy xác nhận**__
**Tại nhóm :** {message.chat.title} [`{message.chat.id}`]
**Quản trị viên:** {from_user.mention} @{from_user.username}
**Hủy xác nhận người dùng:** {user.mention} @{user.username}
**ID người dùng bị hủy xác nhận:** `{user_id}`
**Note:** __{reason or 'None.'}__
**Lúc:** __{timestamp_vietnam}__""",
                disable_web_page_preview=True,
    )

#check
@app.on_message(filters.command("check") & ~filters.private)
#@adminsOnly("can_restrict_members")
#@capture_err
async def check(_, message: Message):
    user_id = await extract_user(message)
    from_user = message.from_user
    if not user_id:
        return await message.reply_text("Tôi không thể tìm thấy người dùng đó.")
    user = await app.get_users(user_id)

    is_fmuted = await is_fmuted_user(user.id)
    #if not is_fmuted:
    #   await message.reply_text("Người này chưa được xác nhận.")

    if is_fmuted:
        return await message.reply_text("Người này đã bị cấm chat và đang đợi admin xác nhận .")

    is_actived = await is_actived_user(user.id)
    if is_actived:
        return await message.reply_text("Người này đã được xác nhận.")

    else:
        await message.reply_text("Người này chưa được xác nhận.")


#checkidol
@app.on_message(filters.command("idol") & ~filters.private)
#@adminsOnly("can_restrict_members")
#@capture_err
async def check(_, message: Message):
    user_id = await extract_user(message)
    from_user = message.from_user
    if not user_id:
        return await message.reply_text("Tôi không thể tìm thấy người dùng đó.")
    user = await app.get_users(user_id)

    is_fmuted = await is_fmuted_user(user.id)
    #if not is_fmuted:
    #   await message.reply_text("Người này chưa được xác nhận.")

    if is_fmuted:
        return await message.reply_text("Người này đã bị cấm chat và đang đợi admin check .")

    is_actived = await is_actived_user(user.id)
    if is_actived:
        return await message.reply_text(f"**{user.mention} UY TÍN đã được admin check. ID {user_id}.**")

    else:
        await message.reply_text(f"{user.mention} chưa được admin check. ID {user_id}.")


#xacnhan
@app.on_message(filters.command("xacnhan") & SUDOERS)
@adminsOnly("can_restrict_members")
#@capture_err
async def xacnhan(_, message):
    await refresh_admin_cache(message.chat.id)

    user_id, reason = await extract_user_and_reason(message)
    from_user = message.from_user
    if not user_id:
        return await message.reply_text("Tôi không thể tìm thấy người dùng này.")
    user = await app.get_users(user_id)

    is_fmuted = await is_fmuted_user(user.id)
    if is_fmuted:
        return await message.reply_text("Người này đã bị cấm chat và đang đợi xác nhận.")

    is_actived = await is_actived_user(user.id)
    if is_actived:
        return await message.reply_text("Người này đã được xác nhận, không cần xác nhận lại.")
    else:
        await add_active_user(user.id)
        #await remove_active_user(user.id)
        await message.reply_text(f"Đã xác nhận {user.mention}. ")
    await app.send_message(
                FMUTE_LOG_GROUP_ID,
                f"""
__**Người dùng được xác nhận bằng lệnh**__
**Tại nhóm :** {message.chat.title} [`{message.chat.id}`]
**Quản trị viên:** {from_user.mention}
**Xác nhận người dùng:** {user.mention}
**ID người dùng được xác nhận:** `{user_id}`
**Note:** __{reason or 'None.'}__""",
                disable_web_page_preview=True,
            )
    await app.send_message(
                XAC_NHAN,
                f"""
__**Người dùng được xác nhận bằng lệnh**__
**Tại nhóm :** {message.chat.title} [`{message.chat.id}`]
**Quản trị viên:** {from_user.mention}
**Xác nhận người dùng:** {user.mention}
**ID người dùng được xác nhận:** `{user_id}`
**Note:** __{reason or 'None.'}__""",
                disable_web_page_preview=True,
    )
'''
#########################################

async def mute_user_globally(
    message: Message,
    user_id: int,
    reason: str,
    mode: str = "default"#, "silent", "check"
):
    from_user = message.from_user
    chat_id = message.chat.id
    user = await app.get_users(user_id)
    is_fmuted = await is_fmuted_user(user.id)
    is_actived = await is_actived_user(user.id)
    vietnam_time = datetime.utcnow() + timedelta(hours=7)
    timestamp_vietnam = vietnam_time.strftime('%H:%M:%S %d-%m-%Y')
    keyboard = ikb({"🚨  Mở chat  🚨": "https://t.me/boost?c=1707112470"})

    if user_id in [from_user.id, BOT_ID] or user.id in SUDOERS or user.id in (await list_admins(chat_id)):
        return await message.reply_text("Không thể cấm chat người này.")

    if is_fmuted:
        return await message.reply_text("Người này đã bị cấm chat.")
    
    if is_actived:
        return await message.reply_text("Người này đã được xác nhận.")

    await add_fmute_user(user.id)

    served_chats = await get_served_chats()
    m = await message.reply_text(
        f"**Đang cấm chat {user.mention} toàn hệ thống...**"
        + f" **Tổng nhóm: {len(served_chats)}.**"
    )

    number_of_chats = 0
    for sc in served_chats:
        try:
            await app.restrict_chat_member(sc["chat_id"], user.id, ChatPermissions())
            number_of_chats += 1
            await asyncio.sleep(1)
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception:
            pass

    # Gửi tin nhắn cá nhân nếu mode phù hợp
    if mode != "silent":
        try:
            await app.send_message(
                user.id,
                f"Bạn đã bị cấm chat toàn hệ thống tại nhóm {message.chat.title}."
                + (f"\nLý do: {reason}" if reason else "")
                + f"\nHãy liên hệ {from_user.mention} để được mở."
            )
        except Exception:
            pass

    mute_log = f"""
__**Cấm chat toàn hệ thống**__
**Nhóm:** {message.chat.title} [`{message.chat.id}`]
**Quản trị viên:** {from_user.mention}
**Người dùng:** {user.mention} @{user.username}
**ID:** `{user.id}`
**Lý do:** {reason or "Không có"}
**Lúc:** {timestamp_vietnam}
**Số nhóm:** {number_of_chats}"""

    await app.send_message(FMUTE_LOG_GROUP_ID, mute_log, disable_web_page_preview=True)
    await m.edit(
        f"🔥 {user.mention} đã bị cấm chat trên **{number_of_chats}** nhóm.",
        reply_markup=keyboard,
    )

#fm
@app.on_message(filters.command("fm") & ~filters.private)
@adminsOnly("can_restrict_members")
async def fm_command(_, message: Message):
    await refresh_admin_cache(message.chat.id)

    user_id, reason = await extract_user_and_reason(message)
    await mute_user_globally(message, user_id, reason, mode="default")

#sm
@app.on_message(filters.command("sm") & ~filters.private)
@adminsOnly("can_restrict_members")
async def sm_command(_, message: Message):
    await refresh_admin_cache(message.chat.id)

    user_id, reason = await extract_user_and_reason(message)
    await mute_user_globally(message, user_id, reason, mode="silent")

#m
@app.on_message(filters.command("m") & ~filters.private)
@adminsOnly("can_restrict_members")
async def m_command(_, message: Message):
    await refresh_admin_cache(message.chat.id)

    user_id, reason = await extract_user_and_reason(message)
    await mute_user_globally(message, user_id, reason, mode="check")




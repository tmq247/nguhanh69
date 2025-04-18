
"""
MIT License

Copyright (c) 2024 TheHamkerCat

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
import requests
from sample_config import BOT_TOKEN
from re import findall
from datetime import datetime, timedelta
from random import shuffle

from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors.exceptions.bad_request_400 import (
    ChatAdminRequired,
    UserNotParticipant,
)
from pyrogram.enums import ChatMemberStatus as CMS
from pyrogram.types import (
    Chat,
    ChatPermissions,
    ChatMemberUpdated,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    User,
)

from wbb import BOT_USERNAME, SUDOERS, WELCOME_DELAY_KICK_SEC, app
from wbb.core.decorators.errors import capture_err
from wbb.core.decorators.permissions import adminsOnly
from wbb.core.keyboard import ikb
from wbb.modules.notes import extract_urls
#from wbb.utils.dbfeds import check_banned_user#, get_fed_id
from wbb.utils.dbfunctions import (
    captcha_off,
    captcha_on,
    del_welcome,
    get_captcha_cache,
    get_welcome,
    has_solved_captcha_once,
    is_captcha_on,
    is_gbanned_user,
    save_captcha_solved,
    set_welcome,
    update_captcha_cache,
)
from wbb.utils.filter_groups import welcome_captcha_group
from wbb.utils.functions import (
    check_format,
    extract_text_and_keyb,
    generate_captcha,
)

__MODULE__ = "Greetings"
__HELP__ = """
/captcha [ENABLE|DISABLE] - Enable/Disable captcha.

/set_welcome - Trả lời tin nhắn này có nội dung chính xác
định dạng cho tin nhắn chào mừng, hãy kiểm tra phần cuối của tin nhắn này.

/del_welcome - Xóa tin nhắn chào mừng.
/get_welcome - Xem tin nhắn chào mừng đã được đặt.

**SET_WELCOME ->**

**Để đặt ảnh hoặc gif làm tin nhắn chào mừng. Thêm thông điệp chào mừng của bạn dưới dạng chú thích cho ảnh hoặc gif. Chú thích có định dạng dưới đây.**

Đối với tin nhắn chào mừng bằng văn bản, chỉ cần gửi văn bản. Sau đó trả lời bằng lệnh 

Định dạng phải giống như dưới đây.

```
**Hi** {name} [{id}] Welcome to {chat}

~ #Dấu phân cách này (~) phải ở giữa văn bản và nút, cũng xóa nhận xét này

button=[Duck, https://duckduckgo.com]
button2=[Github, https://github.com]
```

**NOTES ->**

Kiểm tra /markdownhelp để biết thêm về định dạng và cú pháp khác.
"""

answers_dicc = []
loop = asyncio.get_running_loop()


async def get_initial_captcha_cache():
    global answers_dicc
    answers_dicc = await get_captcha_cache()
    return answers_dicc


loop.create_task(get_initial_captcha_cache())


async def handle_new_member(member, chat):
    global answers_dicc

    # Get cached answers from mongodb in case of bot's been restarted or crashed.
    answers_dicc = await get_captcha_cache()

    # Mute new member and send message with button
    try:
        if member.id in SUDOERS:
            return  # Ignore sudo users
        if await is_gbanned_user(member.id):
            await chat.ban_member(member.id)
            await app.send_message(
                chat.id,
                f"{member.mention} đã bị cấm trên toàn cầu và đã bị xóa,"
                + " nếu bạn cho rằng đây là gban giả, bạn có thể khiếu nại"
                + " ib cho admin nhóm hỗ trợ.",
            )
            return
        if member.is_bot:
            return  # Ignore bots
        if not await is_captcha_on(chat.id):
            return await send_welcome_message(
                chat, member.id
            )

        # Ignore user if he has already solved captcha in this group
        # someday
        if await has_solved_captcha_once(chat.id, member.id):
            return

        await chat.restrict_member(member.id, ChatPermissions())
        text = (
            f"{(member.mention())} Are you human?\n"
            f"Giải mã xác thực này trong {WELCOME_DELAY_KICK_SEC} "
            "giây và 4 lần thử nếu không bạn sẽ bị đá."
        )
    except ChatAdminRequired:
        return

    # Generate a captcha image, answers, and some wrong answers
    captcha = generate_captcha()
    captcha_image = captcha[0]
    captcha_answer = captcha[1]
    wrong_answers = captcha[2]  # This consists of 8 wrong answers
    correct_button = InlineKeyboardButton(
        f"{captcha_answer}",
        callback_data=f"pressed_button {captcha_answer} {member.id}",
    )
    temp_keyboard_1 = [correct_button]  # Button row 1
    temp_keyboard_2 = []  # Botton row 2
    temp_keyboard_3 = []
    for i in range(2):
        temp_keyboard_1.append(
            InlineKeyboardButton(
                f"{wrong_answers[i]}",
                callback_data=f"pressed_button {wrong_answers[i]} {member.id}",
            )
        )
    for i in range(2, 5):
        temp_keyboard_2.append(
            InlineKeyboardButton(
                f"{wrong_answers[i]}",
                callback_data=f"pressed_button {wrong_answers[i]} {member.id}",
            )
        )
    for i in range(5, 8):
        temp_keyboard_3.append(
            InlineKeyboardButton(
                f"{wrong_answers[i]}",
                callback_data=f"pressed_button {wrong_answers[i]} {member.id}",
            )
        )

    shuffle(temp_keyboard_1)
    keyboard = [temp_keyboard_1, temp_keyboard_2, temp_keyboard_3]
    shuffle(keyboard)
    verification_data = {
        "chat_id": chat.id,
        "user_id": member.id,
        "answer": captcha_answer,
        "keyboard": keyboard,
        "attempts": 0,
    }
    keyboard = InlineKeyboardMarkup(keyboard)
    # Append user info, correct answer, and
    answers_dicc.append(verification_data)
    # keyboard for later use with callback query
    button_message = await app.send_photo(
        chat_id=chat.id,
        photo=captcha_image,
        caption=text,
        reply_markup=keyboard,
    )
    os.remove(captcha_image)

    # Save captcha answers etc in mongodb in case the bot gets crashed or restarted.
    await update_captcha_cache(answers_dicc)

    asyncio.create_task(
        kick_restricted_after_delay(
            WELCOME_DELAY_KICK_SEC, button_message, member
        )
    )
    await asyncio.sleep(0.5)



@app.on_chat_member_updated(filters.group, group=welcome_captcha_group)
@capture_err
async def welcome(_, user: ChatMemberUpdated):
    if not (
        user.new_chat_member
        and user.new_chat_member.status not in {CMS.RESTRICTED, CMS.BANNED}
        and not user.old_chat_member
    ):
        return

    member = user.new_chat_member.user if user.new_chat_member else user.from_user
    chat = user.chat
    return await handle_new_member(member, chat)


async def send_welcome_message(chat: Chat, user_id: int, delete: bool = False):
    welcome, raw_text, file_id = await get_welcome(chat.id)

    if not raw_text:
        return
    text = raw_text
    keyb = None
    if findall(r"\[.+\,.+\]", raw_text):
        text, keyb = extract_text_and_keyb(ikb, raw_text)

    if "{chat}" in text:
        text = text.replace("{chat}", chat.title)
    if "{name}" in text:
        text = text.replace("{name}", (await app.get_users(user_id)).mention)
    if "{username}" in text:
        text = text.replace("{username}", (await app.get_users(user_id)).username)
    if "{id}" in text:
        text = text.replace("{id}", f"`{user_id}`")

    async def _send_wait_delete():
        if welcome == "Text":
            m = await app.send_message(
                chat.id,
                text=text,
                reply_markup=keyb,
                disable_web_page_preview=True,
            )
        elif welcome == "Photo":
            m = await app.send_photo(
                chat.id,
                photo=file_id,
                caption=text,
                reply_markup=keyb,
            )
        elif welcome == "Video":
            m = await app.send_video(
                chat.id,
                video=file_id,
                caption=text,
                reply_markup=keyb,
            )
        else:
            m = await app.send_animation(
                chat.id,
                animation=file_id,
                caption=text,
                reply_markup=keyb,
            )
        await asyncio.sleep(300)
        await m.delete()

    asyncio.create_task(_send_wait_delete())








@app.on_callback_query(filters.regex("pressed_button"))
async def callback_query_welcome_button(_, callback_query):
    """After the new member presses the correct button,
    set his permissions to chat permissions,
    delete button message and join message.
    """
    global answers_dicc
    data = callback_query.data
    pressed_user_id = callback_query.from_user.id
    pending_user_id = int(data.split(None, 2)[2])
    button_message = callback_query.message
    answer = data.split(None, 2)[1]

    correct_answer = None
    keyboard = None

    if len(answers_dicc) != 0:
        for i in answers_dicc:
            if (
                i["user_id"] == pending_user_id
                and i["chat_id"] == button_message.chat.id
            ):
                correct_answer = i["answer"]
                keyboard = i["keyboard"]

    if not (correct_answer and keyboard):
        return await callback_query.answer(
            "Đã xảy ra lỗi, hãy tham gia lại " "trò chuyện!"
        )

    if pending_user_id != pressed_user_id:
        return await callback_query.answer("Điều này không dành cho bạn")

    if answer != correct_answer:
        await callback_query.answer("Ừ, sai rồi.")
        for iii in answers_dicc:
            if (
                iii["user_id"] == pending_user_id
                and iii["chat_id"] == button_message.chat.id
            ):
                attempts = iii["attempts"]
                if attempts >= 3:
                    answers_dicc.remove(iii)
                    await button_message.chat.ban_member(pending_user_id)
                    await asyncio.sleep(1)
                    await button_message.chat.unban_member(pending_user_id)
                    await button_message.delete()
                    return await update_captcha_cache(answers_dicc)

                iii["attempts"] += 1
                break

        shuffle(keyboard[0])
        shuffle(keyboard[1])
        shuffle(keyboard[2])
        shuffle(keyboard)
        keyboard = InlineKeyboardMarkup(keyboard)
        return await button_message.edit(
            text=button_message.caption.markdown,
            reply_markup=keyboard,
        )

    await callback_query.answer("Captcha đã được chuyển thành công!")
    await button_message.chat.unban_member(pending_user_id)
    await button_message.delete()

    if len(answers_dicc) != 0:
        for ii in answers_dicc:
            if (
                ii["user_id"] == pending_user_id
                and ii["chat_id"] == button_message.chat.id
            ):
                answers_dicc.remove(ii)
                await update_captcha_cache(answers_dicc)

    chat = callback_query.message.chat

    # Save this verification in db, so we don't have to
    # send captcha to this user when he joins again.
    await save_captcha_solved(chat.id, pending_user_id)

    return await send_welcome_message(chat, pending_user_id, True)


async def kick_restricted_after_delay(
    delay, button_message: Message, user: User
):
    """If the new member is still restricted after the delay, delete
    button message and join message and then kick him
    """
    global answers_dicc
    await asyncio.sleep(delay)
    group_chat = button_message.chat
    user_id = user.id
    await button_message.delete()
    if len(answers_dicc) != 0:
        for i in answers_dicc:
            if i["user_id"] == user_id:
                answers_dicc.remove(i)
                await update_captcha_cache(answers_dicc)
    await _ban_restricted_user_until_date(group_chat, user_id, duration=delay)


async def _ban_restricted_user_until_date(
    group_chat, user_id: int, duration: int
):
    try:
        member = await group_chat.get_member(user_id)
        if member.status == ChatMemberStatus.RESTRICTED:
            until_date = (datetime.now() + timedelta(seconds=duration))
            await group_chat.ban_member(user_id, until_date=until_date)
    except UserNotParticipant:
        pass


@app.on_message(filters.command("captcha") & ~filters.private)
@adminsOnly("can_restrict_members")
async def captcha_state(_, message):
    usage = "**Usage:**\n/captcha [ENABLE|DISABLE]"
    if len(message.command) != 2:
        return await message.reply_text(usage)

    chat_id = message.chat.id
    state = message.text.split(None, 1)[1].strip()
    state = state.lower()
    if state == "enable":
        await captcha_on(chat_id)
        await message.reply_text("Đã bật Captcha cho người dùng mới.")
    elif state == "disable":
        await captcha_off(chat_id)
        await message.reply_text("Captcha bị vô hiệu hóa cho người dùng mới.")
    else:
        await message.reply_text(usage)


# WELCOME MESSAGE


@app.on_message(filters.command("set_welcome") & ~filters.private)
@adminsOnly("can_change_info")
async def set_welcome_func(_, message):
    usage = "Bạn cần trả lời một văn bản, ảnh gif hoặc ảnh để đặt ảnh đó làm lời chào.\n\nLưu ý: cần có chú thích cho ảnh gif và ảnh."
    key = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="Trợ giúp thêm",
                    url=f"t.me/{BOT_USERNAME}?start=help_greetings",
                )
            ],
        ]
    )
    replied_message = message.reply_to_message
    chat_id = message.chat.id
    try:
        if not replied_message:
            await message.reply_text(usage, reply_markup=key)
            return
        if replied_message.animation:
            welcome = "Animation"
            file_id = replied_message.animation.file_id
            text = replied_message.caption
            if not text:
                return await message.reply_text(usage, reply_markup=key)
            raw_text = text.markdown
        if replied_message.photo:
            welcome = "Photo"
            file_id = replied_message.photo.file_id
            text = replied_message.caption
            if not text:
                return await message.reply_text(usage, reply_markup=key)
            raw_text = text.markdown
        if replied_message.video:
            welcome = "Video"
            file_id = replied_message.video.file_id
            text = replied_message.caption
            if not text:
                return await message.reply_text(usage, reply_markup=key)
            raw_text = text.markdown
        if replied_message.text:
            welcome = "Text"
            file_id = None
            text = replied_message.text
            raw_text = text.markdown
        if replied_message.reply_markup and not findall(r"\[.+\,.+\]", raw_text):
            urls = extract_urls(replied_message.reply_markup)
            if urls:
                response = "\n".join(
                    [f"{name}=[{text}, {url}]" for name, text, url in urls]
                )
                raw_text = raw_text + response
        raw_text = await check_format(ikb, raw_text)
        if raw_text:
            await set_welcome(chat_id, welcome, raw_text, file_id)
            return await message.reply_text(
                "Thông báo chào mừng đã được đặt thành công."
            )
        else:
            return await message.reply_text(
                "Định dạng sai, hãy kiểm tra phần trợ giúp.\n\n**Usage:**\nText: `Text`\nText + Buttons: `Text ~ Buttons`",
                reply_markup=key,
            )
    except UnboundLocalError:
        return await message.reply_text(
            "**Chỉ hỗ trợ tin nhắn chào mừng bằng Văn bản, Video, Gif và Hình ảnh.**"
        )


@app.on_message(filters.command("del_welcome") & ~filters.private)
@adminsOnly("can_change_info")
async def del_welcome_func(_, message):
    chat_id = message.chat.id
    await del_welcome(chat_id)
    await message.reply_text("Tin nhắn chào mừng đã bị xóa.")


@app.on_message(filters.command("get_welcome") & ~filters.private)
@adminsOnly("can_change_info")
async def get_welcome_func(_, message):
    chat = message.chat
    welcome, raw_text, file_id = await get_welcome(chat.id)
    if not raw_text:
        return await message.reply_text("Không có tin nhắn chào mừng nào được đặt.")
    if not message.from_user:
        return await message.reply_text(
            "Bạn đang ẩn danh, không thể gửi tin nhắn chào mừng."
        )

    await send_welcome_message(chat, message.from_user.id)

    await message.reply_text(
        f'Welcome: {welcome}\n\nFile_id: `{file_id}`\n\n`{raw_text.replace("`", "")}`'
    )

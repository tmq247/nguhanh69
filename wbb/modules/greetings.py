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
from wbb.utils.dbfeds import check_banned_user#, get_fed_id
from wbb.utils.dbfunctions import (
    #captcha_off,
    #captcha_on,
    del_welcome,
    #get_captcha_cache,
    get_welcome,
    #has_solved_captcha_once,
    #is_captcha_on,
    is_gbanned_user,
    #save_captcha_solved,
    set_welcome,
    #update_captcha_cache,
)
#from wbb.utils.filter_groups import welcome_captcha_group
from wbb.utils.functions import (
    check_format,
    extract_text_and_keyb,
    #generate_captcha,
)

__MODULE__ = "Greetings"
__HELP__ = """
/captcha [ENABLE|DISABLE] - Enable/Disable captcha.

/set_welcome - Reply this to a message containing correct
format for a welcome message, check end of this message.

/del_welcome - Delete the welcome message.
/get_welcome - Get the welcome message.

**SET_WELCOME ->**

**To set a photo or gif as welcome message. Add your welcome message as caption to the photo or gif. The caption muse be in the format given below.**

For text welcome message just send the text. Then reply with the command 

The format should be something like below.

```
**Hi** {name} [{id}] Welcome to {chat}

~ #This separater (~) should be there between text and buttons, remove this comment also

button=[Duck, https://duckduckgo.com]
button2=[Github, https://github.com]
```

**NOTES ->**

Checkout /markdownhelp to know more about formattings and other syntax.
"""







async def handle_new_member(member, chat):
    

    # Mute new member and send message with button
    try:
        if member.id in SUDOERS:
            return  # Ignore sudo users
        
        if await is_gbanned_user(member.id):
            await chat.ban_member(member.id)
            await app.send_message(
                chat.id,
                f"{member.mention} was globally banned, and got removed,"
                + " if you think this is a false gban, you can appeal"
                + " for this ban in support chat.",
            )
            return
        if member.is_bot:
            return  # Ignore bots
        

        # Ignore user if he has already solved captcha in this group
        # someday
        

        
    except ChatAdminRequired:
        return

    # Generate a captcha image, answers, and some wrong answers
    


@app.on_chat_member_updated(filters.group)
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




# WELCOME MESSAGE


@app.on_message(filters.command("set_welcome") & ~filters.private)
@adminsOnly("can_change_info")
async def set_welcome_func(_, message):
    usage = "You need to reply to a text, gif or photo to set it as greetings.\n\nNotes: caption required for gif and photo."
    key = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="More Help",
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
                "Welcome message has been successfully set."
            )
        else:
            return await message.reply_text(
                "Wrong formatting, check the help section.\n\n**Usage:**\nText: `Text`\nText + Buttons: `Text ~ Buttons`",
                reply_markup=key,
            )
    except UnboundLocalError:
        return await message.reply_text(
            "**Only Text, Gif and Photo welcome message are supported.**"
        )


@app.on_message(filters.command("del_welcome") & ~filters.private)
@adminsOnly("can_change_info")
async def del_welcome_func(_, message):
    chat_id = message.chat.id
    await del_welcome(chat_id)
    await message.reply_text("Welcome message has been deleted.")


@app.on_message(filters.command("get_welcome") & ~filters.private)
@adminsOnly("can_change_info")
async def get_welcome_func(_, message):
    chat = message.chat
    welcome, raw_text, file_id = await get_welcome(chat.id)
    if not raw_text:
        return await message.reply_text("No welcome message set.")
    if not message.from_user:
        return await message.reply_text(
            "You're anon, can't send welcome message."
        )

    await send_welcome_message(chat, message.from_user.id)

    await message.reply_text(
        f'Welcome: {welcome}\n\nFile_id: `{file_id}`\n\n`{raw_text.replace("`", "")}`'
            )

"""
MIT License
Copyright (c) 2024 TheHamkerCat
... (Giữ nguyên giấy phép)
"""
import asyncio
import time
from inspect import getfullargspec
from os import path
from pathlib import Path
import json

from aiohttp import ClientSession
from motor.motor_asyncio import AsyncIOMotorClient as MongoClient
from pymongo.errors import ConnectionFailure
from pyrogram import Client, filters
from pyrogram.types import Message
from pyromod import listen
from Python_ARQ import ARQ
from telegraph import Telegraph

is_config = path.exists("config.py")

if is_config:
    from config import *
else:
    from sample_config import *

Path("sessions").mkdir(exist_ok=True)

USERBOT_PREFIX = USERBOT_PREFIX
GBAN_LOG_GROUP_ID = GBAN_LOG_GROUP_ID
WELCOME_DELAY_KICK_SEC = WELCOME_DELAY_KICK_SEC
LOG_GROUP_ID = LOG_GROUP_ID
MESSAGE_DUMP_CHAT = MESSAGE_DUMP_CHAT
MONGO_URL = MONGO_URL
MOD_LOAD = []
MOD_NOLOAD = []
SUDOERS = filters.user()
bot_start_time = time.time()


class Log:
    def __init__(self, save_to_file=False, file_name="wbb.log"):
        self.save_to_file = save_to_file
        self.file_name = file_name

    def info(self, msg):
        print(f"[+]: {msg}")
        if self.save_to_file:
            with open(self.file_name, "a") as f:
                f.write(f"[INFO]({time.ctime(time.time())}): {msg}\n")

    def error(self, msg):
        print(f"[-]: {msg}")
        if self.save_to_file:
            with open(self.file_name, "a") as f:
                f.write(f"[ERROR]({time.ctime(time.time())}): {msg}\n")


log = Log(True, "bot.log")

# Hàm lưu dữ liệu vào tệp txt
def save_to_txt(data, filename="sudoers_backup.txt"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Hàm đọc dữ liệu từ tệp txt
def read_from_txt(filename="sudoers_backup.txt"):
    if path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sudo": "sudo", "sudoers": []}

# MongoDB client
log.info("Initializing MongoDB client")
mongo_client = MongoClient(MONGO_URL)
db = mongo_client.wbb


async def load_sudoers():
    global SUDOERS
    log.info("Loading sudoers")
    sudoersdb = db.sudoers
    try:
        # Kiểm tra kết nối MongoDB
        await mongo_client.admin.command("ping")
        log.info("Kết nối với MongoDB thành công!")

        # Tìm tài liệu sudoers
        sudoers_doc = await sudoersdb.find_one({"sudo": "sudo"})
        sudoers = sudoers_doc["sudoers"] if sudoers_doc else []

        # Thêm SUDO_USERS_ID từ config
        for user_id in SUDO_USERS_ID:
            SUDOERS.add(user_id)
            if user_id not in sudoers:
                sudoers.append(user_id)
                await sudoersdb.update_one(
                    {"sudo": "sudo"},
                    {"$set": {"sudoers": sudoers}},
                    upsert=True,
                )

        # Lưu vào tệp txt làm backup
        save_to_txt({"sudo": "sudo", "sudoers": sudoers})
        log.info(f"Đã tải sudoers từ MongoDB: {sudoers}")
        return sudoers

    except ConnectionFailure as e:
        log.error(f"Không thể kết nối với MongoDB: {e}")
        log.info("Chuyển sang sử dụng tệp txt...")
        # Dự phòng: Đọc từ tệp txt
        sudoers_doc = read_from_txt()
        sudoers = sudoers_doc["sudoers"]
        for user_id in SUDO_USERS_ID:
            SUDOERS.add(user_id)
            if user_id not in sudoers:
                sudoers.append(user_id)
                sudoers_doc["sudoers"] = sudoers
                save_to_txt(sudoers_doc)
        log.info(f"Đã tải sudoers từ tệp txt: {sudoers}")
        return sudoers
    finally:
        # Đóng kết nối MongoDB
        mongo_client.close()


# Khởi tạo bot và userbot
if not SESSION_STRING:
    app2 = Client(
        name="sessions/userbot",
        api_id=API_ID,
        api_hash=API_HASH,
        phone_number=PHONE_NUMBER,
    )
else:
    app2 = Client(
        name="sessions/userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING
    )

aiohttpsession = ClientSession()
arq = ARQ(ARQ_API_URL, ARQ_API_KEY, aiohttpsession)
app = Client("sessions/wbb", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

log.info("Starting bot client")
app.start()
log.info("Starting userbot client")
app2.start()

log.info("Gathering profile info")
x = app.get_me()
y = app2.get_me()

BOT_ID = x.id
BOT_NAME = x.first_name + (x.last_name or "")
BOT_USERNAME = x.username
BOT_MENTION = x.mention
BOT_DC_ID = x.dc_id

USERBOT_ID = y.id
USERBOT_NAME = y.first_name + (y.last_name or "")
USERBOT_USERNAME = y.username
USERBOT_MENTION = y.mention
USERBOT_DC_ID = y.dc_id

if USERBOT_ID not in SUDOERS:
    SUDOERS.add(USERBOT_ID)

log.info("Initializing Telegraph client")
telegraph = Telegraph(domain="graph.org")
telegraph.create_account(short_name=BOT_USERNAME)


async def eor(msg: Message, **kwargs):
    func = (
        (msg.edit_text if msg.from_user.is_self else msg.reply)
        if msg.from_user
        else msg.reply
    )
    spec = getfullargspec(func.__wrapped__).args
    return await func(**{k: v for k, v in kwargs.items() if k in spec})


# Chạy load_sudoers trong context bất đồng bộ
async def init_sudoers():
    await load_sudoers()

# Khởi động chương trình
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    if loop.is_running():
        log.error("Event loop đã chạy, sử dụng coroutine trực tiếp")
        asyncio.ensure_future(init_sudoers())
    else:
        try:
            loop.run_until_complete(init_sudoers())
        except RuntimeError as e:
            log.error(f"Lỗi RuntimeError: {e}")
        except Exception as e:
            log.error(f"Đã xảy ra lỗi: {e}")

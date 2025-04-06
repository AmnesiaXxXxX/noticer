"""Главный модуль запуска"""

import os
from dotenv import load_dotenv
from bot import Bot

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
API_ID = os.getenv("API_ID", "")
API_HASH = os.getenv("API_HASH", "")

if __name__ == "__main__":
    try:
        bot = Bot("reminder_bot", API_ID, API_HASH, BOT_TOKEN)
        bot.launch_bot()
    except KeyboardInterrupt:
        bot.cycle_run = False
        
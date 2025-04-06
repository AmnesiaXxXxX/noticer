"""Главный модуль запуска"""

import os

from dotenv import load_dotenv

from src.bot import Bot
from src.git_updater import GitUpdater

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
API_ID = os.getenv("API_ID", "")
API_HASH = os.getenv("API_HASH", "")
updater = GitUpdater()


def run():
    """Функция для запуска через poetry run app:run"""
    if not updater.is_latest_version:
        if input("Обнаружена новая версия, обновить? (y/n): ") == "y":
            updater.update()
        else:
            pass

    bot = Bot("reminder_bot", API_ID, API_HASH, BOT_TOKEN)
    bot.launch_bot()

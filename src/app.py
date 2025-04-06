"""Главный модуль запуска"""

import os
from dotenv import load_dotenv
from src.bot import Bot

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
API_ID = os.getenv("API_ID", "")
API_HASH = os.getenv("API_HASH", "")

def run():
    """Функция для запуска через poetry run app:run"""
    bot = Bot("reminder_bot", API_ID, API_HASH, BOT_TOKEN)
    bot.launch_bot()
    
        
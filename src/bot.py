"""Модуль бота"""

import inspect
import re
from asyncio import BaseEventLoop, sleep
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Coroutine, Optional, Union

from pyrogram import filters
from pyrogram.client import Client
from pyrogram.handlers.message_handler import MessageHandler
from pyrogram.types import Message

from reminder import Reminder


def run_check(obj: Reminder):
    return obj.check()


class Bot(Client):
    def __init__(
        self, name: str, api_id: Union[int, str], api_hash: str, bot_token: str
    ):
        self.reminders: list[Reminder] = []
        self.cycle_run: bool = True
        self.cycles: int = 0
        self.async_methods: dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {}
        super().__init__(name, api_id, api_hash, bot_token=bot_token)

        self.load_handlers()

    async def update_cycle(self):
        with ThreadPoolExecutor(max_workers=3) as executor:
            while self.cycle_run:
                self.cycles += 1
                future_to_object = {
                    executor.submit(run_check, obj): obj
                    for obj in self.reminders
                    if obj.is_active
                }

                # Собираем результаты по мере их готовности
                for future in future_to_object:
                    try:
                        result = future.result()
                        if result[0]:
                            r = [i for i in self.reminders if i.id == result[1]][0]

                            r.is_active = False
                            await self.send_message(
                                r.from_user.id,
                                f"```Уведомление!!!\n{r.text} на {r.date.strftime("%d/%m/%Y, %H:%M:%S")}```",
                            )
                        await sleep(0.5)
                    except Exception as e:
                        print(
                            f"Ошибка при выполнении для объекта {future_to_object[future].id}: {e}"
                        )

                await sleep(2)

    def collect_methods(self):
        """
        Получает список методов класса и разделяет их на синхронные и асинхронные.

        Args:
            self: Класс, методы которого нужно проанализировать

        Returns:
            Tuple содержащий два списка:
            - первый список - синхронные методы
            - второй список - асинхронные методы
        """

        # Получаем все атрибуты класса
        class_attrs = dir(self)

        for attr_name in class_attrs:
            if hasattr(super(), attr_name):
                continue
            # Пропускаем специальные методы и атрибуты
            if attr_name.startswith("_"):
                continue
            # Если метод наследуется от родительского класса, пропускаем его
            if not attr_name.startswith("handle"):
                continue

            try:
                attr = getattr(self, attr_name)
                # Проверяем, является ли атрибут функцией или методом
                if inspect.ismethod(attr) or inspect.isfunction(attr):
                    if inspect.iscoroutinefunction(attr):
                        self.async_methods[attr_name] = attr

            except AttributeError:
                continue
        return self.async_methods

    def load_handlers(self):
        self.collect_methods()
        for name, func in self.async_methods.items():
            attrs = name.split("_")[1:]
            self.add_handler(MessageHandler(func, filters.command(attrs)))

    def launch_bot(self, main_loop: Optional[BaseEventLoop] = None):
        if main_loop:
            self.loop = main_loop
        self.loop.create_task(self.update_cycle())
        self.run()

    async def handle_help_start(self, _, message: Message):
        q = await message.ask(
            "Ты здесь?",
        )
        await message.reply(f"```HTML\n{message.text.html}```")
        if q.text.lower() == "да":
            await message.reply("HEEELp")
        else:
            await message.reply(q.text.translate("en"))

    async def handle_remind(self, _, message: Message):
        time_arguments = [message.command[1].strip()]
        reminder_text = " ".join(message.command[2:])
        current_time = datetime.now(UTC)

        # Словарь для преобразования сокращений в секунды
        time_units = {
            "s": 1,  # секунды
            "m": 60,  # минуты
            "h": 3600,  # часы
            "d": 86400,  # дни
            "M": 2628000,  # месяцы (примерно 30 дней)
        }

        total_seconds = 0

        for arg in time_arguments:
            # Ищем все совпадения вида "число+буква" в аргументе
            matches = re.findall(r"(\d+)(\w)", arg)
            if matches:
                for match in matches:
                    number, unit = match
                    number = int(number)

                    # Проверяем, что единица времени допустима
                    if unit in time_units:
                        total_seconds += number * time_units[unit]
                    else:
                        await message.reply(f"Неизвестная единица времени: {unit}")
                        return

        if total_seconds == 0:
            await message.reply(
                "Пожалуйста, укажите корректное время (например, 1h, 30m, 1d)"
            )
            return

        # Вычисляем время напоминания
        reminder_time = current_time + timedelta(seconds=total_seconds)
        self.reminders.append(Reminder(message.from_user, reminder_text, reminder_time))

        # Форматируем время для пользователя
        formatted_time = reminder_time.strftime("%Y-%m-%d %H:%M:%S UTC")

        await message.reply(f"Напоминание установлено на {formatted_time}")

    async def handle_listOfReminders(self, _, message: Message):
        user_reminders = [
            str(i.id)
            for i in self.reminders
            if i.from_user.id == message.from_user.id and i.is_active
        ]
        if len(user_reminders):
            await message.reply(" ".join(user_reminders))
        else:
            await message.reply(
                "У вас нет напоминателей!!!",
            )

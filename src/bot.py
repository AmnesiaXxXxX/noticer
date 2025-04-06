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


class Bot(Client):
    """Класс бота"""

    def __init__(
        self, name: str, api_id: Union[int, str], api_hash: str, bot_token: str
    ):
        """
        Инициализирует экземпляр бота.

        Устанавливает базовые параметры для работы с API, создаёт
        необходимые переменные для хранения напоминаний и асинхронных методов.
        После базовой инициализации вызывается метод load_handlers для загрузки
        асинхронных обработчиков команд.

        Args:
            name (str): Имя клиента.
            api_id (Union[int, str]): Идентификатор API.
            api_hash (str): Хэш API.
            bot_token (str): Токен бота для аутентификации.
        """
        self.reminders: list[Reminder] = []
        self.cycle_run: bool = True
        self.cycles: int = 0
        self.async_methods: dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {}
        super().__init__(name, api_id, api_hash, bot_token=bot_token)

        self.load_handlers()

    @staticmethod
    def run_check(obj: Reminder):
        """Функция для проверки напоминателя"""
        return obj.check()

    async def update_cycle(self):
        """
        Запускает асинхронный цикл проверки напоминаний.

        Циклически проверяет каждое активное напоминание, используя ThreadPoolExecutor для
        параллельной обработки. При наступлении времени напоминания отправляется сообщение
        пользователю, а напоминание помечается как неактивное, чтобы не повторять отправку.

        Raises:
            Exception: Пробрасывает исключения, которые не обрабатываются внутри цикла.
        """
        with ThreadPoolExecutor(max_workers=3) as executor:
            while self.cycle_run:
                self.cycles += 1
                future_to_object = {
                    executor.submit(self.run_check, obj): obj
                    for obj in self.reminders
                    if obj.is_active
                }

                # Собираем результаты по мере их готовности
                for future in future_to_object:
                    try:
                        result = future.result()
                        if result[0]:
                            r = next(i for i in self.reminders if i.id == result[1])
                            r.is_active = False
                            await self.send_message(
                                r.from_user.id,
                                f"```Уведомление!!!\n{r.text} на {r.date.strftime('%d/%m/%Y, %H:%M:%S')}```",
                            )
                        await sleep(0.5)
                    except (StopIteration, TimeoutError) as e:
                        print(f"Ошибка для объекта {future_to_object[future].id}: {e}")
                    except Exception as e:
                        raise e

                await sleep(2)

    def collect_methods(self):
        """
        Собирает асинхронные методы-обработчики команд.

        Перебирает все атрибуты экземпляра класса, отфильтровывает методы, которые
        начинаются с "handle", и проверяет, являются ли они асинхронными.
        Найденные методы сохраняются в словаре self.async_methods.

        Returns:
            dict[str, Callable[..., Coroutine[Any, Any, Any]]]: Словарь асинхронных методов,
            где ключом является имя метода.
        """
        # Получаем все атрибуты класса
        class_attrs = dir(self)

        for attr_name in class_attrs:
            if hasattr(super(), attr_name):
                continue
            # Пропускаем специальные методы и атрибуты
            if attr_name.startswith("_"):
                continue
            # Если метод не начинается с "handle", пропускаем его
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
        """
        Загружает асинхронные обработчики команд в бота.

        Вызывает метод collect_methods для сбора всех асинхронных методов-обработчиков.
        Для каждого найденного метода формирует аргументы команды (остаток имени)
        и регистрирует их с помощью MessageHandler.
        """
        self.collect_methods()
        for name, func in self.async_methods.items():
            attrs = name.split("_")[1:]
            self.add_handler(MessageHandler(func, filters.command(attrs)))

    def launch_bot(self, main_loop: Optional[BaseEventLoop] = None):
        """
        Запускает бота.

        Принимает опциональный асинхронный цикл, в котором создаётся задача
        для обновления напоминаний, а затем запускается основной цикл клиента.

        Args:
            main_loop (Optional[BaseEventLoop]): Основной асинхронный цикл.
                Если указан, используется переданный цикл, иначе используется цикл клиента.
        """
        try:
            if main_loop:
                self.loop = main_loop
            self.loop.create_task(self.update_cycle())
            self.run()
        except KeyboardInterrupt:
            self.cycle_run = False

    async def handle_help_start(self, _, message: Message):
        """
        Обрабатывает команду справки.

        Отправляет пользователю запрос "Ты здесь?" и в зависимости от ответа
        отправляет соответствующее сообщение.

        Args:
            _ : Неиспользуемый параметр.
            message (Message): Объект сообщения, содержащий данные пользователя и команды.
        """
        q = await message.ask(
            "Ты здесь?",
        )
        if q.text.lower() == "да":
            await message.reply("HEEELp")
        else:
            await message.reply(q.text.translate("en"))

    async def handle_remind(self, _, message: Message):
        """
        Обрабатывает команду установки напоминания.

        Извлекает данные команды, включает аргументы времени, текст напоминания,
        вычисляет точное время напоминания и добавляет его в список. Затем отправляет
        подтверждение с отформатированным временем напоминания.

        Args:
            _ : Неиспользуемый параметр.
            message (Message): Объект сообщения, содержащий команду, данные пользователя и прочее.

        Side Effects:
            Добавляет объект Reminder в список self.reminders.
            Отправляет сообщение пользователю с информацией об установленном напоминании.
        """
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
        """
        Обрабатывает команду получения списка напоминаний.

        Фильтрует список напоминаний, оставляя только активные напоминания
        текущего пользователя. Если список не пуст, отправляет идентификаторы
        напоминаний, иначе сообщает об отсутствии напоминаний.

        Args:
            _ : Неиспользуемый параметр.
            message (Message): Объект сообщения, содержащий данные пользователя и команды.
        """
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

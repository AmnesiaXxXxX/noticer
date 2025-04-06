from datetime import datetime, UTC
from typing import Optional
from pyrogram.types import User


class Reminder:
    """
    Класс напоминателя

    Этот класс представляет напоминание с текстовым сообщением, запланированной датой,
    и уникальным идентификатором, созданным на основе даты и текста. Также ведется
    отслеживание текущего статуса напоминания, и хранится пользователь, который его установил.

    Атрибуты:
        text (str): Текст напоминания. По умолчанию "Стандартное уведомление", если не задан.
        date (datetime): Запланированная дата и время напоминания. Если не задана,
                         по умолчанию используется текущая дата и время.
        id (int): Уникальный идентификатор, вычисляемый как хэш строкового представления
                  даты, объединенной с текстом.
        is_active (bool): Флаг, указывающий, активно ли напоминание.
        from_user (User): Пользователь, который создал напоминание.

    Методы:
        check() -> tuple[bool, int]:
            Сравнивает запланированную дату напоминания с текущей датой и временем.

            Возвращает:
                tuple[bool, int]: Кортеж, где первый элемент - булево значение,
                указывающее, истекло ли время напоминания (True, если истекло, False - иначе),
                а второй элемент - уникальный идентификатор напоминания.
    """

    def __init__(
        self, user: User, text: str = "Стандартное уведомление", date: Optional[datetime] = None
    ) -> None:
        self.text: str = text
        if date is None:
            date = datetime.now()
        self.date: datetime = date
        self.id: int = hash(str(date) + self.text)
        self.is_active: bool = True
        self.from_user: User = user

    def check(self) -> tuple[bool, int]:
        """Проверяет, прошла ли дата напоминания, и возвращает кортеж (is_expired, id)."""
        now = datetime.now(UTC) if self.date.tzinfo else datetime.now(UTC)
        return self.date < now, self.id

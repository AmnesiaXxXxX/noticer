from datetime import datetime, UTC
from typing import Optional
from pyrogram.types import User


class Reminder:
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
        """Check if the reminder date has passed and return a tuple of (is_expired, id)."""
        now = datetime.now(UTC) if self.date.tzinfo else datetime.now(UTC)
        return self.date < now, self.id

import datetime
from typing import NamedTuple

from investments.money import Money


class Interest(NamedTuple):
    """
    Начисления процентов на кеш.

    По итогам года нужно заплатить с данных начислений обычные 13%

    """

    date: datetime.date
    amount: Money
    description: str

    def __str__(self):
        return f'{self.date} ({self.amount} {self.description})'

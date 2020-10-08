import datetime
from typing import NamedTuple

from investments.money import Money


class Fee(NamedTuple):
    """
    Побочные комиссии.

    По итогам года можно сальдировать сумму данных комиссий с доходами от сделок на фондовой секции
    Из дивидендов вычесть нельзя
    НК РФ 214.1.10 пункты 3, 8, 12,

    """

    date: datetime.date
    amount: Money
    description: str

    def __str__(self):
        return f'{self.date} ({self.amount} {self.description})'

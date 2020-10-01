import datetime
from dataclasses import dataclass

from investments.money import Money


@dataclass
class Fee:
    """
    Побочные комиссии
    По итогам года можно сальдировать сумму данных комиссий с доходами от сделок на фондовой секции
    Из дивидендов вычесть нельзя
    НК РФ 214.1.10 пункты 3, 8, 12,

    """

    date: datetime.date
    amount: Money
    description: str

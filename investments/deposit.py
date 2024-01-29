import datetime
from typing import NamedTuple

from investments.money import Money


class Deposit(NamedTuple):
    date: datetime.date
    amount: Money

    # def __str__(self):
    #     return f'{self.ticker}, {self.date} ({self.amount} tax:{self.tax})'

import datetime
from typing import NamedTuple

from investments.money import Money
from investments.ticker import Ticker


class Dividend(NamedTuple):
    dtype: str
    ticker: Ticker
    date: datetime.date
    amount: Money
    tax: Money

    def __str__(self):
        return f'{self.ticker}, {self.date} ({self.amount} tax:{self.tax})'

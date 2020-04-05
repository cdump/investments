import datetime
from typing import NamedTuple

from investments.money import Money
from investments.ticker import Ticker


class Trade(NamedTuple):
    ticker: Ticker
    datetime: datetime.datetime
    settle_date: datetime.date
    quantity: int
    price: Money
    fee: Money

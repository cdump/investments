import datetime
from typing import NamedTuple

from investments.money import Money
from investments.ticker import Ticker


class Trade(NamedTuple):
    ticker: Ticker
    trade_date: datetime.datetime
    settle_date: datetime.date
    quantity: int

    # цена одной бумаги
    price: Money

    # комиссия за сделку
    fee: Money

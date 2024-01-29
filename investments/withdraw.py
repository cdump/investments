import datetime
from typing import NamedTuple

from investments.money import Money


class Withdraw(NamedTuple):
    date: datetime.date
    amount: Money

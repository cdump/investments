from enum import Enum
from typing import NamedTuple


class TickerKind(Enum):
    Stock = 1
    Option = 2
    Futures = 3
    Bond = 4
    Forex = 5
    Rdr = 6
    Index = 7

    def __str__(self):
        return self.name

    def __lt__(self, other):
        return self.value < other.value


class Ticker(NamedTuple):
    symbol: str
    kind: TickerKind

    def __str__(self):
        return f'{self.symbol} ({self.kind})'

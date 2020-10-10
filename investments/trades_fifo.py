import datetime
from collections import Counter, defaultdict
from typing import Iterable, List, NamedTuple, Optional, Tuple

from investments.money import Money
from investments.ticker import Ticker
from investments.trade import Trade


class FinishedTrade(NamedTuple):
    N: int
    ticker: Ticker
    datetime: datetime.datetime
    settle_date: datetime.date
    quantity: int
    price: Money
    total: Money
    profit: Money


def sign(v: int) -> int:
    assert v != 0
    return -1 if v < 0 else 1


class _TradesFIFO:
    def __init__(self):
        self._portfolio = defaultdict(list)

    def put(self, quantity: int, trade: Trade):
        """
        Put trade to the storage.

        Args:
            quantity (int): The real quantity of the trade, >0 for BUY trades & <0 for SELL trades
            trade (Trade): Base trade, quantity field not used
        """
        assert sign(quantity) == sign(trade.quantity)
        assert abs(quantity) <= abs(trade.quantity)
        if self._portfolio[trade.ticker]:
            assert sign(quantity) == sign(self._portfolio[trade.ticker][0]['quantity'])

        self._portfolio[trade.ticker].append({
            'trade': trade,
            'quantity': quantity,
        })

    def match(self, quantity: int, ticker: Ticker) -> Tuple[Optional[Trade], int]:
        """
        Try to match trade.

        Args:
            quantity (int): The real quantity of the trade, >0 for BUY trades & <0 for SELL trades
            ticker (Ticker): Ticker to match

        Returns:
            matched_trade: A matched trade
            quantity: Real quantity 'used' from matched_trade
        """
        if (ticker not in self._portfolio) or (not self._portfolio[ticker]):
            return None, 0

        front = self._portfolio[ticker][0]
        fqsign = sign(front['quantity'])

        # only match BUY with SELL and vice versa
        if sign(quantity) == fqsign:
            return None, 0

        q = fqsign * min(abs(quantity), abs(front['quantity']))
        if q == front['quantity']:
            self._portfolio[ticker].pop(0)
        else:
            self._portfolio[ticker][0]['quantity'] = front['quantity'] - q

        return front['trade'], q


def analyze_portfolio(trades: Iterable[Trade]) -> List[Tuple[str, int]]:
    out: Counter = Counter()
    for t in trades:
        out.update(**{str(t.ticker): t.quantity})
    return list(filter(lambda x: x[1], sorted(out.items())))


def analyze_trades_fifo(trades: Iterable[Trade]) -> List[FinishedTrade]:
    finished_trades = []
    finished_trade_id = 1

    active_trades = _TradesFIFO()

    for trade in trades:
        total_profit = None

        quantity = trade.quantity
        while quantity != 0:

            matched_trade, q = active_trades.match(quantity, trade.ticker)
            if matched_trade is None:
                assert q == 0
                break
            assert q != 0

            finished_trades.append(FinishedTrade(
                finished_trade_id,
                trade.ticker,
                matched_trade.datetime,
                matched_trade.settle_date,
                q,
                matched_trade.price,
                abs(q) * matched_trade.price,
                Money(0, trade.price.currency),
            ))

            profit = q * (trade.price - matched_trade.price)
            if total_profit is None:
                total_profit = profit
            else:
                total_profit += profit

            quantity -= -1 * q

        if total_profit is not None:
            q = trade.quantity - quantity
            finished_trades.append(FinishedTrade(
                finished_trade_id,
                trade.ticker,
                trade.datetime,
                trade.settle_date,
                q,
                trade.price,
                abs(q) * trade.price,
                total_profit,
            ))
            finished_trade_id += 1

        if quantity != 0:
            active_trades.put(quantity, trade)

    return finished_trades

import datetime
from collections import defaultdict
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Tuple

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


class PortfolioElement(NamedTuple):
    ticker: Ticker
    quantity: int


class TradesAnalyzer:
    _finished_trades: List[FinishedTrade]
    _portfolio: List[PortfolioElement]

    def __init__(self, trades: Iterable[Trade]):
        self._finished_trades = []
        self._portfolio = []
        self.analyze_trades(trades)

    def analyze_trades(self, trades: Iterable[Trade]):
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

                self._finished_trades.append(FinishedTrade(
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
                self._finished_trades.append(FinishedTrade(
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

        self._portfolio = [PortfolioElement(quantity=element['quantity'], ticker=element['ticker']) for element in active_trades.unmatched()]

    @property
    def finished_trades(self) -> List[FinishedTrade]:
        return self._finished_trades

    @property
    def final_portfolio(self) -> List[PortfolioElement]:
        return self._portfolio


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

    def unmatched(self) -> List[Dict[str, Any]]:
        """
        Return basic information about unmatched trades (final portfolio).

        Returns:
            portfolio: Portfolio
        """
        ret = []
        for ticker, trades in self._portfolio.items():
            quantity = sum(v['quantity'] for v in trades)
            if quantity != 0:
                ret.append({'quantity': quantity, 'ticker': ticker})
        return ret

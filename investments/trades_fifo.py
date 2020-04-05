import datetime
from collections import defaultdict
from typing import Any, List, NamedTuple, Tuple

from investments.money import Money
from investments.ticker import Ticker


class FinishedTrade(NamedTuple):
    N: int
    ticker: Ticker
    datetime: datetime.datetime
    settle_date: datetime.date
    quantity: int
    price: Money
    total: Money
    profit: Any
    # profit: Money


def analyze_trades_fifo(trades) -> Tuple[List[Any], List[FinishedTrade]]:
    bought = defaultdict(list)
    trade_id = 1

    finished_trades = []

    for trade in trades:
        if trade.quantity > 0:  # buy
            bought[trade.ticker].append({
                'buy_trade': trade,
                'quantity': trade.quantity,
            })
        else:  # sell
            quantity = abs(trade.quantity)

            total_profit = None
            while quantity != 0:
                front = bought[trade.ticker][0]
                q = min(quantity, front['quantity'])
                if q == front['quantity']:
                    bought[trade.ticker].pop(0)
                else:
                    bought[trade.ticker][0]['quantity'] = front['quantity'] - q

                buy_trade = front['buy_trade']
                finished_trades.append(FinishedTrade(
                    trade_id,
                    trade.ticker,
                    buy_trade.datetime,
                    buy_trade.settle_date,
                    q,
                    buy_trade.price,
                    q * buy_trade.price,
                    0,
                ))

                profit = q * (trade.price - buy_trade.price)
                if total_profit is None:
                    total_profit = profit
                else:
                    total_profit += profit

                quantity -= q

            finished_trades.append(FinishedTrade(
                trade_id,
                trade.ticker,
                trade.datetime,
                trade.settle_date,
                trade.quantity,
                trade.price,
                abs(trade.quantity) * trade.price,
                total_profit,
            ))

            trade_id += 1

    portfolio = []
    for ticker, buy_trades in bought.items():
        quantity = sum(v['quantity'] for v in buy_trades)
        assert quantity >= 0
        if quantity > 0:
            portfolio.append({'ticker': ticker, 'quantity': quantity})

    return portfolio, finished_trades

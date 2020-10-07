import datetime

import pytest

from investments.currency import Currency
from investments.money import Money
from investments.ticker import Ticker, TickerKind
from investments.trade import Trade
from investments.trades_fifo import TradesAnalyzer

analyze_trades_fifo_testdata = [
    # trades: [(Date, Symbol, Quantity, Price)]
    # expect_trades: (N, Symbol, Quantity, Total, Profit)

    # basic case with custom fees
    ([('2018-01-01', 'TEST', 100, 4.2), ('2018-01-04', 'TEST', 50, 17.5), ('2018-01-07', 'TEST', -100, 50.3)],
     [(1, 'TEST', 100, 420, 0), (1, 'TEST', -100, 5030, 4610)]),

    # basic cases
    ([('2018-01-01', 'TEST', 100, 4.2), ('2018-01-04', 'TEST', 50, 17.5), ('2018-01-07', 'TEST', -100, 50.3)],
     [(1, 'TEST', 100, 420, 0), (1, 'TEST', -100, 5030, 4610)]),

    ([('2018-01-01', 'TEST', 100, 4.2), ('2018-01-04', 'TEST', 50, 17.5), ('2018-01-07', 'TEST', -130, 50.3)],
     [(1, 'TEST', 100, 420, 0), (1, 'TEST', 30, 525, 0), (1, 'TEST', -130, 6539, 5594)]),

    ([('2018-01-01', 'TEST', -100, 4.2), ('2018-01-04', 'TEST', 30, 17.5)],
     [(1, 'TEST', -30, 126, 0), (1, 'TEST', 30, 525, -399)]),

    # issue #8 - sell all & open short in one trade
    ([('2018-01-01', 'TEST', 10, 4.2), ('2018-01-04', 'TEST', -10, 17.5), ('2018-01-05', 'TEST', -3, 17.5)],
     [(1, 'TEST', 10, 42, 0), (1, 'TEST', -10, 175, 133)]),

    ([('2018-01-01', 'TEST', 10, 4.2), ('2018-01-05', 'TEST', -13, 17.5)],
     [(1, 'TEST', 10, 42, 0), (1, 'TEST', -10, 175, 133)]),
]


@pytest.mark.parametrize("trades,expect_trades", analyze_trades_fifo_testdata)
def test_analyze_trades_fifo(trades, expect_trades):
    request_trades = []
    for date, ticker, qty, price in trades:
        dt = datetime.datetime.strptime(date, '%Y-%m-%d')
        request_trades.append(Trade(
            ticker=Ticker(symbol=ticker, kind=TickerKind.Stock),
            datetime=dt,
            settle_date=dt.date(),
            quantity=qty,
            price=Money(price, Currency.USD),
            fee=Money(-1, Currency.USD),
        ))

    finished_trades = TradesAnalyzer(request_trades).finished_trades

    assert len(finished_trades) == len(
        expect_trades), f'expect {len(expect_trades)} finished trades but got {len(finished_trades)}'
    for trade, expected in zip(finished_trades, expect_trades):
        assert expected[0] == trade.N, f'expect trade N={expected[0]} but got {trade.N}'
        assert expected[1] == trade.ticker.symbol, f'expect trade ticker={expected[1]} but got {trade.ticker.symbol}'
        assert expected[2] == trade.quantity, f'expect trade quantity={expected[2]} but got {trade.quantity}'
        assert expected[3] == trade.total.amount, f'expect trade total={expected[3]} but got {trade.total.amount}'
        assert expected[4] == trade.profit.amount, f'expect trade profit={expected[4]} but got {trade.profit.amount}'

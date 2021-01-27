import datetime
from decimal import Decimal
from typing import List

import pytest

from investments.currency import Currency
from investments.money import Money
from investments.ticker import Ticker, TickerKind
from investments.trade import Trade
from investments.trades_fifo import TradesAnalyzer, FinishedTrade

analyze_trades_fifo_testdata = [
    # trades: [(Date, Symbol, Quantity, Price)]
    # expect_trades: (N, Symbol, Quantity)

    # basic cases
    ([('2018-01-01', 'TEST', 100, 4.2), ('2018-01-04', 'TEST', 50, 17.5), ('2018-01-07', 'TEST', -100, 50.3)],
     [(1, 'TEST', 100), (1, 'TEST', -100)]),

    ([('2018-01-01', 'TEST', 100, 4.2), ('2018-01-04', 'TEST', 50, 17.5), ('2018-01-07', 'TEST', -130, 50.3)],
     [(1, 'TEST', 100), (1, 'TEST', 30), (1, 'TEST', -130)]),

    ([('2018-01-01', 'TEST', -100, 4.2), ('2018-01-04', 'TEST', 30, 17.5)],
     [(1, 'TEST', -30), (1, 'TEST', 30)]),

    # issue #8 - sell all & open short in one trade
    ([('2018-01-01', 'TEST', 10, 4.2), ('2018-01-04', 'TEST', -10, 17.5), ('2018-01-05', 'TEST', -3, 17.5)],
     [(1, 'TEST', 10), (1, 'TEST', -10)]),

    ([('2018-01-01', 'TEST', 10, 4.2), ('2018-01-05', 'TEST', -13, 17.5)],
     [(1, 'TEST', 10), (1, 'TEST', -10)]),
]


@pytest.mark.parametrize("trades,expect_trades", analyze_trades_fifo_testdata)
def test_analyze_trades_without_fees(trades, expect_trades):
    request_trades = []
    for date, ticker, qty, price in trades:
        dt = datetime.datetime.strptime(date, '%Y-%m-%d')
        request_trades.append(Trade(
            ticker=Ticker(symbol=ticker, kind=TickerKind.Stock),
            trade_date=dt,
            settle_date=dt.date(),
            quantity=qty,
            price=Money(price, Currency.USD),
            fee=Money(0, Currency.USD),
        ))

    finished_trades = TradesAnalyzer(request_trades).finished_trades

    assert len(finished_trades) == len(
        expect_trades), f'expect {len(expect_trades)} finished trades but got {len(finished_trades)}'
    for trade, expected in zip(finished_trades, expect_trades):
        assert expected[0] == trade.N, f'expect trade N={expected[0]} but got {trade.N}'
        assert expected[1] == trade.ticker.symbol, f'expect trade ticker={expected[1]} but got {trade.ticker.symbol}'
        assert expected[2] == trade.quantity, f'expect trade quantity={expected[2]} but got {trade.quantity}'


def test_trades_fees_simple():
    request_trades = []
    ticker = Ticker(symbol='VT', kind=TickerKind.Stock)

    # buy 10
    request_trades.append(Trade(
        ticker=ticker,
        trade_date=datetime.datetime(year=2020, month=1, day=31),  # 63,0359₽
        settle_date=datetime.datetime(year=2020, month=2, day=4),  # 63,9091₽
        quantity=10,
        price=Money(80.62, Currency.USD),
        fee=Money(-1, Currency.USD),
    ))
    # sell 10
    request_trades.append(Trade(
        ticker=ticker,
        trade_date=datetime.datetime(year=2020, month=2, day=10),  # 63,4720₽
        settle_date=datetime.datetime(year=2020, month=2, day=12),  # 63,9490₽
        quantity=-10,
        price=Money(81.82, Currency.USD),
        fee=Money(Decimal('-1.01812674'), Currency.USD),
    ))

    finished_trades = TradesAnalyzer(request_trades).finished_trades

    assert len(finished_trades) == 2

    buy_trade: FinishedTrade = finished_trades[0]
    assert buy_trade.trade_date == datetime.datetime(year=2020, month=1, day=31)
    assert buy_trade.settle_date == datetime.datetime(year=2020, month=2, day=4)
    assert buy_trade.quantity == 10
    assert buy_trade.price.amount == Decimal('80.62')
    assert buy_trade.fee_per_piece.amount == Decimal('-0.1')

    sell_trade: FinishedTrade = finished_trades[1]
    assert sell_trade.trade_date == datetime.datetime(year=2020, month=2, day=10)
    assert sell_trade.settle_date == datetime.datetime(year=2020, month=2, day=12)
    assert sell_trade.quantity == -10
    assert sell_trade.price.amount == Decimal('81.82')
    assert sell_trade.fee_per_piece.amount == Decimal('-0.101812674')


def test_trades_precision() -> List[FinishedTrade]:
    ticker = Ticker(symbol='VT', kind=TickerKind.Stock)
    test_case = [
        Trade(
            ticker=ticker,
            trade_date=datetime.datetime(2020, 1, 31, 9, 30),  # 63,0359₽
            settle_date=datetime.date(2020, 2, 4),  # 63,9091₽
            quantity=10,
            price=Money('80.62', Currency.USD),
            fee=Money('-1', Currency.USD)
        ),
        Trade(
            ticker=ticker,
            trade_date=datetime.datetime(2020, 2, 10, 9, 38),  # 63,4720₽
            settle_date=datetime.date(2020, 2, 12),  # 63,9490₽
            quantity=-10,
            price=Money('81.82', Currency.USD),
            fee=Money('-1.01812674', Currency.USD)
        )
    ]

    finished_trades = TradesAnalyzer(test_case).finished_trades

    buy_trade: FinishedTrade = finished_trades[0]
    assert buy_trade.price.amount == Decimal('80.62')
    assert buy_trade.fee_per_piece.amount == Decimal('-0.1')

    sell_trade: FinishedTrade = finished_trades[1]
    assert sell_trade.price.amount == Decimal('81.82')
    assert sell_trade.fee_per_piece.amount == Decimal('-0.101812674')

    return finished_trades


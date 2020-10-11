import datetime
from decimal import Decimal

import pytest

from investments.currency import Currency
from investments.money import Money
from investments.ticker import Ticker, TickerKind
from investments.trade import Trade
from investments.trades_fifo import FinishedTrade
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
            trade_date=dt,
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


def test_trades_with_fee_simple():
    """Купили/продали одной операцией

    """

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
    assert buy_trade.fee.amount == Decimal('-1')
    assert buy_trade.basis.amount == Decimal('-807.20')  # 10 * 80.62 + 1 * -1
    assert buy_trade.basis_rub.amount == Decimal('-51586.552320')  # 10 * (80.62 * 63.9091) + (1 * 63.0359) * -1
    assert buy_trade.basis_rub.currency == Currency.RUB
    assert buy_trade.profit.amount == Decimal(0)
    assert buy_trade.profit_rub.amount == Decimal(0)

    sell_trade: FinishedTrade = finished_trades[1]
    assert sell_trade.trade_date == datetime.datetime(year=2020, month=2, day=10)
    assert sell_trade.settle_date == datetime.datetime(year=2020, month=2, day=12)
    assert sell_trade.quantity == -10
    assert sell_trade.price.amount == Decimal('81.82')
    assert sell_trade.fee.amount == Decimal('-1.01812674')
    assert sell_trade.basis.amount == Decimal('817.18187326')  # 10 * 81.82 - 1.01812674
    assert sell_trade.basis_rub.amount == Decimal('52258.449259559')  # 10 * (81.82 * 63.9490) - (1.01812674 * 63.4720)
    assert sell_trade.basis_rub.currency == Currency.RUB
    assert sell_trade.profit.amount == Decimal(0)
    assert sell_trade.profit_rub.amount == Decimal(0)


# def test_trades_with_fee_few_trades():
#     """Несколько сделок покупки и несколько продаж вперемешку.
#
#     """
#
#     request_trades = []
#     ticker = Ticker(symbol='VT', kind=TickerKind.Stock)
#
#     # buy 10
#     request_trades.append(Trade(
#         ticker=ticker,
#         trade_date=datetime.datetime(year=2020, month=1, day=31),  # 63,0359₽
#         settle_date=datetime.datetime(year=2020, month=2, day=4),  # 63,9091₽
#         quantity=10,
#         price=Money(80.62, Currency.USD),
#         fee=Money(-1, Currency.USD),
#     ))
#     # sell 3
#     request_trades.append(Trade(
#         ticker=ticker,
#         trade_date=datetime.datetime(year=2020, month=2, day=10),  # 63,4720₽
#         settle_date=datetime.datetime(year=2020, month=2, day=12),  # 63,9490₽
#         quantity=-10,
#         price=Money(81.82, Currency.USD),
#         fee=Money(Decimal('-1.01812674'), Currency.USD),
#     ))
#     # sell 1
#     request_trades.append(Trade(
#         ticker=ticker,
#         trade_date=datetime.datetime(year=2020, month=2, day=10),  # 63,4720₽
#         settle_date=datetime.datetime(year=2020, month=2, day=12),  # 63,9490₽
#         quantity=-10,
#         price=Money(81.82, Currency.USD),
#         fee=Money(Decimal('-1.01812674'), Currency.USD),
#     ))
#     # buy 17
#     request_trades.append(Trade(
#         ticker=ticker,
#         trade_date=datetime.datetime(year=2020, month=2, day=10),  # 63,4720₽
#         settle_date=datetime.datetime(year=2020, month=2, day=12),  # 63,9490₽
#         quantity=-10,
#         price=Money(81.82, Currency.USD),
#         fee=Money(Decimal('-1.01812674'), Currency.USD),
#     ))
#     # sell 9
#     request_trades.append(Trade(
#         ticker=ticker,
#         trade_date=datetime.datetime(year=2020, month=2, day=10),  # 63,4720₽
#         settle_date=datetime.datetime(year=2020, month=2, day=12),  # 63,9490₽
#         quantity=-10,
#         price=Money(81.82, Currency.USD),
#         fee=Money(Decimal('-1.01812674'), Currency.USD),
#     ))
#
#     finished_trades = analyze_trades_fifo(request_trades)
#
#     assert len(finished_trades) == 2
#

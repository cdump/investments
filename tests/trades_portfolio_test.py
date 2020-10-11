import datetime

import pytest

from investments.currency import Currency
from investments.money import Money
from investments.ticker import Ticker, TickerKind
from investments.trade import Trade
from investments.trades_fifo import TradesAnalyzer


def test_analyze_portfolio_different_kinds():
    ticker_stock = Ticker(symbol='TEST', kind=TickerKind.Stock)
    ticker_option = Ticker(symbol='TEST', kind=TickerKind.Option)
    dt = datetime.datetime.now()

    request_trades = [
        Trade(ticker=ticker_stock, trade_date=dt, settle_date=dt.date(), quantity=-3, price=Money(4.2, Currency.USD),
              fee=Money(1, Currency.USD)),
        Trade(ticker=ticker_stock, trade_date=dt, settle_date=dt.date(), quantity=8, price=Money(4.2, Currency.USD),
              fee=Money(1, Currency.USD)),
        Trade(ticker=ticker_option, trade_date=dt, settle_date=dt.date(), quantity=10, price=Money(4.2, Currency.USD),
              fee=Money(1, Currency.USD)),
    ]

    res = TradesAnalyzer(request_trades).final_portfolio

    assert len(res) == 2
    assert res[0].quantity == 5
    assert res[0].ticker == ticker_stock
    assert res[1].quantity == 10
    assert res[1].ticker == ticker_option


analyze_portfolio_testdata = [
    # trades: [(Date, Symbol, Quantity)]
    # expect_portfolio: {Symbol: quantity}
    ([('2018-01-01', 'FOO', 100500), ('2018-01-01', 'BAR', 1998), ('2020-10-12', 'FOO', 7.98), ('2018-01-01', 'BAR', -3)],
     [('FOO (Stock)', 100500 + 7.98), ('BAR (Stock)', 1998 - 3)]),

    # short position
    ([('2018-01-01', 'FOO', 123), ('2018-02-01', 'FOO', -130)], [('FOO (Stock)', 123 - 130)]),

    # filter zero
    ([('2018-01-01', 'FOO', 10), ('2018-02-01', 'BAR', 20), ('2018-02-01', 'FOO', -10)], [('BAR (Stock)', 20)]),
]


@pytest.mark.parametrize("trades,expect_portfolio", analyze_portfolio_testdata)
def test_analyze_portfolio(trades: list, expect_portfolio: dict):
    request_trades = []
    for date, ticker, qty in trades:
        dt = datetime.datetime.strptime(date, '%Y-%m-%d')
        request_trades.append(Trade(
            ticker=Ticker(symbol=ticker, kind=TickerKind.Stock),
            trade_date=dt,
            settle_date=dt.date(),
            quantity=qty,
            price=Money(1, Currency.USD),
            fee=Money(-1, Currency.USD),
        ))

    resp_portfolio = TradesAnalyzer(request_trades).final_portfolio

    assert expect_portfolio == [(str(i.ticker), i.quantity) for i in resp_portfolio]

import datetime

from investments.currency import Currency
from investments.money import Money
from investments.ticker import Ticker, TickerKind
from investments.trade import Trade
from investments.trades_fifo import _TradesFIFO, analyze_trades_fifo


def test_tradesfifo_ticker_different_kinds():
    dt = datetime.datetime.now()
    tfifo = _TradesFIFO()

    ticker_stock = Ticker(symbol='TEST', kind=TickerKind.Stock)
    ticker_option = Ticker(symbol='TEST', kind=TickerKind.Option)

    tfifo.put(3, Trade(
        ticker=ticker_stock,
        datetime=dt,
        settle_date=dt.date(),
        quantity=4,
        price=Money(4.2, Currency.USD),
        fee=Money(1, Currency.USD),
    ))
    unmatched = tfifo.unmatched()
    assert len(unmatched) == 1
    assert unmatched[0]['ticker'] == ticker_stock
    assert unmatched[0]['quantity'] == 3

    tfifo.put(2, Trade(
        ticker=ticker_stock,
        datetime=dt,
        settle_date=dt.date(),
        quantity=4,
        price=Money(4.2, Currency.USD),
        fee=Money(1, Currency.USD),
    ))
    unmatched = tfifo.unmatched()
    assert len(unmatched) == 1
    assert unmatched[0]['ticker'] == ticker_stock
    assert unmatched[0]['quantity'] == 5

    tfifo.put(1, Trade(
        ticker=ticker_option,
        datetime=dt,
        settle_date=dt.date(),
        quantity=3,
        price=Money(4.2, Currency.USD),
        fee=Money(1, Currency.USD),
    ))
    unmatched = tfifo.unmatched()
    assert len(unmatched) == 2
    unmatched_q = {x['ticker']: x['quantity'] for x in unmatched}
    assert ticker_stock in unmatched_q
    assert ticker_option in unmatched_q
    assert unmatched_q[ticker_stock] == 5
    assert unmatched_q[ticker_option] == 1


def test_analyze_trades_fifo():
    dt = datetime.datetime.now()

    testcases = [
        {
            'trades': [
                ('2018-01-01', 'TEST', 100, 4.2),
                ('2018-01-04', 'TEST', 50, 17.5),
                ('2018-01-07', 'TEST', -100, 50.3),
            ],
            'expect_portfolio': [('TEST', 50)],
        },
        {
            'trades': [
                ('2018-01-01', 'TEST', 100, 4.2),
                ('2018-01-04', 'TEST', 50, 17.5),
                ('2018-01-07', 'TEST', -130, 50.3),
            ],
            'expect_portfolio': [('TEST', 20)],
        },
        {
            'trades': [
                ('2018-01-01', 'TEST', -100, 4.2),
                ('2018-01-04', 'TEST', 30, 17.5),
            ],
            'expect_portfolio': [('TEST', -70)],
        },
    ]

    for tc in testcases:
        trades = []
        for t in tc['trades']:
            dt = datetime.datetime.strptime(t[0], '%Y-%m-%d')
            trades.append(Trade(
                ticker=Ticker(symbol=t[1], kind=TickerKind.Stock),
                datetime=dt,
                settle_date=dt.date(),
                quantity=t[2],
                price=Money(t[3], Currency.USD),
                fee=Money(1, Currency.USD),
            ))

        portfolio, finished_trades = analyze_trades_fifo(trades)
        print(portfolio)
        assert len(portfolio) == len(tc['expect_portfolio'])
        assert len(portfolio) == 1  # FIXME
        assert portfolio[0]['ticker'].symbol == tc['expect_portfolio'][0][0]
        assert portfolio[0]['quantity'] == tc['expect_portfolio'][0][1]

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
    # trades: [(Date, Symbol, Quantity, Price)]
    # expect_portfolio: (Symbol, quantity)
    # expect_trades: (N, Symbol, Quantity, Total, Profit)
    testcases = [
        {
            'trades': [
                ('2018-01-01', 'TEST', 100, 4.2),
                ('2018-01-04', 'TEST', 50, 17.5),
                ('2018-01-07', 'TEST', -100, 50.3),
            ],
            'expect_portfolio': [('TEST', 50)],
            'expect_trades': [(1, 'TEST', 100, 420, 0), (1, 'TEST', -100, 5030, 4610)],
        },
        {
            'trades': [
                ('2018-01-01', 'TEST', 100, 4.2),
                ('2018-01-04', 'TEST', 50, 17.5),
                ('2018-01-07', 'TEST', -130, 50.3),
            ],
            'expect_portfolio': [('TEST', 20)],
            'expect_trades': [(1, 'TEST', 100, 420, 0), (1, 'TEST', 30, 525, 0), (1, 'TEST', -130, 6539, 5594)],
        },
        {
            'trades': [
                ('2018-01-01', 'TEST', -100, 4.2),
                ('2018-01-04', 'TEST', 30, 17.5),
            ],
            'expect_portfolio': [('TEST', -70)],
            'expect_trades': [(1, 'TEST', -30, 126, 0), (1, 'TEST', 30, 525, -399)],
        },

        # issue #8 - sell all & open short in one trade
        {
            'trades': [
                ('2018-01-01', 'TEST', 10, 4.2),
                ('2018-01-04', 'TEST', -10, 17.5),
                ('2018-01-05', 'TEST', -3, 17.5),
            ],
            'expect_portfolio': [('TEST', -3)],
            'expect_trades': [(1, 'TEST', 10, 42, 0), (1, 'TEST', -10, 175, 133)],
        },
        {
            'trades': [
                ('2018-01-01', 'TEST', 10, 4.2),
                ('2018-01-05', 'TEST', -13, 17.5),
            ],
            'expect_portfolio': [('TEST', -3)],
            'expect_trades': [(1, 'TEST', 10, 42, 0), (1, 'TEST', -10, 175, 133)],
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
        # print(finished_trades)
        # print(portfolio)
        assert len(finished_trades) == len(tc['expect_trades']), f'expect {len(tc["expect_trades"])} finished trades but got {len(finished_trades)}'
        for trade, expected in zip(finished_trades, tc['expect_trades']):
            assert expected[0] == trade.N, f'expect trade N={expected[0]} but got {trade.N}'
            assert expected[1] == trade.ticker.symbol, f'expect trade ticker={expected[1]} but got {trade.ticker.symbol}'
            assert expected[2] == trade.quantity, f'expect trade quantity={expected[2]} but got {trade.quantity}'
            assert expected[3] == trade.total.amount, f'expect trade total={expected[3]} but got {trade.total.amount}'
            assert expected[4] == trade.profit.amount, f'expect trade profit={expected[4]} but got {trade.profit.amount}'

        assert len(portfolio) == len(tc['expect_portfolio'])
        assert len(portfolio) == 1  # FIXME
        assert portfolio[0]['ticker'].symbol == tc['expect_portfolio'][0][0]
        assert portfolio[0]['quantity'] == tc['expect_portfolio'][0][1]

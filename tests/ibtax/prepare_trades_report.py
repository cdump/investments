import datetime

from investments.currency import Currency
from investments.data_providers.cbr import ExchangeRatesRUB
from investments.ibtax.ibtax import prepare_trades_report
from investments.money import Money
from investments.ticker import Ticker, TickerKind
from investments.trades_fifo import FinishedTrade


def test_simple_trades():
    ticker = Ticker(symbol='VT', kind=TickerKind.Stock)

    trades = [
        FinishedTrade(N=1, ticker=ticker, trade_date=datetime.datetime(2020, 1, 30, 0, 0), settle_date=datetime.datetime(2020, 2, 3, 0, 0), quantity=7,
                      price=Money(80.62, Currency.USD), fee_per_piece=Money(-0.123375, Currency.USD)),

        FinishedTrade(N=1, ticker=ticker, trade_date=datetime.datetime(2020, 1, 31, 0, 0), settle_date=datetime.datetime(2020, 2, 4, 0, 0), quantity=-7,
                      price=Money(81.82, Currency.USD), fee_per_piece=Money('-0.1309628571428571428571428571', Currency.USD)),

        FinishedTrade(N=2, ticker=ticker, trade_date=datetime.datetime(2020, 1, 30, 0, 0), settle_date=datetime.datetime(2020, 2, 3, 0, 0), quantity=1,
                      price=Money(80.62, Currency.USD), fee_per_piece=Money('-0.123375', Currency.USD)),

        FinishedTrade(N=2, ticker=ticker, trade_date=datetime.datetime(2020, 1, 31, 0, 0), settle_date=datetime.datetime(2020, 2, 4, 0, 0), quantity=9,
                      price=Money(80.62, Currency.USD), fee_per_piece=Money(-0.1, Currency.USD)),

        FinishedTrade(N=2, ticker=ticker, trade_date=datetime.datetime(2020, 2, 10, 0, 0), settle_date=datetime.datetime(2020, 2, 12, 0, 0), quantity=-10,
                      price=Money(81.82, Currency.USD), fee_per_piece=Money('-0.101812674', Currency.USD)),
    ]
    cbr_client = ExchangeRatesRUB(Currency.USD)

    res: dict = prepare_trades_report(trades, cbr_client, False).to_dict()

    assert res['settle_rate'] == {0: Money(63.1385, Currency.RUB), 1: Money(63.9091, Currency.RUB), 2: Money(63.1385, Currency.RUB), 3: Money(63.9091, Currency.RUB), 4: Money(63.9490, Currency.RUB)}
    assert res['fee_rate'] == {0: Money(62.3934, Currency.RUB), 1: Money(63.0359, Currency.RUB), 2: Money(62.3934, Currency.RUB), 3: Money(63.0359, Currency.RUB), 4: Money(63.4720, Currency.RUB)}
    assert res['fee'] == {0: Money(-0.84, Currency.USD), 1: Money(-0.91, Currency.USD), 2: Money(-0.12, Currency.USD), 3: Money(-0.90, Currency.USD), 4: Money(-1.00, Currency.USD)}
    assert res['total'] == {0: Money(-565.18, Currency.USD), 1: Money(571.83, Currency.USD), 2: Money(-80.74, Currency.USD), 3: Money(-726.48, Currency.USD), 4: Money(817.20, Currency.USD)}
    assert res['total_rub'] == {0: Money(-35685.51, Currency.RUB), 1: Money(36545.46, Currency.RUB), 2: Money(-5097.93, Currency.RUB), 3: Money(-46427.85, Currency.RUB), 4: Money(52258.50, Currency.RUB)}
    assert res['profit_rub'] == {0: Money(0, Currency.RUB), 1: Money(859.95, Currency.RUB), 2: Money(0, Currency.RUB), 3: Money(0, Currency.RUB), 4: Money(732.72, Currency.RUB)}

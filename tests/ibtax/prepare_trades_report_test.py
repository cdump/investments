import datetime
from decimal import Decimal

from investments.currency import Currency
from investments.data_providers.cbr import ExchangeRatesRUB
from investments.ibtax.ibtax import prepare_trades_report
from investments.money import Money
from investments.ticker import Ticker, TickerKind
from investments.trades_fifo import FinishedTrade
from tests.trades_fifo_test import test_trades_precision


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
    cbr_client = ExchangeRatesRUB()

    res: dict = prepare_trades_report(trades, cbr_client).to_dict()

    assert res['settle_rate'] == {
        0: Money(63.1385, Currency.RUB),
        1: Money(63.9091, Currency.RUB),
        2: Money(63.1385, Currency.RUB),
        3: Money(63.9091, Currency.RUB),
        4: Money(63.9490, Currency.RUB)
    }
    assert res['fee_rate'] == {
        0: Money(62.3934, Currency.RUB),
        1: Money(63.0359, Currency.RUB),
        2: Money(62.3934, Currency.RUB),
        3: Money(63.0359, Currency.RUB),
        4: Money(63.4720, Currency.RUB)
    }
    assert res['fee'] == {
        0: Money('-0.863625', Currency.USD),
        1: Money('-0.9167399999999999999999999997', Currency.USD),
        2: Money('-0.123375', Currency.USD),
        3: Money('-0.9', Currency.USD),
        4: Money('-1.018126740', Currency.USD)
    }
    assert res['total'] == {
        0: Money('-565.203625', Currency.USD),
        1: Money('571.82326', Currency.USD),
        2: Money('-80.743375', Currency.USD),
        3: Money('-726.48', Currency.USD),
        4: Money('817.181873260', Currency.USD)
    }
    assert res['total_rub'] == {
        0: Money('-35685.465590075', Currency.RUB),
        1: Money('36545.510403034', Currency.RUB),
        2: Money('-5097.923655725', Currency.RUB),
        3: Money('-46427.897088', Currency.RUB),
        4: Money('52258.44925955872', Currency.RUB)
    }
    assert res['profit_rub'] == {
        0: Money(0, Currency.RUB),
        1: Money('860.044812959', Currency.RUB),
        2: Money(0, Currency.RUB),
        3: Money(0, Currency.RUB),
        4: Money('732.62851583372', Currency.RUB)
    }


def test_precision():
    """
    Отладка проблемы с потерей точности при расчётах финансового результата.

    """

    test_case = test_trades_precision()

    res: dict = prepare_trades_report(test_case, ExchangeRatesRUB()).to_dict()

    assert [x.amount for x in res['total_rub'].values()] == [
        Decimal('-51586.552320'),  # Расход: (80.62 * 10 * 63.9091) + (0.1 * 10 * 63.0359) = 51586.55232₽
        Decimal('52258.4492595587200'),  # Доход: (81.82 * 10 * 63.9490) - (0.101812674 * 10 * 63.4720) = 52258.4492595587200₽
    ]

    assert [x.amount for x in res['profit_rub'].values()] == [
        Decimal('0'),
        Decimal('671.8969395587200'),  # Финансовый результат: 52258.4492595587200 - 51586.552320 = 671.896939559₽
    ]

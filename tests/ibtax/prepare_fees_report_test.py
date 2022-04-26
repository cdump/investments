import datetime
from decimal import Decimal

from investments.currency import Currency
from investments.money import Money
from investments.fees import Fee
from investments.data_providers.cbr import ExchangeRatesRUB
from investments.ibtax.ibtax import prepare_fees_report


def test_simple_fees_verbose():
    fees = [
        Fee(date=datetime.datetime(2020, 1, 30, 0, 0), amount=Money(0.01, Currency.USD), description='Other Fees'),
        Fee(date=datetime.datetime(2020, 1, 30, 0, 0), amount=Money(-0.01, Currency.USD), description='Other Fees'),
    ]
    cbr_client = ExchangeRatesRUB()
    res: dict = prepare_fees_report(fees, cbr_client, True).to_dict()
    assert res['rate'] == {
        0: Money(62.3934, Currency.RUB),
        1: Money(62.3934, Currency.RUB)
    }
    assert res['amount_rub'] == {
        0: Money(0.623934, Currency.RUB),
        1: Money(-0.623934, Currency.RUB)
    }


def test_simple_fees_no_verbose():
    fees = [
        Fee(date=datetime.datetime(2020, 1, 30, 0, 0), amount=Money(0.01, Currency.USD), description='Other Fees'),
        Fee(date=datetime.datetime(2020, 1, 30, 0, 0), amount=Money(-0.01, Currency.USD), description='Other Fees'),
    ]
    cbr_client = ExchangeRatesRUB()
    res: dict = prepare_fees_report(fees, cbr_client, False).to_dict()
    assert res['rate'] == {}
    assert res['amount_rub'] == {}


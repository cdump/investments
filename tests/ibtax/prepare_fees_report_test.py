import datetime

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
    assert res['rate'] == {0: Money(62.3934, Currency.RUB), 1: Money(62.3934, Currency.RUB)}
    assert res['amount_rub'] == {0: Money(0.623934, Currency.RUB), 1: Money(-0.623934, Currency.RUB)}


def test_simple_fees_no_verbose():
    fees = [
        Fee(date=datetime.datetime(2020, 1, 30, 0, 0), amount=Money(0.01, Currency.USD), description='Other Fees'),
        Fee(date=datetime.datetime(2020, 1, 30, 0, 0), amount=Money(-0.01, Currency.USD), description='Other Fees'),
    ]
    cbr_client = ExchangeRatesRUB()
    res: dict = prepare_fees_report(fees, cbr_client, False).to_dict()
    assert res['rate'] == {}
    assert res['amount_rub'] == {}


def test_same_sign_fees_are_not_treated_as_reversals():
    fees = [
        Fee(date=datetime.date(2024, 1, 1), amount=Money(-1, Currency.RUB), description='Same fee'),
        Fee(date=datetime.date(2024, 1, 1), amount=Money(-1, Currency.RUB), description='Same fee'),
    ]

    res = prepare_fees_report(fees, ExchangeRatesRUB(), False)

    assert res['amount'].tolist() == [Money(-1, Currency.RUB), Money(-1, Currency.RUB)]


def test_fee_reversals_are_matched_one_to_one():
    fees = [
        Fee(date=datetime.date(2024, 1, 1), amount=Money(-1, Currency.RUB), description='Same fee'),
        Fee(date=datetime.date(2024, 1, 1), amount=Money(-1, Currency.RUB), description='Same fee'),
        Fee(date=datetime.date(2024, 1, 1), amount=Money(1, Currency.RUB), description='Same fee'),
    ]

    res = prepare_fees_report(fees, ExchangeRatesRUB(), False)

    assert res['amount'].tolist() == [Money(-1, Currency.RUB)]

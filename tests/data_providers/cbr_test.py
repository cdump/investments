from datetime import datetime, date
from decimal import Decimal

import pytest  # type: ignore
from requests.exceptions import ConnectionError

from investments.currency import Currency
from investments.data_providers.currency_rates.cbr import ExchangeRates
from investments.money import Money

test_cases = [
    (datetime(2015, 1, 15), Currency.USD, Money('66.0983', Currency.RUB)),
    (datetime(2015, 3, 7), Currency.USD, Money('59.9938', Currency.RUB)),
    (datetime(2015, 3, 8), Currency.USD, Money('59.9938', Currency.RUB)),
    (datetime(2020, 3, 31), Currency.USD, Money('77.7325', Currency.RUB)),
    (datetime(2020, 1, 9), Currency.USD, Money('61.9057', Currency.RUB)),
    (date(2020, 2, 4), Currency.EUR, Money('70.7921', Currency.RUB)),

    (datetime(2015, 3, 7), Currency.EUR, Money('66.1012', Currency.RUB)),
    (datetime(2015, 1, 15), Currency.EUR, Money('77.9629', Currency.RUB)),
    (datetime(2015, 3, 8), Currency.EUR, Money('66.1012', Currency.RUB)),
    (datetime(2020, 3, 31), Currency.EUR, Money('85.7389', Currency.RUB)),
]


@pytest.mark.parametrize('trade_date,currency,expect_rate', test_cases)
def test_exchange_rates_rub(trade_date: datetime, currency: Currency, expect_rate: Money):
    try:
        p = ExchangeRates(from_currency=currency, year_from=2015, cache_dir=None)
    except ConnectionError as ex:
        pytest.skip(f'connection error: {ex}')
        return

    rate = p.get_rate(trade_date)
    assert rate == expect_rate, f'{trade_date}: {rate} != {expect_rate}'


def test_convert_to_rub():
    client_usd = ExchangeRates(Currency.USD)
    rate_date = datetime(2020, 3, 31)
    expected_rate = client_usd.get_rate(rate_date)
    assert expected_rate.amount == Decimal('77.7325')

    test_usd = Money(10.98, Currency.USD)
    res = client_usd.convert_to_base_currency(test_usd, rate_date)

    assert res.amount == Decimal('853.50285')
    assert res.currency == Currency.RUB

    test_rub = Money(Decimal('858.3066'), Currency.RUB)
    res = client_usd.convert_to_base_currency(test_rub, rate_date)

    assert res.amount == Decimal('858.3066')
    assert res.currency == Currency.RUB


def test_unknown_currency():
    with pytest.raises(NotImplementedError) as ex:
        ExchangeRates(from_currency=20, year_from=2015, cache_dir=None)
    assert 'only USD and EUR currencies supported' in str(ex.value)

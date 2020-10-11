from datetime import datetime

import pytest  # type: ignore
from requests.exceptions import ConnectionError

from investments.currency import Currency
from investments.data_providers.cbr import ExchangeRatesRUB
from investments.money import Money

test_cases = [
    (datetime(2015, 1, 15), Currency.USD, Money('66.0983', Currency.RUB)),
    (datetime(2015, 3, 7), Currency.USD, Money('59.9938', Currency.RUB)),
    (datetime(2015, 3, 8), Currency.USD, Money('59.9938', Currency.RUB)),
    (datetime(2020, 3, 31), Currency.USD, Money('77.7325', Currency.RUB)),
    (datetime(2015, 3, 7), Currency.EUR, Money('66.1012', Currency.RUB)),
    (datetime(2015, 1, 15), Currency.EUR, Money('77.9629', Currency.RUB)),
    (datetime(2015, 3, 8), Currency.EUR, Money('66.1012', Currency.RUB)),
    (datetime(2020, 3, 31), Currency.EUR, Money('85.7389', Currency.RUB)),
]


@pytest.mark.parametrize('trade_date,currency,expect_rate', test_cases)
def test_exchange_rates_rub(trade_date: datetime, currency: Currency, expect_rate: Money):
    try:
        p = ExchangeRatesRUB(currency=currency, year_from=2015, cache_dir=None)
    except ConnectionError as ex:
        pytest.skip(f'connection error: {ex}')
        return

    rate = p.get_rate(trade_date)
    assert rate == expect_rate, f'{trade_date}: {rate} != {expect_rate}'

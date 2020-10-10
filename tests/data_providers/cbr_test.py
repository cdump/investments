from datetime import datetime

import pytest  # type: ignore
from requests.exceptions import ConnectionError

from investments.currency import Currency
from investments.data_providers.cbr import ExchangeRatesRUB
from investments.money import Money

test_cases = [
    (datetime(2015, 1, 15), Money('66.0983', Currency.RUB)),
    (datetime(2015, 3, 7), Money('59.9938', Currency.RUB)),
    (datetime(2015, 3, 8), Money('59.9938', Currency.RUB)),
    (datetime(2020, 1, 9), Money('61.9057', Currency.RUB)),
    (datetime(2020, 3, 31), Money('77.7325', Currency.RUB)),
]


@pytest.mark.parametrize("trade_date,expect_rate", test_cases)
def test_exchange_rates_rub(trade_date: datetime, expect_rate: Money):
    try:
        p = ExchangeRatesRUB(year_from=2015, cache_dir=None)
    except ConnectionError as ex:
        pytest.skip(f'connection error: {ex}')
        return

    rate = p.get_rate(trade_date)
    assert rate == expect_rate, f'{trade_date}: {rate} != {expect_rate}'

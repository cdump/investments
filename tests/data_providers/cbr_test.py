from datetime import datetime

from investments.currency import Currency
from investments.data_providers.cbr import ExchangeRatesRUB
from investments.money import Money


def test_exchange_rates_rub():
    test_cases = [
        (datetime(2015, 1, 15), Money('66.0983', Currency.RUB)),
        (datetime(2015, 3, 7), Money('59.9938', Currency.RUB)),
        (datetime(2015, 3, 8), Money('59.9938', Currency.RUB)),
        (datetime(2020, 3, 31), Money('77.7325', Currency.RUB)),
    ]

    p = ExchangeRatesRUB(year_from=2015, cache_dir=None)
    for tc in test_cases:
        rate = p.get_rate(tc[0])
        assert rate == tc[1], f'{tc[0]}: {rate} != {tc[1]}'

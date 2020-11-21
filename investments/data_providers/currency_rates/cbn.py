"""
Клиент к API CBN ЧР с курсами валют относительно чешской кроны.

Необходим для перевода сумм сделок в чешскую крону по курсу ЧНБ (Česká národní banka) на дату поставки в соответствии с НК ЧР

"""
from investments.data_providers.currency_rates import ExchangeRateClient


class ExchangeRates(ExchangeRateClient):
    pass
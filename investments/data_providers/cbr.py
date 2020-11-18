"""
Клиент к API ЦБ РФ с курсами валют относительно рубля.

Необходим для перевода сумм сделок в рубли по курсу ЦБ на дату поставки в соответствии с НК РФ

"""

import datetime
import logging
import xml.etree.ElementTree as ET  # type: ignore
from typing import List, Tuple

import pandas  # type: ignore
import requests

from investments.currency import Currency
from investments.data_providers.cache import DataFrameCache
from investments.money import Money


class ExchangeRatesRUB:
    currency_codes = {
        Currency.USD: 'R01235',
        Currency.EUR: 'R01239',
    }
    currency: Currency
    _df: pandas.DataFrame

    def __init__(self, currency: Currency, year_from: int = 2000, cache_dir: str = None):
        self.currency = currency

        currency_code = self.currency_codes.get(self.currency)
        if not currency_code:
            raise NotImplementedError(f'only USD and EUR currencies supported [{self.currency} requested]')

        cache = DataFrameCache(cache_dir, f'cbrates_{currency_code}_since{year_from}.cache', datetime.timedelta(days=1))
        df = cache.get()
        if df is not None:
            logging.info('CBR cache hit')
            self._df = df
            return

        end_date = (datetime.datetime.utcnow() + datetime.timedelta(days=1)).strftime('%d/%m/%Y')
        r = requests.get(f'http://www.cbr.ru/scripts/XML_dynamic.asp?date_req1=01/01/{year_from}&date_req2={end_date}&VAL_NM_RQ={currency_code}')

        tree = ET.fromstring(r.text)

        rates_data: List[Tuple[datetime.date, Money]] = []
        for rec in tree.findall('Record'):
            assert rec.get('Id') == currency_code
            d = datetime.datetime.strptime(rec.attrib['Date'], '%d.%m.%Y').date()
            v = rec.findtext('Value')
            assert isinstance(v, str)
            rates_data.append((d, Money(v.replace(',', '.'), Currency.RUB)))

        df = pandas.DataFrame(rates_data, columns=['date', 'rate'])
        df.set_index(['date'], inplace=True)
        today = datetime.datetime.utcnow().date()
        df = df.reindex(pandas.date_range(df.index.min(), today))
        df['rate'].fillna(method='pad', inplace=True)

        cache.put(df)
        self._df = df

    @property
    def dataframe(self) -> pandas.DataFrame:
        return self._df

    def get_rate(self, dt: datetime.datetime) -> Money:
        return self._df.loc[dt].item()

    def convert_to_rub(self, source: Money, rate_date: datetime.datetime) -> Money:
        assert isinstance(rate_date, datetime.datetime)

        if source.currency == Currency.RUB:
            return Money(source.amount, Currency.RUB)

        rate = self.get_rate(rate_date)
        return Money(source.amount * rate.amount, rate.currency)

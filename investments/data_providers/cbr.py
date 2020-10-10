import datetime
import logging
import xml.etree.ElementTree as ET  # type: ignore
from typing import List, Optional, Tuple

import pandas  # type: ignore
import requests

from investments.currency import Currency
from investments.data_providers.cache import DataFrameCache
from investments.money import Money

cbr_client = None


class ExchangeRatesRUB:
    USD_CODE = 'R01235'

    def __init__(self, year_from: int = 2000, year_end: int = 2030, cache_dir: str = None):
        cache = DataFrameCache(cache_dir, f'cbrates_since{year_from}.cache', datetime.timedelta(days=1))
        df = cache.get()
        if df is not None:
            logging.info('CBR cache hit')
            self._df = df
            return

        # todo multi currency
        r = requests.get(f'http://www.cbr.ru/scripts/XML_dynamic.asp?date_req1=01/01/{year_from}&date_req2=01/01/{year_end}&VAL_NM_RQ={self.USD_CODE}')
        tree = ET.fromstring(r.text)

        rates_data: List[Tuple[datetime.date, Money]] = []
        for rec in tree.findall('Record'):
            assert rec.get('Id') == self.USD_CODE, 'only USD supported'
            d = datetime.datetime.strptime(rec.attrib['Date'], '%d.%m.%Y').date()
            v = rec.findtext('Value')
            assert isinstance(v, str)
            rates_data.append((d, Money(v.replace(',', '.'), Currency.RUB)))

        df = pandas.DataFrame(rates_data, columns=['date', 'rate'])
        df.set_index(['date'], inplace=True)
        # df = df.reindex(pandas.date_range(df.index.min(), df.index.max()))
        today = datetime.datetime.utcnow().date()
        df = df.reindex(pandas.date_range(df.index.min(), today))
        df['rate'].fillna(method='pad', inplace=True)

        cache.put(df)
        self._df = df

    @property
    def dataframe(self) -> pandas.DataFrame:
        return self._df

    def get_rate(self, date: datetime.date) -> Money:
        return self._df.loc[date].item()


def init_client(client: Optional[ExchangeRatesRUB] = None):
    global cbr_client
    if not client:
        client = ExchangeRatesRUB()
    cbr_client = client  # noqa: WPS442


def get_client() -> ExchangeRatesRUB:
    global cbr_client
    if cbr_client is None:
        init_client()
    return cbr_client  # type: ignore


def convert_to_rub(source: Money, rate_date: datetime.date) -> Money:
    if source.currency == Currency.RUB:
        return Money(source.amount, Currency.RUB)

    # todo multi currency
    rate = get_client().get_rate(rate_date)
    return Money(source.amount * rate.amount, rate.currency)

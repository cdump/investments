import datetime
import xml.etree.ElementTree as ET  # type: ignore
from typing import List, Tuple

import pandas  # type: ignore
import requests

from investments.currency import Currency
from investments.data_providers.cache import DataFrameCache
from investments.money import Money


class ExchangeRatesRUB:
    def __init__(self, year_from: int = 2000, cache_dir: str = None):
        cache = DataFrameCache(cache_dir, f'cbrates_since{year_from}.cache', datetime.timedelta(days=1))
        df = cache.get()
        if df is not None:
            self._df = df
            return

        r = requests.get(f'http://www.cbr.ru/scripts/XML_dynamic.asp?date_req1=01/01/{year_from}&date_req2=01/01/2030&VAL_NM_RQ=R01235')
        tree = ET.fromstring(r.text)

        rates_data: List[Tuple[datetime.date, Money]] = []
        for rec in tree.findall('Record'):
            assert rec.get('Id') == 'R01235', 'only USD(R01235) supported'
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

    def dataframe(self) -> pandas.DataFrame:
        return self._df

    def get_rate(self, date: datetime.date) -> Money:
        return self._df.loc[date].item()

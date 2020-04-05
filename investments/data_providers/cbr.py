import datetime
import os
import xml.etree.ElementTree as ET

import pandas
import requests

from investments.currency import Currency
from investments.money import Money


class ExchangeRatesRUB(object):
    def __init__(self, year_from: int = 2000, cache_dir: str = None):
        today = datetime.datetime.utcnow().date()
        cache_file = None
        if cache_dir is not None:
            os.makedirs(cache_dir, exist_ok=True)
            cache_file = os.path.join(cache_dir, f'cbrates_since{year_from}.cache')
            try:
                mdate = datetime.datetime.utcfromtimestamp(os.path.getmtime(cache_file)).date()
            except FileNotFoundError:
                pass
            else:
                if today == mdate:
                    self._df = pandas.read_pickle(cache_file)
                    return

        r = requests.get(f'http://www.cbr.ru/scripts/XML_dynamic.asp?date_req1=01/01/{year_from}&date_req2=01/01/2030&VAL_NM_RQ=R01235')
        tree = ET.fromstring(r.text)

        rates_data = []
        for rec in tree.findall('Record'):
            assert rec.get('Id') == 'R01235', 'only USD(R01235) supported'
            d = datetime.datetime.strptime(rec.get('Date'), '%d.%m.%Y').date()
            v = rec.find('Value').text.replace(',', '.')
            rates_data.append((d, Money(v, Currency.RUB)))

        df = pandas.DataFrame(rates_data, columns=['date', 'rate'])
        df.set_index(['date'], inplace=True)
        # df = df.reindex(pandas.date_range(df.index.min(), df.index.max()))
        df = df.reindex(pandas.date_range(df.index.min(), today))
        df['rate'].fillna(method='pad', inplace=True)

        if cache_file is not None:
            df.to_pickle(cache_file)

        self._df = df

    def dataframe(self) -> pandas.DataFrame:
        return self._df

    def get_rate(self, date: datetime.date) -> Money:
        return self._df.loc[date].item()

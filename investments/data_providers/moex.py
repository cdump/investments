import asyncio
import datetime
from typing import Optional

import aiomoex  # type: ignore
import pandas  # type: ignore

from investments.data_providers.cache import DataFrameCache
from investments.ticker import Ticker


async def async_get_board_candles(ticker: Ticker, cache_dir: Optional[str], start: str, end: Optional[str], interval: int):
    cache_file = f'moex_candles_{ticker.symbol}_{start}_{end if end else "now"}_{interval}.cache'
    ttl = datetime.timedelta(days=1)

    cache = DataFrameCache(cache_dir, cache_file, ttl)
    df = cache.get()
    if df is not None:
        return df

    async with aiomoex.ISSClientSession():
        engine, market, board = '', '', ''

        resp = await aiomoex.find_securities(ticker.symbol, columns=('secid', 'name', 'group', 'primary_boardid'))
        for x in resp:
            if x['secid'] != ticker.symbol:
                continue
            engine, market = x['group'].split('_')
            board = x['primary_boardid']

        if engine == '':
            raise Exception(f'unknown ticker {ticker}')

        rdata = await aiomoex.get_board_candles(ticker.symbol, start=start, end=end, interval=interval, engine=engine, market=market, board=board)
        df = pandas.DataFrame(rdata)
        df.set_index('begin', inplace=True)
        df.drop(['value'], axis=1, inplace=True)

        cache.put(df)
        return df


def get_board_candles(ticker: Ticker, cache_dir: str = None, start='2016-01-01', end=None, interval=24):
    return asyncio.run(async_get_board_candles(ticker, cache_dir, start, end, interval))

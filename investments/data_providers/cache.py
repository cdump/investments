import datetime
import os
from typing import Optional

import pandas  # type: ignore


class DataFrameCache:
    def __init__(self, cache_dir: Optional[str], cache_file: str, ttl: datetime.timedelta):
        if cache_dir is None:
            self._cache_file = None
            return

        assert cache_file is not None
        assert ttl is not None
        os.makedirs(cache_dir, exist_ok=True)

        self._cache_file = os.path.join(cache_dir, cache_file)
        self._ttl = ttl

    def get(self) -> Optional[pandas.DataFrame]:
        if self._cache_file is None:
            return None
        try:
            mtime = os.path.getmtime(self._cache_file)
        except FileNotFoundError:
            return None

        if (datetime.datetime.utcnow() - datetime.datetime.utcfromtimestamp(mtime)) > self._ttl:
            return None
        return pandas.read_pickle(self._cache_file)

    def put(self, df: pandas.DataFrame):
        if self._cache_file is None:
            return None
        df.to_pickle(self._cache_file)

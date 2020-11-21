import datetime
from abc import ABC, abstractmethod

from investments.money import Money


class ExchangeRateClient(ABC):

    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def get_rate(self, dt: datetime.date) -> Money:
        pass

    @abstractmethod
    def convert_to_base_currency(self, source: Money, rate_date: datetime.date) -> Money:
        pass

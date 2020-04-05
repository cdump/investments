from enum import Enum


class Currency(Enum):
    USD = 1
    RUB = 2

    @staticmethod
    def parse(strval: str):
        if strval in {'$', 'USD'}:
            return Currency.USD
        if strval in {'₽', 'RUB'}:
            return Currency.RUB
        raise ValueError

    def __str__(self):
        if self == Currency.USD:
            return '$'
        elif self == Currency.RUB:
            return '₽'
        return self.__repr__(self)

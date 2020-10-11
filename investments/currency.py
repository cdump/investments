from enum import Enum


class Currency(Enum):
    USD = 1
    RUB = 2
    EUR = 3

    @staticmethod
    def parse(strval: str):
        if strval in {'$', 'USD'}:
            return Currency.USD
        if strval in {'₽', 'RUB'}:
            return Currency.RUB
        if strval in {'€', 'EUR'}:
            return Currency.EUR
        raise ValueError(strval)

    def __str__(self):
        if self == Currency.USD:
            return '$'
        elif self == Currency.RUB:
            return '₽'
        elif self == Currency.EUR:
            return '€'
        return self.__repr__(self)

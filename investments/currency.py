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

    def iso_numeric_code(self) -> str:
        """
        Код валюты в соответствии с общероссийским классификатором валют (ОК (МК (ИСО 4217) 003-97) 014-2000).

        see https://classifikators.ru/okv

        Raises:
            ValueError: if currency is unsupported

        """
        if self == Currency.USD:
            return '840'
        elif self == Currency.RUB:
            return '643'
        elif self == Currency.EUR:
            return '978'
        raise ValueError(self)

from decimal import Decimal
from typing import Union

from investments.currency import Currency


class Money(object):
    def __init__(self, amount: Union[Decimal, str, float], currency: Currency):
        self._amount = amount if isinstance(amount, Decimal) else Decimal(str(amount))
        self._currency = currency

    @property
    def currency(self) -> Currency:
        return self._currency

    @property
    def amount(self) -> Decimal:
        return self._amount

    def convert_to(self, rate: 'Money') -> 'Money':
        return Money(self._amount * rate.amount, rate.currency)

    def round(self, digits=0) -> 'Money':  # noqa: WPS125
        return Money(round(self._amount, digits), self._currency)

    def __repr__(self):
        return f'Money({self._amount}, {self._currency})'

    def __str__(self):
        return f'{self._amount}{self._currency}'

    def __add__(self, other: 'Money') -> 'Money':
        if not isinstance(other, Money):
            return NotImplemented
        assert self._currency == other.currency
        return Money(self._amount + other.amount, self._currency)

    def __sub__(self, other: 'Money') -> 'Money':
        if not isinstance(other, Money):
            return NotImplemented
        assert self._currency == other.currency
        return Money(self._amount - other.amount, self._currency)

    def __mul__(self, mul: int):
        if isinstance(mul, int):
            return Money(self._amount * mul, self._currency)
        return NotImplemented

    def __rmul__(self, mul: int):
        return self.__mul__(mul)

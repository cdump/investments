from decimal import Decimal
from typing import Union

from investments.currency import Currency


class Money:
    def __init__(self, amount: Union[Decimal, str, float, int], currency: Currency):
        self._amount = amount if isinstance(amount, Decimal) else Decimal(str(amount))
        self._currency = currency

    @property
    def currency(self) -> Currency:
        return self._currency

    @property
    def amount(self) -> Decimal:
        return self._amount

    def convert_to(self, rate: 'Money') -> 'Money':
        if self.currency == rate.currency:
            return Money(self.amount, self.currency)
        return Money(self.amount * rate.amount, rate.currency)

    def round(self, digits=0) -> 'Money':  # noqa: WPS125
        return Money(round(self._amount, digits), self._currency)

    def __repr__(self):
        return f'Money({self._amount}, {self._currency})'

    def __str__(self):
        return f'{self._amount}{self._currency}'

    def __eq__(self, other) -> bool:
        if isinstance(other, Money):
            return self.amount == other.amount and self.currency == other.currency
        return False

    def __lt__(self, other) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        if self._currency != other.currency:
            raise TypeError(f'different currencies: {self._currency} & {other.currency}')
        return self.amount < other.amount

    def __add__(self, other) -> 'Money':
        if isinstance(other, int) and other == 0:
            # useful for sum([x.amount for x in ..])
            return self
        if not isinstance(other, Money):
            return NotImplemented
        if self._currency != other.currency:
            raise TypeError(f'different currencies: {self._currency} & {other.currency}')
        return Money(self._amount + other.amount, self._currency)

    def __radd__(self, other) -> 'Money':
        return self.__add__(other)

    def __sub__(self, other) -> 'Money':
        if isinstance(other, int) and other == 0:
            return self
        if not isinstance(other, Money):
            return NotImplemented
        if self._currency != other.currency:
            raise TypeError(f'different currencies: {self._currency} & {other.currency}')
        return Money(self._amount - other.amount, self._currency)

    def __rsub__(self, other) -> 'Money':
        return -1 * self.__sub__(other)

    def __mul__(self, mul):
        if isinstance(mul, int):
            return Money(self._amount * mul, self._currency)
        return NotImplemented

    def __rmul__(self, mul: int):
        return self.__mul__(mul)

    def __truediv__(self, d):
        if isinstance(d, int):
            return Money(self._amount / d, self._currency)

        if isinstance(d, Money):
            if self._currency != d.currency:
                raise TypeError(f'different currencies: {self._currency} & {d.currency}')
            return float(self._amount / d.amount)

        return NotImplemented

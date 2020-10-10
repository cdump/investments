from datetime import datetime
from decimal import Decimal

import pytest

from investments.currency import Currency
from investments.data_providers.cbr import get_client, convert_to_rub
from investments.money import Money


def test_money():
    usd1 = Money(1, Currency.USD)
    usd7 = Money(7, Currency.USD)

    rub1 = Money(1, Currency.RUB)
    rub3 = Money(3, Currency.RUB)
    rub5 = Money(5, Currency.RUB)

    assert usd1 != rub1
    assert usd1 != usd7
    assert usd1 == Money(1, Currency.USD)

    assert rub1 < rub3
    with pytest.raises(TypeError):
        r = rub1 < usd7

    with pytest.raises(TypeError):
        r = usd1 + rub3

    with pytest.raises(TypeError):
        r = usd1 + 1

    r = usd1 + usd7
    assert r.amount == 8
    assert r.currency == Currency.USD

    r = rub5 - rub3
    assert r.amount == 2
    assert r.currency == Currency.RUB


def test_money_zero():
    rub3 = Money(3, Currency.RUB)

    r = rub3 + 0
    assert r == rub3

    r = 0 + rub3
    assert r == rub3

    r = rub3 - 0
    assert r == rub3

    r = 0 - rub3
    assert r.amount == -1 * rub3.amount
    assert r == -1 * rub3

    with pytest.raises(TypeError):
        r = rub3 + 3

    with pytest.raises(TypeError):
        r = 3 + rub3

    with pytest.raises(TypeError):
        r = rub3 - 3

    with pytest.raises(TypeError):
        r = 3 - rub3


def test_money_float():
    v = 0.3
    v_expect = 0.9

    m = Money(v, Currency.USD)
    m_expect = Money(v_expect, Currency.USD)

    vsum = v + v + v
    assert vsum != v_expect

    msum = Money(v + v + v, Currency.USD)
    assert msum.amount != m_expect.amount

    msum = m + m + m
    assert msum.amount == m_expect.amount


def test_convert_to_rub():
    rate_date = datetime(2020, 3, 31)
    get_client().get_rate(rate_date)  # 77.7325₽

    test_usd = Money(10.98, Currency.USD)
    res = convert_to_rub(test_usd, rate_date)

    assert res.amount == Decimal('853.50285')
    assert res.currency == Currency.RUB

    test_rub = Money(Decimal('858.3066'), Currency.RUB)
    res = convert_to_rub(test_rub, rate_date)

    assert res.amount == Decimal('858.3066')
    assert res.currency == Currency.RUB

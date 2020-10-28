import pytest

from investments.currency import Currency
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

    with pytest.raises(TypeError):
        r = rub3 / usd1

    r = rub5 / rub1
    assert isinstance(r, float)
    assert r == 5

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

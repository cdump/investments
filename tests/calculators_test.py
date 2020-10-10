from investments.currency import Currency
from investments.calculators import compute_total_cost
from investments.money import Money


def test_compute_total_cost():
    buy_cost = compute_total_cost(10, Money(1.7, Currency.USD), Money(-0.1, Currency.USD))
    assert buy_cost.amount == -1 * ((10 * 1.7) + (10 * 0.1))
    assert buy_cost.currency is Currency.USD

    sell_cost = compute_total_cost(-10, Money(1.7, Currency.USD), Money(-0.1, Currency.USD))
    assert sell_cost.amount == (10 * 1.7) - (10 * 0.1)
    assert sell_cost.currency is Currency.USD

"""Калькулятор цены сделки с учётом комиссий."""

from investments.money import Money


def compute_total_cost(quantity: int, price_per_piece: Money, fee_per_piece: Money) -> Money:
    """Полная сумма сделки (цена +/- комиссии)."""
    assert price_per_piece.currency is fee_per_piece.currency
    fee = abs(quantity) * abs(fee_per_piece)
    price = abs(quantity) * price_per_piece
    if quantity > 0:
        # buy trade
        return -1 * (price + fee)

    # sell trade
    return price - fee

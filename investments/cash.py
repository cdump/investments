from typing import NamedTuple

from investments.money import Money


class Cash(NamedTuple):
    """
    Движения денежных средств по счёту.

    По итогам года нужно отчитаться о всех зачислениях/списаниях по счёту у иностранного брокера в соответствии со статьёй 12 173-ФЗ «О валютном регулировании»

    """

    description: str
    amount: Money

    def __str__(self):
        return f'Cash ({self.amount} {self.description})'

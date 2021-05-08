from enum import Enum, unique
from typing import Tuple


@unique
class Currency(Enum):
    """
    Список поддерживаемых валют следует смотреть на официальном сайте IB.

    @see https://www.interactivebrokers.com/en/index.php?f=1323

    """

    USD = (('$', 'USD'), '840', 'R01235')
    RUB = (('₽', 'RUB', 'RUR'), '643', '')
    EUR = (('€', 'EUR'), '978', 'R01239')

    def __init__(self, aliases: Tuple[str], iso_code: str, cbr_code: str):
        self._iso_code = iso_code
        self._cbr_code = cbr_code
        self.aliases = aliases

    @staticmethod
    def parse(strval: str):
        try:
            return [item for _, item in Currency.__members__.items() if strval in item.aliases][0]
        except IndexError:
            raise ValueError(strval)

    def __str__(self):
        return str(self.aliases[0])

    @property
    def iso_numeric_code(self) -> str:
        """
        Код валюты в соответствии с общероссийским классификатором валют (ОК (МК (ИСО 4217) 003-97) 014-2000).

        @see https://classifikators.ru/okv

        """
        return self._iso_code

    @property
    def cbr_code(self) -> str:
        """
        Код валюты в соответствии с классификатором ЦБ РФ.

        @see http://www.cbr.ru/scripts/XML_daily_eng.asp?date_req=22/01/2020

        """
        return self._cbr_code

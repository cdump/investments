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
    AUD = (('AUD',), '036', 'R01010')
    GBP = (('GBP',), '826', 'R01035')
    CAD = (('CAD',), '124', 'R01350')
    CZK = (('CZK',), '203', 'R01760')
    DKK = (('DKK',), '208', 'R01215')
    HKD = (('HKD',), '344', 'R01200')
    HUF = (('HUF',), '348', 'R01135')
    YEN = (('YEN',), '392', 'R01820')
    KRW = (('KRW',), '410', 'R01815')
    NOK = (('NOK',), '578', 'R01535')
    PLN = (('PLN',), '985', 'R01565')
    SGD = (('SGD',), '702', 'R01625')
    ZAR = (('ZAR',), '710', 'R01810')
    SEK = (('SEK',), '752', 'R01770')
    CHF = (('CHF',), '756', 'R01775')
    TRY = (('TRY',), '949', 'R01700J')

    # unknown currency for cbr.ru
    # CNH = (('CNH',), 'unknown', 'unknown')
    # ILS = (('ILS',), '376', 'unknown')
    # MXN = (('MXN',), '484', 'unknown')
    # NZD = (('NZD',), '554', 'unknown')

    def __init__(self, aliases: Tuple[str], iso_code: str, cbr_code: str):
        self._iso_code = iso_code
        self._cbr_code = cbr_code
        self.aliases = aliases

    @staticmethod
    def parse(search: str):
        try:
            return [
                currency_item for _, currency_item in Currency.__members__.items()  # noqa: WPS609
                if search in currency_item.aliases
            ][0]
        except IndexError:
            raise ValueError(search)

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

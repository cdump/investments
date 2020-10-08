import datetime
import re
import xml.etree.ElementTree as ET  # type: ignore
from typing import List, Optional

from investments.currency import Currency
from investments.dividend import Dividend
from investments.money import Money
from investments.ticker import Ticker, TickerKind
from investments.trade import Trade


def _parse_datetime(strval: str):
    return datetime.datetime.strptime(strval, '%Y-%m-%dT%H:%M:%S')


def _parse_tickerkind(strval: str):
    if strval in {'Акции', 'ПАИ'}:
        return TickerKind.Stock
    if strval == 'РДР':
        return TickerKind.Rdr
    if strval == 'Облигации':
        return TickerKind.Bond
    raise ValueError(strval)


class TickersStorageFR:
    def __init__(self, dividends_name_to_ticker):
        self._tickers = set()
        self._name_to_ticker = {}
        self._isin_to_ticker = {}
        self._grn_to_ticker = {}
        self._dividends_name_to_ticker = dividends_name_to_ticker or {}

    def put(self, *, symbol: str, kind: TickerKind, name: str, isin: str, grn: str):
        name = name.strip().lower()
        ticker = Ticker(symbol, kind)
        if ticker not in self._tickers:
            self._tickers.add(ticker)

            assert name not in self._name_to_ticker
            assert isin not in self._isin_to_ticker
            self._name_to_ticker[name] = ticker
            self._isin_to_ticker[isin] = ticker
            if grn != '':
                assert grn not in self._grn_to_ticker
                self._grn_to_ticker[grn] = ticker
        else:
            assert self._name_to_ticker[name] == ticker
            assert self._isin_to_ticker[isin] == ticker
            if grn != '':
                assert self._grn_to_ticker[grn] == ticker

    def get(self, grn: Optional[str] = None, isin: Optional[str] = None, name: Optional[str] = None) -> Ticker:
        if grn is not None:
            return self._grn_to_ticker[grn]

        if isin is not None:
            return self._isin_to_ticker[isin]

        assert name is not None
        name = name.strip().lower()
        return self._name_to_ticker[name]

    def get_by_dividend_name(self, name: str) -> Ticker:
        name = name.strip().lower()
        symbol = self._dividends_name_to_ticker.get(name)
        if symbol is None:
            raise KeyError(f'unsupported dividend name "{name}"')

        ticker = Ticker(symbol, TickerKind.Stock)
        assert ticker in self._tickers, f'unknown ticker "{name}" {ticker}'
        return ticker


class OpenBrokerFRParser:
    def __init__(self, dividends_name_to_ticker=None):
        self._trades = []
        self._dividends = []
        self._deposits_and_withdrawals = []
        self._tickers = TickersStorageFR(dividends_name_to_ticker)

    @property
    def trades(self) -> List:
        return self._trades

    @property
    def dividends(self) -> List:
        return self._dividends

    @property
    def deposits_and_withdrawals(self) -> List:
        return self._deposits_and_withdrawals

    def parse_xml(self, xml_file_name: str):
        tree = ET.parse(xml_file_name)
        self._parse_tickers(tree)
        self._parse_non_trade_operations(tree)
        self._parse_trades(tree)

        self._trades.sort(key=lambda x: x.datetime)
        self._dividends.sort(key=lambda x: x.date)
        self._deposits_and_withdrawals.sort(key=lambda x: x[0])

    def _parse_tickers(self, xml_tree: ET.ElementTree):
        for rec in xml_tree.findall('spot_portfolio_security_params/item'):
            f = rec.attrib
            self._tickers.put(
                symbol=f['ticker'],
                kind=_parse_tickerkind(f['security_type']),
                name=f['security_name'],
                isin=f['isin'],
                grn=f['security_grn_code'],
            )

    def _parse_cb_convertation(self, f):
        # WARNING: lost price information, do not use for tax calculation!
        qnty = int(f['quantity'])
        assert float(f['quantity']) == qnty
        ticker = self._tickers.get(name=f['security_name'])
        dt = _parse_datetime(f['operation_date'])
        self._trades.append(Trade(
            ticker=ticker,
            datetime=dt,
            settle_date=dt,
            quantity=qnty,
            price=Money(0, Currency.RUB),  # TODO: other currencies
            fee=Money(0, Currency.RUB),
        ))

    def _parse_money_payment(self, f, bonds_redemption):
        comment = f['comment']
        currency = Currency.parse(f['currency_code'])
        money_total = Money(f['amount'], currency)
        dt = _parse_datetime(f['operation_date'])

        m1 = re.match(r'^Выплата дохода клиент (\w+) дивиденды (?P<name>.*?) налог к удержанию (?P<tax>[0-9.]+) рублей$', comment)
        m2 = re.match(r'^Выплата дохода клиент (\w+) дивиденды (?P<name>.*?) налог 0.00 рублей удержан эмитентом$', comment)
        if m1 is not None or m2 is not None:
            if m1 is not None:
                name, tax = m1.group('name'), m1.group('tax')
            elif m2 is not None:
                name, tax = m2.group('name'), '0'
            self._dividends.append(Dividend(
                dtype='',
                ticker=self._tickers.get_by_dividend_name(name),
                date=dt.date(),
                amount=money_total,
                tax=Money(tax, currency),
            ))
            return

        m = re.match(r'^Выплата дохода клиент (\w+) \(Выкуп (?P<name>[^,]+), (?P<isin>\w+), количество (?P<quantity>\d+)\) налог не удерживается$', comment)
        if m is not None:
            isin, quantity_buyout = m.group('isin'), int(m.group('quantity'))
            self._trades.append(Trade(
                ticker=self._tickers.get(isin=isin),
                datetime=dt,
                settle_date=dt,
                quantity=-1 * quantity_buyout,
                price=money_total / quantity_buyout,
                fee=Money(0, currency),
            ))
            return

        m = re.match(r'^Выплата дохода клиент (\w+) \((?P<type>НКД \d+|Погашение) (?P<name>.*?)\) налог (к удержанию 0.00 рублей|не удерживается)$', comment)
        if m is not None:
            ticker = self._tickers.get(name=m.group('name'))
            if m.group('type').startswith('НКД'):
                # WARNING: do not use for tax calculation!
                for (price, quantity_coupons) in ((Money(0, currency), 1), (money_total, -1)):
                    self._trades.append(Trade(
                        ticker=ticker,
                        datetime=dt,
                        settle_date=dt,
                        quantity=quantity_coupons,
                        price=price,
                        fee=Money(0, currency),
                    ))
                return

            if m.group('type') == 'Погашение':
                key = (ticker, dt)
                quantity_redemption = bonds_redemption[key]
                self._trades.append(Trade(
                    ticker=ticker,
                    datetime=dt,
                    settle_date=dt,
                    quantity=quantity_redemption,
                    price=-1 * money_total / int(quantity_redemption),
                    fee=Money(0, currency),
                ))
                del bonds_redemption[key]
                return

            raise Exception(f'Unknown type {m.group("type")}')

        raise Exception(f'unsupported description {f}')

    def _parse_non_trade_operations(self, xml_tree: ET.ElementTree):
        bonds_redemption = {}

        for rec_non_trade in xml_tree.findall('spot_non_trade_security_operations/item'):
            f = rec_non_trade.attrib
            if 'Снятие ЦБ с учета. Погашение облигаций' in f['comment']:
                ticker = self._tickers.get(grn=f['grn_code'])
                key = (ticker, _parse_datetime(f['operation_date']))
                assert key not in bonds_redemption
                qnty = float(f['quantity'])
                assert float(int(qnty)) == qnty
                bonds_redemption[key] = int(qnty)

            elif '(Конвертация ЦБ)' in f['comment']:
                self._parse_cb_convertation(f)
            else:
                # print(f)
                # exit(1)
                pass

        for rec_money_ops in xml_tree.findall('spot_non_trade_money_operations/item'):
            f = rec_money_ops.attrib
            comment = f['comment']

            if any(comment.startswith(p) for p in ('Поставлены на торги средства клиента', 'Перевод  денежных средств с клиента')):
                self._deposits_and_withdrawals.append((
                    _parse_datetime(f['operation_date']),
                    Money(f['amount'], Currency.parse(f['currency_code'])),
                ))
                continue

            if comment.startswith('Выплата дохода клиент'):
                self._parse_money_payment(f, bonds_redemption)
                continue

            known_prefixes = [
                'Комиссия ',
                'Вознаграждение ',
                'Ежегодная комиссия за',
                'Возмещение за депозитарные услуги',
                'Депозитарная комиссия за операции',
                'Удержан налог на доход  по дивидендам',
                'Налог на доход за',
                'Удержан налог на доход с клиента ',
                'Перечисление дохода по акциям',
                'Возврат ошибочно удержанного налога с клиента',
                'Возврат излишне удержанного налога с клиента',
                'Проценты по предоставленным займам ЦБ',
                'Списаны средства клиента',
            ]
            if any(comment.startswith(p) for p in known_prefixes):
                continue

            raise Exception(f'unsupported description {f}')

        assert not bonds_redemption, 'not empty'

    def _parse_trades(self, xml_tree: ET.ElementTree):
        for rec in xml_tree.findall('spot_main_deals_conclusion/item'):
            f = rec.attrib
            qnty = -1 * float(f['sell_qnty']) if 'sell_qnty' in f else float(f['buy_qnty'])
            assert float(int(qnty)) == qnty

            ticker = self._tickers.get(
                grn=f['security_grn_code'] if 'security_grn_code' in f else None,
                name=f['security_name'],
            )
            if ticker.kind == TickerKind.Bond:
                price = Money(f['volume_currency'], Currency.parse(f['price_currency_code'])) / abs(int(qnty))
            else:
                price = Money(f['price'], Currency.parse(f['price_currency_code']))

            expected_volume = abs(int(qnty)) * price
            actual_volume = Money(f['volume_currency'], Currency.parse(f['price_currency_code']))
            assert expected_volume == actual_volume, f'expected_volume({expected_volume} = {qnty} * {price}) != ({actual_volume}) for {f}'

            self._trades.append(Trade(
                ticker=ticker,
                datetime=_parse_datetime(f['conclusion_time']),
                settle_date=_parse_datetime(f['execution_date']),
                quantity=int(qnty),
                price=price,
                fee=Money(f['broker_commission'], Currency.parse(f['broker_commission_currency_code'])),
            ))

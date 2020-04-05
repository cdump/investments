import csv
import datetime
from typing import Dict, Iterator, List

from investments.currency import Currency
from investments.dividend import Dividend
from investments.money import Money
from investments.ticker import Ticker, TickerKind
from investments.trade import Trade


def _parse_datetime(strval: str):
    return datetime.datetime.strptime(strval.replace(' ', ''), '%Y-%m-%d,%H:%M:%S')


def _parse_date(strval: str):
    return datetime.datetime.strptime(strval, '%Y-%m-%d').date()


def _parse_tickerkind(strval: str):
    if strval == 'Stocks':
        return TickerKind.Stock
    if strval == 'Equity and Index Options':
        return TickerKind.Option
    raise ValueError(strval)


class NamedRowsParser(object):
    def __init__(self):
        self._fields = []

    def parse_header(self, fields: List[str]):
        self._fields = fields

    def parse(self, row: List[str]) -> Dict[str, str]:
        assert len(row) == len(self._fields)
        return {k: v for k, v in zip(self._fields, row)}


class TickersStorage(object):
    def __init__(self):
        self._tickers = set()
        self._description_to_ticker = {}
        self._multipliers = {}

    def put(self, *, symbol: str, description: str, kind: TickerKind, multiplier: int):
        ticker = Ticker(symbol, kind)
        if ticker not in self._tickers:
            assert description not in self._description_to_ticker
            assert ticker not in self._multipliers
            self._tickers.add(ticker)
            self._multipliers[ticker] = multiplier
            self._description_to_ticker[description] = ticker
            return
        assert self._description_to_ticker[description] == ticker
        assert self._multipliers[ticker] == multiplier

    def get_ticker(self, name: str, kind: TickerKind):
        ticker = Ticker(name, kind)
        if ticker in self._tickers:
            return ticker

        dtt = self._description_to_ticker.get(name)
        if dtt is not None:
            assert dtt.kind == kind
            return dtt

        raise KeyError

    def get_multiplier(self, ticker: Ticker):
        return self._multipliers[ticker]


class InteractiveBrokersReportParser(object):
    def __init__(self):
        self._trades = []
        self._dividends = []
        self._deposits_and_withdrawals = []
        self._tickers = TickersStorage()
        self._settle_dates = {}

    def trades(self):
        return self._trades

    def dividends(self):
        return self._dividends

    def deposits_and_withdrawals(self):
        return self._deposits_and_withdrawals

    def parse_csv(self, *, activity_csvs: List[str], trade_confirmation_csvs: List[str]):
        # 1. parse tickers info
        for ac_fname in activity_csvs:
            with open(ac_fname, newline='') as ac_fh:
                self._real_parse_activity_csv(csv.reader(ac_fh, delimiter=','), {
                    'Financial Instrument Information': self._parse_instrument_information,
                })

        # 2. parse settle_date from trade confirmation
        for tc_fname in trade_confirmation_csvs:
            with open(tc_fname, newline='') as tc_fh:
                self._parse_trade_confirmation_csv(csv.reader(tc_fh, delimiter=','))

        # 3. parse everything else from activity (trades, dividends, ...)
        for activity_fname in activity_csvs:
            with open(activity_fname, newline='') as activity_fh:
                self._real_parse_activity_csv(csv.reader(activity_fh, delimiter=','), {
                    'Trades': self._parse_trades,
                    'Dividends': self._parse_dividends,
                    'Withholding Tax': self._parse_withholding_tax,
                    'Deposits & Withdrawals': self._parse_deposits,
                    # 'Account Information', 'Cash Report', 'Change in Dividend Accruals', 'Change in NAV',
                    # 'Codes', 'Fees', 'Interest Accruals', 'Interest', 'Mark-to-Market Performance Summary',
                    # 'Net Asset Value', 'Notes/Legal Notes', 'Open Positions', 'Realized & Unrealized Performance Summary',
                    # 'Statement', '\ufeffStatement', 'Total P/L for Statement Period', 'Transaction Fees',
                })

        # 4. sort
        self._trades.sort(key=lambda x: x.datetime)
        self._dividends.sort(key=lambda x: x.date)
        self._deposits_and_withdrawals.sort(key=lambda x: x[0])

    def _parse_trade_confirmation_csv(self, csv_reader: Iterator[List[str]]):
        parser = NamedRowsParser()
        parser.parse_header(next(csv_reader))
        for row in csv_reader:
            f = parser.parse(row)
            if f['LevelOfDetail'] != 'EXECUTION':
                continue
            settle_date = _parse_date(f['SettleDate'])

            key = (f['Symbol'], _parse_datetime(f['Date/Time']))
            existing_settle_date = self._settle_dates.get(key)
            if existing_settle_date is not None:
                assert existing_settle_date == settle_date
            else:
                self._settle_dates[key] = settle_date

    def _real_parse_activity_csv(self, csv_reader: Iterator[List[str]], parsers):
        nrparser = NamedRowsParser()
        for row in csv_reader:
            try:
                parser_fn = parsers[row[0]]
            except KeyError:
                # raise Exception(f'Unknown data {row}')
                continue

            if row[1] == 'Header':
                nrparser.parse_header(row[2:])
                continue

            if row[1] in {'Total', 'SubTotal'} or row[2] == 'Total':
                continue

            if row[1] == 'Data':
                fields = nrparser.parse(row[2:])
                parser_fn(fields)
            else:
                raise Exception(f'Unknown data {row}')

    def _parse_instrument_information(self, f: Dict[str, str]):
        self._tickers.put(
            symbol=f['Symbol'],
            description=f['Description'],
            kind=_parse_tickerkind(f['Asset Category']),
            multiplier=int(f['Multiplier']),
        )

    def _parse_trades(self, f: Dict[str, str]):
        ticker = self._tickers.get_ticker(f['Symbol'], _parse_tickerkind(f['Asset Category']))
        quantity_multiplier = self._tickers.get_multiplier(ticker)
        currency = Currency.parse(f['Currency'])

        dt = _parse_datetime(f['Date/Time'])

        settle_date = self._settle_dates.get((ticker.symbol, dt))
        assert settle_date is not None

        self._trades.append(Trade(
            ticker=ticker,
            datetime=dt,
            settle_date=settle_date,
            quantity=int(f['Quantity']) * quantity_multiplier,
            price=Money(f['T. Price'], currency),
            fee=Money(f['Comm/Fee'], currency),
        ))

    def _parse_withholding_tax(self, f: Dict[str, str]):
        name = f['Description'].split('(')[0].strip(' ')
        ticker = self._tickers.get_ticker(name, TickerKind.Stock)
        date = _parse_date(f['Date'])
        tax_amount = Money(f['Amount'], Currency.parse(f['Currency']))

        assert tax_amount.amount < 0
        tax_amount *= -1
        found = False
        for i, v in enumerate(self._dividends):
            if v.ticker == ticker and v.date == date:
                assert v.tax.amount == 0
                assert v.amount.currency == tax_amount.currency
                self._dividends[i] = Dividend(
                    ticker=v.ticker,
                    date=v.date,
                    amount=v.amount,
                    tax=tax_amount,
                )
                found = True
                break

        if not found:
            raise Exception(f'dividend not found for {ticker} on {date}')

    def _parse_dividends(self, f: Dict[str, str]):
        name = f['Description'].split('(')[0].strip(' ')
        ticker = self._tickers.get_ticker(name, TickerKind.Stock)
        date = _parse_date(f['Date'])
        amount = Money(f['Amount'], Currency.parse(f['Currency']))

        assert amount.amount > 0
        self._dividends.append(Dividend(
            ticker=ticker,
            date=date,
            amount=amount,
            tax=Money(0, amount.currency),
        ))

    def _parse_deposits(self, f: Dict[str, str]):
        currency = Currency.parse(f['Currency'])
        date = _parse_date(f['Settle Date'])
        amount = Money(f['Amount'], currency)
        self._deposits_and_withdrawals.append((date, amount))

import csv
import datetime
from decimal import Decimal

from investments.currency import Currency
from investments.fees import Fee
from investments.interests import Interest
from investments.money import Money
from investments.report_parsers.ib import InteractiveBrokersReportParser, _parse_date, _parse_datetime
from investments.ticker import TickerKind


def test_parse_dividends():
    p = InteractiveBrokersReportParser()

    lines = """Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Multiplier,Type,Code
Financial Instrument Information,Data,Stocks,JNJ,JOHNSON & JOHNSON,8719,,1,,
Financial Instrument Information,Data,Stocks,INTC,INTEL CORP,270639,,1,,
Financial Instrument Information,Data,Stocks,BND,BLABLABLA,270666,,1,,
Financial Instrument Information,Data,Stocks,GXC,SPDR S&P CHINA ETF,45540754,78463X400,1,ETF,
Dividends,Header,Currency,Date,Description,Amount
Dividends,Data,USD,2016-06-01,INTC (US4581401001) Cash Dividend USD 0.26000000 (Ordinary Dividend),6.5
Dividends,Data,USD,2016-06-07,JNJ(US4781601046) Cash Dividend 0.80000000 USD per Share (Ordinary Dividend),8
Dividends,Data,USD,2019-07-01,GXC(US78463X4007) Cash Dividend 0.80726400 USD per Share (Ordinary Dividend),1.61
Dividends,Data,USD,2019-07-01,GXC(US78463X4007) Payment in Lieu of Dividend (Ordinary Dividend),2.42
Dividends,Data,USD,2019-08-01,BND(US9219378356) Choice Dividend  0.17220900 USD Distribution Value - US Tax,1.66
Dividends,Data,USD,2019-08-02,BND(US9219378356) Cash Dividend USD 0.193413 per Share (Ordinary Dividend),3.87
Dividends,Data,USD,2019-08-02,BND(US9219378356) Cash Dividend USD 0.193413 per Share - Reversal (Ordinary Dividend),-3.87
Dividends,Data,Total,,,777.11"""

    lines = lines.split('\n')
    p._real_parse_activity_csv(csv.reader(lines, delimiter=','), {
        'Financial Instrument Information': p._parse_instrument_information,
        'Dividends': p._parse_dividends,
        'Withholding Tax': p._parse_withholding_tax,
    })

    d = p.dividends
    assert d[0].amount == Money(6.5, Currency.USD)
    assert d[1].amount == Money(8, Currency.USD)
    assert d[2].amount == Money(1.61, Currency.USD)
    assert d[3].amount == Money(2.42, Currency.USD)


def test_parse_dividends_with_tax():
    p = InteractiveBrokersReportParser()

    # both cases described in https://github.com/cdump/investments/issues/17

    lines = """Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Multiplier,Type,Code
Financial Instrument Information,Data,Stocks,INTC,INTEL CORP,270639,,1,,
Financial Instrument Information,Data,Stocks,JNJ,JOHNSON & JOHNSON,8719,,1,,
Dividends,Header,Currency,Date,Description,Amount
Dividends,Data,USD,2016-06-01,INTC (US4581401001) Cash Dividend USD 0.26000000 (Ordinary Dividend),6.5
Dividends,Data,USD,2016-06-07,JNJ(US4781601046) Cash Dividend 0.80000000 USD per Share (Ordinary Dividend),8
Withholding Tax,Header,Currency,Date,Description,Amount,Code
Withholding Tax,Data,USD,2016-06-01,INTC(US4581401001) Choice Dividend  0.26000000 USD Distribution Value - US Tax,-0.65,
Withholding Tax,Data,USD,2016-06-07,JNJ(US4781601046) Cash Dividend 0.80000000 USD per Share - US Tax,-0.8,"""

    lines = lines.split('\n')
    p._real_parse_activity_csv(csv.reader(lines, delimiter=','), {
        'Financial Instrument Information': p._parse_instrument_information,
        'Dividends': p._parse_dividends,
        'Withholding Tax': p._parse_withholding_tax,
    })

    d = p.dividends
    assert d[0].ticker.symbol == 'INTC'
    assert d[0].amount == Money(6.5, Currency.USD)
    assert d[0].tax == Money(0.65, Currency.USD)

    assert d[1].ticker.symbol == 'JNJ'
    assert d[1].amount == Money(8, Currency.USD)
    assert d[1].tax == Money(0.8, Currency.USD)


def test_parse_ticker_description_changed():
    p = InteractiveBrokersReportParser()

    lines = """Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Multiplier,Type,Code
Financial Instrument Information,Data,Stocks,VNQ,VANGUARD REIT ETF,31230302,922908553,1,ETF,
Financial Instrument Information,Data,Stocks,VNQ,VANGUARD REAL ESTATE ETF,31230302,US9229085538,1,ETF,"""

    lines = lines.split('\n')
    p._real_parse_activity_csv(csv.reader(lines, delimiter=','), {
        'Financial Instrument Information': p._parse_instrument_information,
    })

    a = p._tickers.get_ticker('VANGUARD REIT ETF', TickerKind.Stock)
    assert a.symbol == 'VNQ'

    b = p._tickers.get_ticker('VANGUARD REAL ESTATE ETF', TickerKind.Stock)
    assert b.symbol == 'VNQ'


def test_parse_fees():
    p = InteractiveBrokersReportParser()

    lines = """Fees,Header,Subtitle,Currency,Date,Description,Amount
Fees,Data,Other Fees,USD,2020-02-05,E*****42:GLOBAL SNAPSHOT FOR JAN 2020,-0.03
Fees,Data,Other Fees,USD,2020-02-05,E*****42:GLOBAL SNAPSHOT FOR JAN 2020,0.03
Fees,Data,Other Fees,USD,2020-06-03,E*****42:US CONSOLIDATED SNAPSHOT FOR MAY 2020,-0.01
Fees,Data,Other Fees,USD,2020-06-03,E*****42:US CONSOLIDATED SNAPSHOT FOR MAY 2020,0.01
Fees,Data,Other Fees,USD,2020-07-02,Balance of Monthly Minimum Fee for Jun 2020,-7.64
Fees,Data,Other Fees,USD,2020-09-03,Balance of Monthly Minimum Fee for Aug 2020,-10
Fees,Data,Total,,,,-17.64
Fees,Notes,"Market data is provided by Global Financial Information Services (GmbH)"""

    lines = lines.split('\n')
    p._real_parse_activity_csv(csv.reader(lines, delimiter=','), {
        'Fees': p._parse_fees,
    })

    assert len(p.fees) == 6
    assert p.fees[1] == Fee(date=datetime.date(2020, 2, 5), amount=Money(0.03, Currency.USD),
                            description='Other Fees - E*****42:GLOBAL SNAPSHOT FOR JAN 2020')
    assert p.fees[5] == Fee(date=datetime.date(2020, 9, 3), amount=Money(-10., Currency.USD),
                            description='Other Fees - Balance of Monthly Minimum Fee for Aug 2020')


def test_parse_interests():
    p = InteractiveBrokersReportParser()

    lines = """Interest,Header,Currency,Date,Description,Amount
Interest,Data,RUB,2020-03-04,RUB Credit Interest for Feb-2020,3.21
Interest,Data,Total,,,3.21
Interest,Data,Total in USD,,,0.04844211
Interest,Data,USD,2020-03-04,USD Credit Interest for Feb-2020,0.09
Interest,Data,Total,,,0.09
Interest,Data,Total Interest in USD,,,0.13844211"""

    lines = lines.split('\n')
    p._real_parse_activity_csv(csv.reader(lines, delimiter=','), {
        'Interest': p._parse_interests,
    })

    assert len(p.interests) == 2
    assert p.interests[0] == Interest(date=datetime.date(2020, 3, 4), amount=Money(3.21, Currency.RUB),
                                      description='RUB Credit Interest for Feb-2020')
    assert p.interests[1] == Interest(date=datetime.date(2020, 3, 4), amount=Money(0.09, Currency.USD),
                                      description='USD Credit Interest for Feb-2020')


def test_parse_trades_with_fees():
    p = InteractiveBrokersReportParser()

    lines = """Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Listing Exch,Multiplier,Type,Code
Financial Instrument Information,Data,Stocks,VT,VANGUARD TOT WORLD STK ETF,52197301,US9220427424,ARCA,1,ETF,
Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,C. Price,Proceeds,Comm/Fee,Basis,Realized P/L,MTM P/L,Code
Trades,Data,Order,Stocks,USD,VT,"2020-01-31, 09:30:00",10,80.62,79.73,-806.2,-1,807.2,0,-8.9,O
Trades,Data,Order,Stocks,USD,VT,"2020-02-10, 09:38:00",-10,81.82,82.25,818.2,-1.01812674,-807.2,9.981873,-4.3,C
Trades,SubTotal,,Stocks,USD,VT,,0,,,12,-2.01812674,0,9.981873,-13.2,
Trades,Total,,Stocks,USD,,,,,,-57144.745,-25.563491343,57180.290364603,9.981873,-16.654,"""

    lines = lines.split('\n')
    p._settle_dates = {
        ('VT', _parse_datetime('2020-01-31, 09:30:00')): _parse_date('2020-02-04'),
        ('VT', _parse_datetime('2020-02-10, 09:38:00')): _parse_date('2020-02-12'),
    }

    p._real_parse_activity_csv(csv.reader(lines, delimiter=','), {
        'Financial Instrument Information': p._parse_instrument_information,
        'Trades': p._parse_trades,
    })

    assert len(p.trades) == 2

    # buy trade
    assert p.trades[0].ticker.symbol == 'VT'
    assert p.trades[0].datetime == _parse_datetime('2020-01-31, 09:30:00')
    assert p.trades[0].settle_date == _parse_date('2020-02-04')
    assert p.trades[0].quantity == 10
    assert p.trades[0].price.amount == Decimal('80.62')
    assert p.trades[0].price.currency == Currency.USD
    assert p.trades[0].fee.amount == Decimal('-1')
    assert p.trades[0].fee.currency == Currency.USD

    # sell trade
    assert p.trades[1].ticker.symbol == 'VT'
    assert p.trades[1].datetime == _parse_datetime('2020-02-10, 09:38:00')
    assert p.trades[1].settle_date == _parse_date('2020-02-12')
    assert p.trades[1].quantity == -10
    assert p.trades[1].price.amount == Decimal('81.82')
    assert p.trades[1].price.currency == Currency.USD
    assert p.trades[1].fee.amount == Decimal('-1.01812674')
    assert p.trades[1].fee.currency == Currency.USD

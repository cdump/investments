import csv

from investments.currency import Currency
from investments.money import Money
from investments.report_parsers.ib import InteractiveBrokersReportParser
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

    d = p.dividends()
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

    d = p.dividends()
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

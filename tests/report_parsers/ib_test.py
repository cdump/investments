import csv

from investments.currency import Currency
from investments.money import Money
from investments.report_parsers.ib import InteractiveBrokersReportParser


def test_parse_dividends():
    p = InteractiveBrokersReportParser()

    lines = """Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Multiplier,Type,Code
Financial Instrument Information,Data,Stocks,JNJ,JOHNSON & JOHNSON,8719,,1,,
Financial Instrument Information,Data,Stocks,INTC,INTEL CORP,270639,,1,,
Financial Instrument Information,Data,Stocks,GXC,SPDR S&P CHINA ETF,45540754,78463X400,1,ETF,
Dividends,Header,Currency,Date,Description,Amount
Dividends,Data,USD,2016-06-01,INTC (US4581401001) Cash Dividend USD 0.26000000 (Ordinary Dividend),6.5
Dividends,Data,USD,2016-06-07,JNJ(US4781601046) Cash Dividend 0.80000000 USD per Share (Ordinary Dividend),8
Dividends,Data,USD,2019-07-01,GXC(US78463X4007) Cash Dividend 0.80726400 USD per Share (Ordinary Dividend),1.61
Dividends,Data,USD,2019-07-01,GXC(US78463X4007) Payment in Lieu of Dividend (Ordinary Dividend),2.42
Dividends,Data,Total,,,777.11"""

    lines = lines.split('\n')
    p._real_parse_activity_csv(csv.reader(lines, delimiter=','), {
        'Financial Instrument Information': p._parse_instrument_information,
        'Dividends': p._parse_dividends,
    })

    d = p.dividends()
    assert len(d) == 4
    assert d[0].amount == Money(6.5, Currency.USD)
    assert d[1].amount == Money(8, Currency.USD)
    assert d[2].amount == Money(1.61, Currency.USD)
    assert d[3].amount == Money(2.42, Currency.USD)

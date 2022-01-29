import csv
import datetime
from decimal import Decimal
from typing import Any

import pytest

from investments.cash import Cash
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


def test_parse_dividends_with_changed_tax():
    """Обработка возврата WHT по дивидендам в начале следующего года."""

    p = InteractiveBrokersReportParser()

    lines = """Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Multiplier,Type,Code
Financial Instrument Information,Data,Stocks,FREL,FIDELITY REAL ESTATE ETF,183005003,US3160928574,1,ETF,
Dividends,Header,Currency,Date,Description,Amount
Dividends,Data,USD,2020-03-25,FREL(US3160928574) Cash Dividend USD 0.282 per Share (Ordinary Dividend),54.14
Withholding Tax,Header,Currency,Date,Description,Amount,Code
Withholding Tax,Data,USD,2020-03-25,FREL(US3160928574) Cash Dividend USD 0.282 per Share - US Tax,-5.41,
Withholding Tax,Data,USD,2020-03-25,FREL(US3160928574) Cash Dividend USD 0.282 per Share - US Tax,5.41,
Withholding Tax,Data,USD,2020-03-25,FREL(US3160928574) Cash Dividend USD 0.282 per Share - US Tax,-3.07,"""

    lines = lines.split('\n')
    p._real_parse_activity_csv(csv.reader(lines, delimiter=','), {
        'Financial Instrument Information': p._parse_instrument_information,
        'Dividends': p._parse_dividends,
        'Withholding Tax': p._parse_withholding_tax,
    })

    d = p.dividends
    assert d[0].ticker.symbol == 'FREL'
    assert d[0].amount == Money(54.14, Currency.USD)
    assert d[0].tax == Money(3.07, Currency.USD)


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
Interest,Data,CAD,2020-03-04,CAD Credit Interest for Feb-2020,7.45
Interest,Data,Total,,,7.45
Interest,Data,Total in USD,,,6.69
Interest,Data,USD,2020-03-04,USD Credit Interest for Feb-2020,0.09
Interest,Data,Total,,,0.09
Interest,Data,Total Interest in USD,,,0.13844211"""

    lines = lines.split('\n')
    p._real_parse_activity_csv(csv.reader(lines, delimiter=','), {
        'Interest': p._parse_interests,
    })

    assert len(p.interests) == 3
    assert p.interests[0] == Interest(date=datetime.date(2020, 3, 4), amount=Money(3.21, Currency.RUB),
                                      description='RUB Credit Interest for Feb-2020')
    assert p.interests[2] == Interest(date=datetime.date(2020, 3, 4), amount=Money(0.09, Currency.USD),
                                      description='USD Credit Interest for Feb-2020')
    assert p.interests[1] == Interest(date=datetime.date(2020, 3, 4), amount=Money(7.45, Currency.CAD),
                                      description='CAD Credit Interest for Feb-2020')


def test_parse_cash():
    p = InteractiveBrokersReportParser()

    lines = """Cash Report,Header,Currency Summary,Currency,Total,Securities,Futures,Month to Date,Year to Date,
Cash Report,Data,Starting Cash,Base Currency Summary,0,0,0,,,
Cash Report,Data,Commissions,Base Currency Summary,-82.64370531,-82.64370531,0,-8.62621762,-82.64370531,
Cash Report,Data,Deposits,Base Currency Summary,65663.765,65663.765,0,1625.96,65663.765,
Cash Report,Data,Dividends,Base Currency Summary,1045.45,1045.45,0,523.67,1045.45,
Cash Report,Data,Broker Interest Paid and Received,Base Currency Summary,0.13844211,0.13844211,0,0,0.13844211,
Cash Report,Data,Net Trades (Sales),Base Currency Summary,74217.07255104,74217.07255104,0,3923.70991107,74217.07255106,
Cash Report,Data,Net Trades (Purchase),Base Currency Summary,-140090.704656633,-140090.704656633,0,-7874.79454332,-140090.70465664,
Cash Report,Data,Other Fees,Base Currency Summary,-23.2,-23.2,0,-0.6,-23.2,
Cash Report,Data,Withholding Tax,Base Currency Summary,-103.55,-103.55,0,-51.39,-103.55,
Cash Report,Data,Cash FX Translation Gain/Loss,Base Currency Summary,-156.23378547,-156.23378547,0,,,
Cash Report,Data,Ending Cash,Base Currency Summary,470.093845757,470.093845757,0,,,
Cash Report,Data,Ending Settled Cash,Base Currency Summary,470.093845757,470.093845757,0,,,
Cash Report,Data,Starting Cash,RUB,0,0,0,,,
Cash Report,Data,Deposits,RUB,4495000,4495000,0,120000,4495000,
Cash Report,Data,Broker Interest Paid and Received,RUB,3.21,3.21,0,0,3.21,
Cash Report,Data,Net Trades (Purchase),RUB,-4495003.210000001,-4495003.210000001,0,-295619.97975,-4495003.21,
Cash Report,Data,Ending Cash,RUB,0,0,0,,,
Cash Report,Data,Ending Settled Cash,RUB,0,0,0,,,
Cash Report,Data,Starting Cash,USD,0,0,0,,,
Cash Report,Data,Commissions,USD,-82.64370531,-82.64370531,0,-8.62621762,-82.64370531,
Cash Report,Data,Dividends,USD,1045.45,1045.45,0,523.67,1045.45,
Cash Report,Data,Broker Interest Paid and Received,USD,0.09,0.09,0,0,0.09,
Cash Report,Data,Net Trades (Sales),USD,74217.07255104,74217.07255104,0,3923.70991107,74217.07255106,
Cash Report,Data,Net Trades (Purchase),USD,-74583.125,-74583.125,0,-3932.96,-74583.125,
Cash Report,Data,Other Fees,USD,-23.2,-23.2,0,-0.6,-23.2,
Cash Report,Data,Withholding Tax,USD,-103.55,-103.55,0,-51.39,-103.55,
Cash Report,Data,Ending Cash,USD,470.093845757,470.093845757,0,,,
Cash Report,Data,Ending Settled Cash,USD,470.093845757,470.093845757,0,,,"""

    lines = lines.split('\n')
    p._real_parse_activity_csv(csv.reader(lines, delimiter=','), {
        'Cash Report': p._parse_cash_report,
    })

    assert len(p.cash) == 16
    assert p.cash[1] == Cash(amount=Money(4495000, Currency.RUB), description='Deposits')
    assert p.cash[15] == Cash(amount=Money(470.093845757, Currency.USD), description='Ending Settled Cash')


def test_parse_trades_with_thousands_separator():
    """Сделки с более чем 1000 бумаг в отчёте форматируются с запятой как разделителем тысяч."""
    p = InteractiveBrokersReportParser()

    lines = """Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Listing Exch,Multiplier,Type,Code
Financial Instrument Information,Data,Stocks,NOK,NOKIA CORP-SPON ADR,661513,US6549022043,NYSE,1,ADR,
Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,C. Price,Proceeds,Comm/Fee,Basis,Realized P/L,MTM P/L,Code
Trades,Data,Order,Stocks,USD,NOK,"2020-04-03, 09:48:58","-3200",2.995,2.97,-958.4,-1.6,960,0,-8,O
Trades,Data,Order,Stocks,USD,NOK,"2020-04-06, 11:43:36",500,3.125,3.16,-1562.5,-2.5,1565,0,17.5,O
Trades,Data,Order,Stocks,USD,NOK,"2020-04-06, 11:44:50","5,000",3.125,3.16,-6250,-10,6260,0,70,O;P
Trades,SubTotal,,Stocks,USD,NOK,,"2,299.81",,,-8770.9,-14.1,8785,0,79.5,"""

    lines = lines.split('\n')

    p._settle_dates.put('NOK', _parse_datetime('2020-04-03, 09:48:58'), _parse_date('2020-02-04'), 'a')
    p._settle_dates.put('NOK', _parse_datetime('2020-04-06, 11:43:36'), _parse_date('2020-02-12'), 'b')
    p._settle_dates.put('NOK', _parse_datetime('2020-04-06, 11:44:50'), _parse_date('2020-02-12'), 'c')

    p._real_parse_activity_csv(csv.reader(lines, delimiter=','), {
        'Financial Instrument Information': p._parse_instrument_information,
        'Trades': p._parse_trades,
    })

    assert len(p.trades) == 3
    assert {-3200, 500, 5000} == {trade.quantity for trade in p.trades}


def test_parse_trades_with_fees():
    p = InteractiveBrokersReportParser()

    lines = """Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Listing Exch,Multiplier,Type,Code
Financial Instrument Information,Data,Stocks,VT,VANGUARD TOT WORLD STK ETF,52197301,US9220427424,ARCA,1,ETF,
Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,C. Price,Proceeds,Comm/Fee,Basis,Realized P/L,MTM P/L,Code
Trades,Data,Order,Stocks,USD,VT,"2020-01-31, 09:30:00",10,80.62,79.73,-806.2,-1,807.2,0,-8.9,O
Trades,Data,Order,Stocks,USD,VT,"2020-02-10, 09:38:00",-10,81.82,82.25,818.2,-1.01812674,-807.2,9.981873,-4.3,C
Trades,SubTotal,,Stocks,USD,VT,,0,,,12,-2.01812674,0,9.981873,-13.2,"""

    lines = lines.split('\n')
    p._settle_dates.put('VT', _parse_datetime('2020-01-31, 09:30:00'), _parse_date('2020-02-04'), '')
    p._settle_dates.put('VT', _parse_datetime('2020-02-10, 09:38:00'), _parse_date('2020-02-12'), '')

    p._real_parse_activity_csv(csv.reader(lines, delimiter=','), {
        'Financial Instrument Information': p._parse_instrument_information,
        'Trades': p._parse_trades,
    })

    assert len(p.trades) == 2

    # buy trade
    assert p.trades[0].ticker.symbol == 'VT'
    assert p.trades[0].trade_date == _parse_datetime('2020-01-31, 09:30:00')
    assert p.trades[0].settle_date == _parse_date('2020-02-04')
    assert p.trades[0].quantity == 10
    assert p.trades[0].price.amount == Decimal('80.62')
    assert p.trades[0].price.currency == Currency.USD
    assert p.trades[0].fee.amount == Decimal('-1')
    assert p.trades[0].fee.currency == Currency.USD
    assert p.trades[0].fee_per_piece.currency == Currency.USD
    assert p.trades[0].fee_per_piece.amount == Decimal('-0.1')

    # sell trade
    assert p.trades[1].ticker.symbol == 'VT'
    assert p.trades[1].trade_date == _parse_datetime('2020-02-10, 09:38:00')
    assert p.trades[1].settle_date == _parse_date('2020-02-12')
    assert p.trades[1].quantity == -10
    assert p.trades[1].price.amount == Decimal('81.82')
    assert p.trades[1].price.currency == Currency.USD
    assert p.trades[1].fee.amount == Decimal('-1.01812674')
    assert p.trades[1].fee.currency == Currency.USD
    assert p.trades[1].fee_per_piece.amount == Decimal('-0.101812674')
    assert p.trades[1].fee_per_piece.currency == Currency.USD


@pytest.mark.parametrize("case,expected", [
    ('2020-06-02', datetime.date(2020, 6, 2)),
    ('', None),
])
def test_parse_date(case: str, expected: Any):
    if expected is None:
        with pytest.raises(ValueError):
            _parse_date(case)

    else:
        res = _parse_date(case)
        assert res == expected


def test_group_confirmation_reports_by_order_id():
    """
    Иногда в отчётах о подтверждении сделок появляется операция отмены исполнения и следом правильная строка
    с данными об исполнении.
    Выглядит как
    - строка с датой исполнения A
    - строка с типом TradeCancel
    - строка с датой исполнения Б
    и всё это по одной сделке.

    Чтобы решить эту проблему автоматически, мы группируем строки в отчёте о подтверждении по параметру OrderId
    и далее работаем только с последней строкой по каждому ордеру.
    """
    p = InteractiveBrokersReportParser()
    lines = """"ClientAccountID","AccountAlias","Model","CurrencyPrimary","AssetClass","Symbol","Description","Conid","SecurityID","SecurityIDType","CUSIP","ISIN","ListingExchange","UnderlyingConid","UnderlyingSymbol","UnderlyingSecurityID","UnderlyingListingExchange","Issuer","Multiplier","Strike","Expiry","Put/Call","PrincipalAdjustFactor","TransactionType","TradeID","OrderID","ExecID","BrokerageOrderID","OrderReference","VolatilityOrderLink","ClearingFirmID","OrigTradePrice","OrigTradeDate","OrigTradeID","OrderTime","Date/Time","ReportDate","SettleDate","TradeDate","Exchange","Buy/Sell","Quantity","Price","Amount","Proceeds","Commission","BrokerExecutionCommission","BrokerClearingCommission","ThirdPartyExecutionCommission","ThirdPartyClearingCommission","ThirdPartyRegulatoryCommission","OtherCommission","CommissionCurrency","Tax","Code","OrderType","LevelOfDetail","TraderID","IsAPIOrder","AllocatedTo","AccruedInterest","RFQID","SerialNumber","DeliveryType","CommodityType","Fineness","Weight"
"U3473202","","","EUR","STK","DXETd","X EURO STOXX 50 1C","59141442","LU0380865021","ISIN","","LU0380865021","IBIS","","","","","","1","","","","","ExchTrade","3567512579","1784592333","0000d349.603f512e.01.01","004ef3dd.000128a9.603f2319.0001","","","","0","","","2021-03-03,10:32:45","2021-03-03,10:32:45","2021-03-03","2021-03-05","2021-03-03","GETTEX","BUY","70","56.04","3922.8","-3922.8","-1.9614","-1.9614","0","0","0","0","0","EUR","0","O","LMT","EXECUTION","","N","","0","","","","","0.0","0.0 ()"
"U3473202","","","EUR","STK","DXETd","X EURO STOXX 50 1C","59141442","LU0380865021","ISIN","","LU0380865021","IBIS","","","","","","1","","","","","ExchTrade","3571384109","1786706570","0000d349.60409e83.01.01","004ef3dd.000128a9.6040747b.0001","","","","0","","","2021-03-04,07:15:50","2021-03-04,07:15:50","2021-03-04","2021-03-08","2021-03-04","GETTEX","BUY","100","56.11","5611","-5611","-2.8055","-2.8055","0","0","0","0","0","EUR","0","O","LMT","EXECUTION","","N","","0","","","","","0.0","0.0 ()"
"U3473202","","","EUR","STK","DXETd","X EURO STOXX 50 1C","59141442","LU0380865021","ISIN","","LU0380865021","IBIS","","","","","","1","","","","","TradeCancel","","1786706570","","","","","","56.11","2021-03-04","3571384109","","2021-03-04,07:15:50","2021-03-05","","2021-03-04","--","BUY (Ca.)","-100","56.11","-5611","5611","0","","","","","","","EUR","0","Ca","LMT","EXECUTION","","N","","0","","","","","0.0","0.0 ()"
"U3473202","","","EUR","STK","DXETd","X EURO STOXX 50 1C","59141442","LU0380865021","ISIN","","LU0380865021","IBIS","","","","","","1","","","","","ExchTrade","3571384109","1786706570","0000d349.60409e83.01.01","004ef3dd.000128a9.6040747b.0001","","","","0","","","2021-03-04,07:15:50","2021-03-04,07:15:50","2021-03-05","2021-03-09","2021-03-04","GETTEX","BUY","100","56.11","5611","-5611","0","","","","","","","EUR","0","O","LMT","EXECUTION","","N","","0","","","","","0.0","0.0 ()"
"U3473202","","","EUR","STK","DXETd","X EURO STOXX 50 1C","59141442","LU0380865021","ISIN","","LU0380865021","IBIS","","","","","","1","","","","","ExchTrade","3650141124","1831441961","0000d349.605d9a95.01.01","004ef3dd.000128a9.605d74ba.0001","","","","0","","","2021-03-26,06:37:20","2021-03-26,06:37:20","2021-03-26","2021-03-30","2021-03-26","GETTEX","BUY","15","58.38","875.7","-875.7","-1.25","-1.25","0","0","0","0","0","EUR","0","O","LMT","EXECUTION","","N","","0","","","","","0.0","0.0 ()\""""
    lines = lines.split('\n')

    p._parse_trade_confirmation_csv(csv.reader(lines, delimiter=','))

    assert len(p._settle_dates) == 3
    assert {'1784592333', '1786706570', '1831441961'} == {
        i.order_id
        for i in p._settle_dates._settle_data.values()
    }
    assert p._settle_dates.get_date('DXETd', _parse_datetime('2021-03-04,07:15:50')) == _parse_date('2021-03-09')
    assert p._settle_dates.get_date('DXETd', _parse_datetime('2021-03-03,10:32:45')) == _parse_date('2021-03-05')

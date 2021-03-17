import argparse
import logging
import os
from typing import Iterable, List, Optional

import pandas  # type: ignore
from tabulate import tabulate

from investments.calculators import compute_total_cost
from investments.currency import Currency
from investments.data_providers import cbr
from investments.dividend import Dividend
from investments.fees import Fee
from investments.interests import Interest
from investments.money import Money
from investments.report_parsers.ib import InteractiveBrokersReportParser
from investments.trades_fifo import TradesAnalyzer, FinishedTrade, PortfolioElement  # noqa: I001


def apply_round_for_dataframe(source: pandas.DataFrame, columns: Iterable, digits: int = 2) -> pandas.DataFrame:
    source[list(columns)] = source[list(columns)].applymap(
        lambda x: x.round(digits=digits) if isinstance(x, Money) else round(x, digits),
    )
    return source


def prepare_trades_report(finished_trades: List[FinishedTrade], cbr_client_usd: cbr.ExchangeRatesRUB) -> pandas.DataFrame:
    """
    Расчёт расхода/дохода и финансового результата по закрытым сделкам.

    Общая методика расчёта расхода/дохода по сделке:
    [сумма сделки] * [курс валюты на дату поставки] +/- [сумма комиссии] * [курс валюты на дату сделки]

    """
    trade_date_column = 'trade_date'
    tax_date_column = 'settle_date'

    df = pandas.DataFrame(finished_trades, columns=finished_trades[0].fields)

    df[trade_date_column] = df[trade_date_column].dt.normalize()
    df[tax_date_column] = pandas.to_datetime(df[tax_date_column])

    tax_years = df.groupby('N')[tax_date_column].max().map(lambda x: x.year).rename('tax_year')
    df = df.join(tax_years, how='left', on='N')

    df['price_rub'] = df.apply(lambda x: cbr_client_usd.convert_to_rub(x['price'], x[tax_date_column]), axis=1)
    df['fee_per_piece_rub'] = df.apply(lambda x: cbr_client_usd.convert_to_rub(x['fee_per_piece'], x[trade_date_column]), axis=1)
    df['fee'] = df.apply(lambda x: (x['fee_per_piece'] * abs(x['quantity'])), axis=1)

    df['total'] = df.apply(
        lambda x: compute_total_cost(x['quantity'], x['price'], x['fee_per_piece']),
        axis=1,
    )
    df['total_rub'] = df.apply(
        lambda x: compute_total_cost(x['quantity'], x['price_rub'], x['fee_per_piece_rub']),
        axis=1,
    )

    df = df.join(cbr_client_usd.dataframe['rate'].rename('settle_rate'), how='left', on=tax_date_column)
    df = df.join(cbr_client_usd.dataframe['rate'].rename('fee_rate'), how='left', on=trade_date_column)
    df['profit_rub'] = df['total_rub']

    profit = df.groupby('N')['profit_rub'].sum().reset_index().set_index('N')
    df = df.join(profit, how='left', on='N', lsuffix='_delete')
    df.drop(columns=['profit_rub_delete'], axis=0, inplace=True)
    df.loc[~df.index.isin(df.groupby('N')[trade_date_column].idxmax()), 'profit_rub'] = Money(0, Currency.RUB)

    return df


def prepare_dividends_report(dividends: List[Dividend], cbr_client_usd: cbr.ExchangeRatesRUB, verbose: bool) -> pandas.DataFrame:
    operation_date_column = 'date'
    if not verbose:
        dividends = [x for x in dividends if x.amount.amount != 0 or x.tax.amount != 0]  # remove reversed dividends

    df_data = [(i + 1, x.ticker, pandas.to_datetime(x.date), x.amount, x.tax) for i, x in enumerate(dividends)]
    df = pandas.DataFrame(df_data, columns=['N', 'ticker', 'date', 'amount', 'tax_paid'])

    df['tax_year'] = df[operation_date_column].map(lambda x: x.year)

    df = df.join(cbr_client_usd.dataframe, how='left', on=operation_date_column)

    df['amount_rub'] = df.apply(lambda x: cbr_client_usd.convert_to_rub(x['amount'], x[operation_date_column]), axis=1)
    df['tax_paid_rub'] = df.apply(lambda x: cbr_client_usd.convert_to_rub(x['tax_paid'], x[operation_date_column]), axis=1)
    df['tax_rate'] = df.apply(lambda x: round(x['tax_paid'].amount * 100 / x['amount'].amount, 2), axis=1)

    return df


def prepare_fees_report(fees: List[Fee], cbr_client_usd: cbr.ExchangeRatesRUB) -> pandas.DataFrame:
    operation_date_column = 'date'
    df_data = [
        (i + 1, pandas.to_datetime(x.date), x.amount, x.description, x.date.year)
        for i, x in enumerate(fees)
    ]
    df = pandas.DataFrame(df_data, columns=['N', operation_date_column, 'amount', 'description', 'tax_year'])
    df = df.join(cbr_client_usd.dataframe, how='left', on=operation_date_column)

    df['amount_rub'] = df.apply(lambda x: cbr_client_usd.convert_to_rub(x['amount'], x[operation_date_column]), axis=1)
    return df


def prepare_interests_report(interests: List[Interest], cbr_client_usd: cbr.ExchangeRatesRUB) -> pandas.DataFrame:
    operation_date_column = 'date'
    df_data = [
        (i + 1, pandas.to_datetime(x.date), x.amount, x.description, x.date.year)
        for i, x in enumerate(interests)
    ]
    df = pandas.DataFrame(df_data, columns=['N', operation_date_column, 'amount', 'description', 'tax_year'])
    df = df.join(cbr_client_usd.dataframe, how='left', on=operation_date_column)
    df['amount_rub'] = df.apply(lambda x: cbr_client_usd.convert_to_rub(x['amount'], x[operation_date_column]), axis=1)
    return df


def _show_header(msg: str):
    print(f'>>> {msg} <<<')


def _show_year_header(year: str):
    print('\n', '______' * 8, year, '______' * 8, '\n\n')


def _show_fees_report(fees: pandas.DataFrame, year: int, verbose: bool):
    fees_by_year = fees[fees['tax_year'] == year].drop(columns=['tax_year'])
    if fees_by_year.empty:
        return

    feed_presenter = fees_by_year.copy(deep=True).set_index(['N', 'date'])
    if not verbose:
        apply_round_for_dataframe(feed_presenter, {'rate'}, 4)
        apply_round_for_dataframe(feed_presenter, {'amount', 'amount_rub'}, 2)

    _show_header('OTHER FEES')
    print(feed_presenter.to_string())
    print('\nTOTAL:\t', feed_presenter['amount_rub'].sum())
    print('\n\n')


def _show_interests_report(interests: pandas.DataFrame, year: int, verbose: bool):
    interests_by_year = interests[interests['tax_year'] == year].drop(columns=['tax_year'])
    if interests_by_year.empty:
        return

    interests_presenter = interests_by_year.copy(deep=True).set_index(['N', 'date'])
    if not verbose:
        apply_round_for_dataframe(interests_presenter, {'rate'}, 4)
        apply_round_for_dataframe(interests_presenter, {'amount', 'amount_rub'}, 2)

    _show_header('INTERESTS')
    print(interests_presenter.to_string())
    print('\n\n')


def _show_dividends_report(dividends: pandas.DataFrame, year: int, verbose: bool):
    dividends_by_year = dividends[dividends['tax_year'] == year].drop(columns=['tax_year'])
    if dividends_by_year.empty:
        return

    dividends_by_year['N'] -= dividends_by_year['N'].iloc[0] - 1

    dividends_presenter = dividends_by_year.copy(deep=True).set_index(['N', 'ticker', 'date'])
    if not verbose:
        apply_round_for_dataframe(dividends_presenter, {'rate'}, 4)
        apply_round_for_dataframe(dividends_presenter, {'amount', 'amount_rub', 'tax_paid', 'tax_paid_rub'}, 2)
        dividends_presenter = dividends_presenter.drop(columns=['tax_rate'])

    _show_header('DIVIDENDS')
    print(dividends_presenter.to_string())
    print('\n\n')


def _show_trades_report(trades: pandas.DataFrame, year: int, verbose: bool):
    trades_by_year = trades[trades['tax_year'] == year].drop(columns=['tax_year'])
    if trades_by_year.empty:
        return

    trades_by_year['N'] -= trades_by_year['N'].iloc[0] - 1

    _show_header('TRADES')
    trades_presenter = trades_by_year.copy(deep=True).set_index(['N', 'ticker', 'trade_date'])
    if not verbose:
        apply_round_for_dataframe(trades_presenter, {'price', 'total', 'total_rub', 'profit_rub'}, 2)
        apply_round_for_dataframe(trades_presenter, {'fee', 'settle_rate', 'fee_rate'}, 4)
        trades_presenter = trades_presenter.drop(columns=['fee_per_piece', 'fee_per_piece_rub', 'price_rub'])

    print(trades_presenter.to_string())
    print('\n\n')

    _show_header('TRADES RESULTS BEFORE TAXES')
    trades_summary_presenter = _prepare_trades_summary_report(trades_by_year)
    if not verbose:
        apply_round_for_dataframe(trades_summary_presenter, {'expenses', 'income', 'profit'}, 2)
    print(trades_summary_presenter.reset_index().to_string())
    print('\n\n')


def _prepare_trades_summary_report(trades_by_year: pandas.DataFrame) -> pandas.DataFrame:
    trades_summary_presenter = trades_by_year.copy(deep=True).groupby(lambda idx: (
        trades_by_year.loc[idx, 'ticker'].kind,
        'expenses' if trades_by_year.loc[idx, 'quantity'] > 0 else 'income',
    ))['total_rub'].sum().reset_index()
    trades_summary_presenter = trades_summary_presenter['index'].apply(pandas.Series).join(trades_summary_presenter).pivot(index=0, columns=1, values='total_rub')
    trades_summary_presenter.index.name = ''
    trades_summary_presenter.columns.name = ''
    trades_summary_presenter['profit'] = trades_summary_presenter['income'] + trades_summary_presenter['expenses']
    return trades_summary_presenter


def show_portfolio_report(portfolio: List[PortfolioElement]):
    _show_header('PORTFOLIO')
    for elem in portfolio:
        print(f'{elem.ticker}\tx\t{elem.quantity}')
    print('\n\n')


def show_ndfl_report(trades: Optional[pandas.DataFrame], dividends: Optional[pandas.DataFrame],
                     fees: Optional[pandas.DataFrame], interests: Optional[pandas.DataFrame],
                     filter_years: List[int], show_humanize_numbers: bool):  # noqa: WPS318,WPS319

    years = set()
    for report in (trades, dividends, fees, interests):
        if report is not None:
            years |= set(report['tax_year'].unique())

    for year in years:  # noqa: WPS426
        if filter_years and (year not in filter_years):
            continue
        _show_year_header(f'   {year}   ')

        ndfl_report = [
            ['Код дохода', 'Код расхода', 'Доход руб.', 'Расход руб.', 'Уплаченный налог руб.', 'Источник выплаты'],
        ]

        if dividends is not None:
            # income code 1010
            dividends_by_year = dividends[dividends['tax_year'] == year]
            dividends_presenter = dividends_by_year.copy(deep=True)
            income_dividends = dividends_presenter['amount_rub'].sum()
            tax_dividends = dividends_presenter['tax_paid_rub'].sum()
            if show_humanize_numbers:
                income_dividends = income_dividends.round(2)
                tax_dividends = tax_dividends.round(2)
            ndfl_report.append(
                [1010, None, income_dividends, 0, tax_dividends, 'Interactive Brokers dividends'],
            )

        if trades is not None:
            # income code 1530, expenses code 201 [@see НК РФ 214.1.3]
            trades_by_year = trades[trades['tax_year'] == year]
            trades_summary_presenter = _prepare_trades_summary_report(trades_by_year)
            expenses_trades = abs(trades_summary_presenter['expenses'].sum())
            income_trades = trades_summary_presenter['income'].sum()

            if fees is not None:
                fees_by_year = fees[fees['tax_year'] == year]
                feed_presenter = fees_by_year.copy(deep=True)
                expenses_trades += abs(feed_presenter['amount_rub'].sum())

            if show_humanize_numbers:
                income_trades = income_trades.round(2)
                expenses_trades = expenses_trades.round(2)

            ndfl_report.append(
                [1530, 201, income_trades, expenses_trades, 0, 'Interactive Brokers trades'],
            )

        if interests is not None:
            # income code 4800
            interests_by_year = interests[interests['tax_year'] == year]
            income_interests: Money = interests_by_year['amount_rub'].sum()
            if show_humanize_numbers:
                income_interests = income_interests.round(2)

            ndfl_report.append(
                [4800, None, income_interests, 0, 0, 'Interactive Brokers interests'],
            )

        print(tabulate(ndfl_report, headers='firstrow', tablefmt='presto', colalign=('right', 'decimal')))

        _show_year_header(f'EOF {year}  ')


def show_report(trades: Optional[pandas.DataFrame], dividends: Optional[pandas.DataFrame],
                fees: Optional[pandas.DataFrame], interests: Optional[pandas.DataFrame],
                filter_years: List[int], verbose: bool):  # noqa: WPS318,WPS319
    years = set()
    for report in (trades, dividends, fees, interests):
        if report is not None:
            years |= set(report['tax_year'].unique())

    for year in years:  # noqa: WPS426
        if filter_years and (year not in filter_years):
            continue
        _show_year_header(f'   {year}   ')

        if dividends is not None:
            _show_dividends_report(dividends, year, verbose)

        if trades is not None:
            _show_trades_report(trades, year, verbose)

        if fees is not None:
            _show_fees_report(fees, year, verbose)

        if interests is not None:
            _show_interests_report(interests, year, verbose)

        _show_year_header(f'EOF {year}  ')


def csvs_in_dir(directory: str):
    ret = []
    for filename in os.scandir(directory):
        if not filename.is_file():
            continue
        if not filename.name.lower().endswith('.csv'):
            continue
        ret.append(filename.path)
    return ret


def parse_reports(activity_reports_dir: str, confirmation_reports_dir: str) -> InteractiveBrokersReportParser:
    parser_object = InteractiveBrokersReportParser()

    activity_reports = csvs_in_dir(activity_reports_dir)
    confirmation_reports = csvs_in_dir(confirmation_reports_dir)

    for apath in activity_reports:
        logging.info('Activity report %s', apath)
    for cpath in confirmation_reports:
        logging.info('Confirmation report %s', cpath)

    logging.info('start reports parse')
    parser_object.parse_csv(
        activity_csvs=activity_reports,
        trade_confirmation_csvs=confirmation_reports,
    )
    logging.info(f'end reports parse {parser_object}')

    return parser_object


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--activity-reports-dir', type=str, required=True, help='directory with InteractiveBrokers .csv activity reports')
    parser.add_argument('--confirmation-reports-dir', type=str, required=True, help='directory with InteractiveBrokers .csv confirmation reports')
    parser.add_argument('--cache-dir', type=str, default='.', help='directory for caching (CBR RUB exchange rates)')
    parser.add_argument('--years', type=lambda x: [int(v.strip()) for v in x.split(',')], default=[], help='comma separated years for final report, omit for all')
    parser.add_argument('--verbose', nargs='?', default=False, const=True, help='do not "prune" reversed dividends, show dividends tax percent, etc.')
    parser.add_argument('--ndfl-summary', nargs='?', default=False, const=True, help='show summary or 3-ndfl year reporting')
    args = parser.parse_args()

    if os.path.abspath(args.activity_reports_dir) == os.path.abspath(args.confirmation_reports_dir):
        print('--activity-reports-dir and --confirmation-reports-dir MUST be different directories')
        return

    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    parser_object = parse_reports(args.activity_reports_dir, args.confirmation_reports_dir)

    trades = parser_object.trades
    dividends = parser_object.dividends
    fees = parser_object.fees
    interests = parser_object.interests

    if not trades:
        logging.warning('no trades found')
        return

    # fixme first_year without dividends
    first_year = min(trades[0].trade_date.year, dividends[0].date.year) if dividends else trades[0].trade_date.year
    cbr_client_usd = cbr.ExchangeRatesRUB(currency=Currency.USD, year_from=first_year, cache_dir=args.cache_dir)

    dividends_report = prepare_dividends_report(dividends, cbr_client_usd, args.verbose) if dividends else None
    fees_report = prepare_fees_report(fees, cbr_client_usd) if fees else None
    interests_report = prepare_interests_report(interests, cbr_client_usd) if interests else None

    analyzer = TradesAnalyzer(trades)
    finished_trades = analyzer.finished_trades
    portfolio = analyzer.final_portfolio

    trades_report = prepare_trades_report(finished_trades, cbr_client_usd) if finished_trades else None

    if args.ndfl_summary:
        show_ndfl_report(trades_report, dividends_report, fees_report, interests_report, args.years, not args.verbose)
    else:
        show_report(trades_report, dividends_report, fees_report, interests_report, args.years, args.verbose)
        show_portfolio_report(portfolio)


if __name__ == '__main__':
    main()

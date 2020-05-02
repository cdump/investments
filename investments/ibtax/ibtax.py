import argparse
import os
from typing import List, Optional

import pandas

from investments.currency import Currency
from investments.data_providers.cbr import ExchangeRatesRUB
from investments.money import Money
from investments.report_parsers.ib import InteractiveBrokersReportParser
from investments.trades_fifo import analyze_trades_fifo


def prepare_trades_report(df: pandas.DataFrame, usdrub_rates_df: pandas.DataFrame):
    # tax_date_column = 'date'
    tax_date_column = 'settle_date'

    df['date'] = df['datetime'].dt.normalize()
    df['settle_date'] = pandas.to_datetime(df['settle_date'])

    tax_years = df.groupby('N')[tax_date_column].max().map(lambda x: x.year).rename('tax_year')
    df = df.join(tax_years, how='left', on='N')

    df = df.join(usdrub_rates_df, how='left', on=tax_date_column)
    df['total_rub'] = df.apply(lambda x: x['total'].convert_to(x['rate']).round(digits=2), axis=1)

    df['profit_rub'] = df['total_rub']
    df.loc[df['quantity'] >= 0, 'profit_rub'] *= -1

    profit = df.groupby('N')['profit_rub'].sum().reset_index().set_index('N')
    df = df.join(profit, how='left', on='N', lsuffix='del')
    df.drop(columns=['profit_rubdel'], axis=0, inplace=True)
    df.loc[~df.index.isin(df.groupby('N')['datetime'].idxmax()), 'profit_rub'] = Money(0, Currency.RUB)

    return df


def prepare_dividends_report(dividends, usdrub_rates_df: pandas.DataFrame):
    df_data = [(i + 1, x.ticker, pandas.to_datetime(x.date), x.amount, x.tax) for i, x in enumerate(dividends)]
    df = pandas.DataFrame(df_data, columns=['N', 'ticker', 'date', 'amount', 'tax_paid'])
    df['tax_year'] = df['date'].map(lambda x: x.year)

    df = df.join(usdrub_rates_df, how='left', on='date')

    # df['tax_rate'] = df.apply(lambda x: round(x['tax_paid'].amount * 100 / x['amount'].amount, 2), axis=1)
    df['amount_rub'] = df.apply(lambda x: x['amount'].convert_to(x['rate']).round(digits=2), axis=1)
    df['tax_paid_rub'] = df.apply(lambda x: x['tax_paid'].convert_to(x['rate']).round(digits=2), axis=1)
    return df


def show_report(trades: Optional[pandas.DataFrame], dividends: Optional[pandas.DataFrame], portfolio, filter_years: List[int]):
    years = set()
    for report in (trades, dividends):
        if report is not None:
            years |= set(report['tax_year'].unique())

    for year in years:  # noqa: WPS426
        if filter_years and (year not in filter_years):
            continue
        print('______' * 8, f'  {year}  ', '______' * 8, '\n')

        if dividends is not None:
            dividends_year = dividends[dividends['tax_year'] == year].drop(columns=['tax_year'])
            dividends_year['N'] -= dividends_year['N'].iloc[0] - 1

            print('>>> DIVIDENDS <<<')
            print(dividends_year.set_index(['N', 'ticker', 'date']).to_string())
            # print('\n>>> DIVIDENDS PROFIT BEFORE TAXES:\n   ', dividends_year['amount_rub'].sum())
            print('\n\n')

        if trades is not None:
            trades_year = trades[trades['tax_year'] == year].drop(columns=['tax_year', 'datetime'])
            trades_year['N'] -= trades_year['N'].iloc[0] - 1

            print('>>> TRADES <<<')
            print(trades_year.set_index(['N', 'ticker', 'date']).to_string())
            print('\n\n')

            print('>>> TRADES RESULTS BEFORE TAXES <<<')
            tp = trades_year.groupby(lambda idx: (
                trades_year.loc[idx, 'ticker'].kind,
                'expenses' if trades_year.loc[idx, 'quantity'] > 0 else 'income',
            ))['total_rub'].sum().reset_index()
            tp = tp['index'].apply(pandas.Series).join(tp).pivot(index=0, columns=1, values='total_rub')
            tp.index.name = ''
            tp.columns.name = ''
            tp['profit'] = tp['income'] - tp['expenses']
            print(tp.reset_index().to_string())

        print('______' * 8, f'EOF {year}', '______' * 8, '\n\n\n')

    print('>>> PORTFOLIO <<<')
    for v in portfolio:
        print(v['quantity'], ' x ', v['ticker'])


def csvs_in_dir(directory: str):
    ret = []
    for fname in os.scandir(directory):
        if not fname.is_file():
            continue
        if not fname.name.lower().endswith('.csv'):
            continue
        ret.append(fname.path)
    return ret


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--activity-reports-dir', type=str, required=True, help='directory with InteractiveBrokers .csv activity reports')
    parser.add_argument('--confirmation-reports-dir', type=str, required=True, help='directory with InteractiveBrokers .csv confirmation reports')
    parser.add_argument('--cache-dir', type=str, default='.', help='directory for caching (CBR RUB exchange rates)')
    parser.add_argument('--years', type=lambda x: [int(v.strip()) for v in x.split(',')], default=[], help='comma separated years for final report, omit for all')
    args = parser.parse_args()

    if os.path.abspath(args.activity_reports_dir) == os.path.abspath(args.confirmation_reports_dir):
        print('--activity-reports-dir and --confirmation-reports-dir MUST be different directories')
        return

    p = InteractiveBrokersReportParser()

    activity_reports = csvs_in_dir(args.activity_reports_dir)
    confirmation_reports = csvs_in_dir(args.confirmation_reports_dir)

    for apath in activity_reports:
        print(f'[*] Activity report {apath}')
    for cpath in confirmation_reports:
        print(f'[*] Confirmation report {cpath}')

    print('========' * 8)
    print('')

    p.parse_csv(
        activity_csvs=activity_reports,
        trade_confirmation_csvs=confirmation_reports,
    )

    trades = p.trades()
    dividends = p.dividends()

    if not trades:
        print('no trades found')
        return

    first_year = min(trades[0].datetime.year, dividends[0].date.year) if dividends else trades[0].datetime.year
    cbrates_df = ExchangeRatesRUB(year_from=first_year, cache_dir=args.cache_dir).dataframe()

    dividends_report = prepare_dividends_report(dividends, cbrates_df) if dividends else None

    portfolio, finished_trades = analyze_trades_fifo(trades)
    if finished_trades:
        finished_trades_df = pandas.DataFrame(finished_trades, columns=finished_trades[0]._fields)  # noqa: WPS437
        trades_report = prepare_trades_report(finished_trades_df, cbrates_df)
    else:
        trades_report = None

    show_report(trades_report, dividends_report, portfolio, args.years)


if __name__ == '__main__':
    # cdir = os.path.dirname(os.path.abspath(__file__))
    # bdir = os.path.join(cdir, '../../')
    # sys.path.insert(0, os.path.normpath(bdir))
    main()

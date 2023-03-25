from abc import ABC, abstractmethod
from enum import Enum
from typing import Iterable, List, Optional, Union

import pandas  # type: ignore
from tabulate import tabulate
from weasyprint import CSS, HTML  # type: ignore

from investments.money import Money
from investments.trades_fifo import PortfolioElement


def apply_round_for_dataframe(source: pandas.DataFrame, columns: Iterable, digits: int = 2) -> pandas.DataFrame:
    source[list(columns)] = source[list(columns)].applymap(
        lambda x: x.round(digits=digits) if isinstance(x, Money) else round(x, digits),
    )
    return source


class DisplayMode(Enum):
    PRINT = 'print'
    PDF = 'pdf'


class ReportPresenter(ABC):
    def __init__(self, verbose: bool = False, dst_filepath: Optional[str] = None, date_format: str = '%d.%m.%Y'):
        assert dst_filepath is None or dst_filepath.endswith('.pdf')

        self._output: str = ''
        self._dst_filepath: Optional[str] = dst_filepath
        self._verbose: bool = verbose
        self._display_mode: DisplayMode = DisplayMode.PDF if dst_filepath else DisplayMode.PRINT
        self._date_format = date_format

    def is_print_mode(self) -> bool:
        return self._display_mode == DisplayMode.PRINT

    @abstractmethod
    def prepare_report(self, trades: Optional[pandas.DataFrame], dividends: Optional[pandas.DataFrame],
                       fees: Optional[pandas.DataFrame], interests: Optional[pandas.DataFrame],
                       portfolio: List[PortfolioElement], filter_years: List[int]):  # noqa: WPS319
        pass

    def present(self):
        if self.is_print_mode():
            print(self._output)
        else:
            css_style = """
            @page {
                size: a4 landscape;
                margin: 1cm;
            }
            table, th, td {
                border: 2px solid black;
                border-collapse: collapse;
            }
            div.pagebreak {
                page-break-after: always;
            }
            h1.year {
                page-break-before: always;
            }
            """
            HTML(string=self._output).write_pdf(self._dst_filepath, stylesheets=[CSS(string=css_style)])

    def _append_output(self, msg: str):
        self._output += msg

    def _append_year_header(self, year: int):
        if self.is_print_mode():
            line = '______' * 8
            self._append_output(f'\n\n\n>>> {line} {year} {line} <<<\n')
        else:
            self._append_output(f'<h1 class="year">{year}</h1>')

    def _append_header(self, header: str):
        if self.is_print_mode():
            self._append_output(f'\n>>> {header} <<<\n')
        else:
            self._append_output(f'<h2>{header}</h2>')

    def _start_new_page(self):
        if self.is_print_mode():
            self._append_output('\n\n')
        else:
            self._append_output('<div class="pagebreak"></div>')

    def _append_table(self, tabulate_data: Union[list, pandas.DataFrame], headers='keys', **kwargs) -> str:
        defaults = {
            'showindex': False,
            'numalign': 'decimal',
            'stralign': 'right',
            'tablefmt': 'presto' if self.is_print_mode() else 'html',
        }
        if isinstance(tabulate_data, pandas.DataFrame):
            for col in tabulate_data.select_dtypes(include=['datetime64']):
                tabulate_data[col] = tabulate_data[col].dt.strftime(self._date_format)

        defaults.update(**kwargs)
        return tabulate(tabulate_data, headers=headers, **defaults)  # type: ignore


class NativeReportPresenter(ReportPresenter):
    def prepare_report(self, trades: Optional[pandas.DataFrame], dividends: Optional[pandas.DataFrame],
                       fees: Optional[pandas.DataFrame], interests: Optional[pandas.DataFrame],
                       portfolio: List[PortfolioElement], filter_years: List[int]):  # noqa: WPS318,WPS319
        years = set()
        for report in (trades, dividends, fees, interests):
            if report is not None:
                years |= set(report['tax_year'].unique())

        for year in years:  # noqa: WPS426
            if filter_years and (year not in filter_years):
                continue

            self._append_year_header(year)

            if dividends is not None:
                self._append_dividends_report(dividends, year)

            if trades is not None:
                self._append_trades_report(trades, year)

            if fees is not None:
                self._append_fees_report(fees, year)

            if interests is not None:
                self._append_interests_report(interests, year)

        self._append_portfolio_report(portfolio)

    def _append_portfolio_report(self, portfolio: List[PortfolioElement]):
        self._start_new_page()
        self._append_header('PORTFOLIO')
        self._append_output(self._append_table([[str(elem.ticker), elem.quantity] for elem in portfolio], headers=['Ticker', 'Quantity'], colalign=('left',)))

    def _append_dividends_report(self, dividends: pandas.DataFrame, year: int):
        dividends_by_year = dividends[dividends['tax_year'] == year].drop(columns=['tax_year'])
        if dividends_by_year.empty:
            return

        dividends_by_year['N'] -= dividends_by_year['N'].iloc[0] - 1
        dividends_presenter = dividends_by_year.copy(deep=True)
        if not self._verbose:
            apply_round_for_dataframe(dividends_presenter, {'rate'}, 4)
            apply_round_for_dataframe(dividends_presenter, {'amount', 'amount_rub', 'tax_paid', 'tax_paid_rub'}, 2)
            dividends_presenter = dividends_presenter.drop(columns=['tax_rate'])

        self._start_new_page()
        self._append_header('DIVIDENDS')
        self._append_output(self._append_table(dividends_presenter))

    def _append_fees_report(self, fees: pandas.DataFrame, year: int):
        fees_by_year = fees[fees['tax_year'] == year].drop(columns=['tax_year'])
        if fees_by_year.empty:
            return

        feed_presenter = fees_by_year.copy(deep=True)
        if not self._verbose:
            apply_round_for_dataframe(feed_presenter, {'rate'}, 4)
            apply_round_for_dataframe(feed_presenter, {'amount', 'amount_rub'}, 2)

        self._start_new_page()
        self._append_header('OTHER FEES')
        self._append_output(self._append_table(feed_presenter))

    def _append_interests_report(self, interests: pandas.DataFrame, year: int):
        interests_by_year = interests[interests['tax_year'] == year].drop(columns=['tax_year'])
        if interests_by_year.empty:
            return

        interests_presenter = interests_by_year.copy(deep=True)
        if not self._verbose:
            apply_round_for_dataframe(interests_presenter, {'rate'}, 4)
            apply_round_for_dataframe(interests_presenter, {'amount', 'amount_rub'}, 2)

        self._start_new_page()
        self._append_header('INTERESTS')
        self._append_output(self._append_table(interests_presenter))

    def _append_trades_report(self, trades: pandas.DataFrame, year: int):
        trades_by_year = trades[trades['tax_year'] == year].drop(columns=['tax_year'])
        if trades_by_year.empty:
            return

        trades_by_year['N'] -= trades_by_year['N'].iloc[0] - 1

        trades_presenter = trades_by_year.copy(deep=True).set_index(['N', 'ticker', 'trade_date'])
        trades_presenter['ticker_name'] = trades_presenter.apply(lambda x: str(x.name[1]), axis=1)

        trades_presenter = trades_presenter[[
            'ticker_name', 'date', 'settle_date', 'quantity', 'price', 'fee_per_piece', 'price_rub',
            'fee_per_piece_rub', 'fee', 'total', 'total_rub', 'settle_rate', 'fee_rate', 'profit_rub',
        ]]

        if not self._verbose:
            apply_round_for_dataframe(trades_presenter, {'price', 'total', 'total_rub', 'profit_rub'}, 2)
            apply_round_for_dataframe(trades_presenter, {'fee', 'settle_rate', 'fee_rate'}, 4)
            trades_presenter = trades_presenter.drop(columns=['fee_per_piece', 'fee_per_piece_rub', 'price_rub'])

        self._start_new_page()
        self._append_header('TRADES')
        self._append_output(self._append_table(trades_presenter))

        self._start_new_page()
        self._append_header('TRADES RESULTS BEFORE TAXES')
        trades_summary_presenter = trades_by_year.copy(deep=True).groupby(lambda idx: (
            trades_by_year.loc[idx, 'ticker'].kind,
            'expenses' if trades_by_year.loc[idx, 'quantity'] > 0 else 'income',
        ))['total_rub'].sum().reset_index()
        trades_summary_presenter = trades_summary_presenter['index'].apply(pandas.Series).join(trades_summary_presenter).pivot(index=0, columns=1, values='total_rub')
        trades_summary_presenter.index.name = ''
        trades_summary_presenter.columns.name = ''
        trades_summary_presenter['profit'] = trades_summary_presenter['income'] + trades_summary_presenter['expenses']

        if not self._verbose:
            apply_round_for_dataframe(trades_summary_presenter, {'expenses', 'income', 'profit'}, 2)

        self._append_output(self._append_table(trades_summary_presenter.reset_index()))

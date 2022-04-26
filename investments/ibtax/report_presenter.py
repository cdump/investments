import operator
from abc import ABC, abstractmethod
from decimal import Decimal
from enum import Enum
from typing import Iterable, List, Optional, Union

import pandas  # type: ignore
from tabulate import tabulate
from weasyprint import CSS, HTML  # type: ignore

from investments.currency import Currency
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


# ставка налога по умолчанию, в процентах
TAX_RATE = 13


class ReportPresenter(ABC):
    def __init__(self, verbose: bool = False, dst_filepath: Optional[str] = None):
        assert dst_filepath is None or dst_filepath.endswith('.pdf')

        self._output: str = ''
        self._dst_filepath: Optional[str] = dst_filepath
        self._verbose: bool = verbose
        self._display_mode: DisplayMode = DisplayMode.PDF if dst_filepath else DisplayMode.PRINT

    def is_print_mode(self) -> bool:
        return self._display_mode == DisplayMode.PRINT

    def rounding_enabled(self) -> bool:
        return not self._verbose

    @staticmethod
    def filter_by_year(frame: pandas.DataFrame, year: int) -> Optional[pandas.DataFrame]:
        frame_by_year = frame[frame['tax_year'] == year].drop(columns=['tax_year'])
        if frame_by_year.empty:
            return None

        return frame_by_year

    @abstractmethod
    def prepare_report(self, trades: Optional[pandas.DataFrame], dividends: Optional[pandas.DataFrame],
                       fees: Optional[pandas.DataFrame], interests: Optional[pandas.DataFrame],
                       portfolio: List[PortfolioElement], filter_years: List[int]):  # noqa: WPS319
        pass

    def present(self):
        if self.is_print_mode():
            print(self._output)
        else:
            css_style = '@page { size: a3 landscape; margin: 1cm;} table, th, td {border: 2px solid black; border-collapse: collapse; padding: 5px;}'
            HTML(string=self._output).write_pdf(self._dst_filepath, stylesheets=[CSS(string=css_style)])

    def _append_output(self, msg: str):
        self._output += msg

    def _append_header(self, header: str):
        if self.is_print_mode():
            self._append_output(f'\n>>> {header} <<<\n')
        else:
            self._append_output(f'<br/><h1>{header}</h1><br/>')

    def _append_sub_header(self, header: str):
        if self.is_print_mode():
            self._append_output(f'\n{header}\n')
        else:
            self._append_output(f'<h3>{header}</h3>')

    def _append_paragraph(self, message: str):
        if self.is_print_mode():
            self._append_output(f'\n{message}')
        else:
            self._append_output(f'<p>{message}</p>')

    def _append_padding(self):
        if self.is_print_mode():
            self._append_output('\n\n\n')
        else:
            self._append_output('<br/><br/><br/>')

    def _append_table(
        self,
        tabulate_data: Union[list, pandas.DataFrame],
        headers: Union[str, List[str]] = 'keys',
        **kwargs,
    ):
        defaults = {
            'showindex': False,
            'numalign': 'decimal',
            'stralign': 'right',
            'tablefmt': 'presto' if self.is_print_mode() else 'html',
        }
        defaults.update(**kwargs)
        self._append_output(tabulate(tabulate_data, headers=headers, **defaults))  # type: ignore


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

    def _append_year_header(self, year: int):
        title_bracket = '______' * 8
        self._append_header(f'{title_bracket}  {year}  {title_bracket}')

    def _append_portfolio_report(self, portfolio: List[PortfolioElement]):
        self._append_padding()
        self._append_header('PORTFOLIO')
        self._append_table(
            [[str(elem.ticker), elem.quantity] for elem in portfolio],
            headers=['Ticker', 'Quantity'],
            colalign=('left',),
        )

    def _append_dividends_report(self, dividends: pandas.DataFrame, year: int):
        dividends_by_year = self.filter_by_year(dividends, year)
        if dividends_by_year is None:
            return

        dividends_by_year['N'] -= dividends_by_year['N'].iloc[0] - 1
        dividends_presenter = dividends_by_year.copy(deep=True)
        dividends_presenter['date'] = dividends_presenter['date'].dt.date
        if self.rounding_enabled():
            apply_round_for_dataframe(dividends_presenter, {'rate'}, 4)
            apply_round_for_dataframe(dividends_presenter, {'amount', 'amount_rub', 'tax_paid', 'tax_paid_rub'}, 2)
            dividends_presenter = dividends_presenter.drop(columns=['tax_rate'])

        self._append_padding()
        self._append_header('DIVIDENDS')
        self._append_table(dividends_presenter)

    def _append_fees_report(self, fees: pandas.DataFrame, year: int):
        fees_by_year = self.filter_by_year(fees, year)
        if fees_by_year is None:
            return

        feed_presenter = fees_by_year.copy(deep=True)
        feed_presenter['date'] = feed_presenter['date'].dt.date
        if self.rounding_enabled():
            apply_round_for_dataframe(feed_presenter, {'rate'}, 4)
            apply_round_for_dataframe(feed_presenter, {'amount', 'amount_rub'}, 2)

        self._append_padding()
        self._append_header('OTHER FEES')
        self._append_table(feed_presenter)

    def _append_interests_report(self, interests: pandas.DataFrame, year: int):
        interests_by_year = self.filter_by_year(interests, year)
        if interests_by_year is None:
            return

        interests_presenter = interests_by_year.copy(deep=True)
        interests_presenter['date'] = interests_presenter['date'].dt.date
        if self.rounding_enabled():
            apply_round_for_dataframe(interests_presenter, {'rate'}, 4)
            apply_round_for_dataframe(interests_presenter, {'amount', 'amount_rub'}, 2)

        self._append_padding()
        self._append_header('INTERESTS')
        self._append_table(interests_presenter)

    def _append_trades_report(self, trades: pandas.DataFrame, year: int):
        trades_by_year = self.filter_by_year(trades, year)
        if trades_by_year is None:
            return

        trades_by_year['N'] -= trades_by_year['N'].iloc[0] - 1

        trades_presenter = trades_by_year.copy(deep=True).set_index(['N', 'ticker', 'trade_date'])
        trades_presenter['settle_date'] = trades_presenter['settle_date'].dt.date
        trades_presenter['ticker_name'] = trades_presenter.apply(lambda x: str(x.name[1]), axis=1)

        trades_presenter = trades_presenter[[
            'ticker_name', 'date', 'settle_date', 'quantity', 'price', 'fee_per_piece', 'price_rub',
            'fee_per_piece_rub', 'fee', 'total', 'total_rub', 'settle_rate', 'fee_rate', 'profit_rub',
        ]]

        if self.rounding_enabled():
            apply_round_for_dataframe(trades_presenter, {'price', 'total', 'total_rub', 'profit_rub'}, 2)
            apply_round_for_dataframe(trades_presenter, {'fee', 'settle_rate', 'fee_rate'}, 4)
            trades_presenter = trades_presenter.drop(columns=['fee_per_piece', 'fee_per_piece_rub', 'price_rub'])

        self._append_padding()
        self._append_header('TRADES')
        self._append_table(trades_presenter)

        self._append_padding()
        self._append_header('TRADES RESULTS BEFORE TAXES')
        trades_summary_presenter = trades_by_year.copy(deep=True).groupby(lambda idx: (
            trades_by_year.loc[idx, 'ticker'].kind,
            'expenses' if trades_by_year.loc[idx, 'quantity'] > 0 else 'income',
        ))['total_rub'].sum().reset_index()
        trades_summary_presenter = trades_summary_presenter['index'].apply(pandas.Series).join(trades_summary_presenter).pivot(index=0, columns=1, values='total_rub')
        trades_summary_presenter.index.name = ''
        trades_summary_presenter.columns.name = ''
        trades_summary_presenter['profit'] = trades_summary_presenter['income'] + trades_summary_presenter['expenses']

        if self.rounding_enabled():
            apply_round_for_dataframe(trades_summary_presenter, {'expenses', 'income', 'profit'}, 2)

        self._append_table(trades_summary_presenter.reset_index())


class NdflDetailsReportPresenter(ReportPresenter):
    TAX_RATE = Decimal(TAX_RATE / 100)

    DIVIDENDS_INCOME_CODE = '1010'
    INTERESTS_INCOME_CODE = '4800'
    TRADES_EXPENSE_CODE = '201'
    TRADES_INCOME_CODE = '1530'

    def prepare_report(self, trades: Optional[pandas.DataFrame], dividends: Optional[pandas.DataFrame],
                       fees: Optional[pandas.DataFrame], interests: Optional[pandas.DataFrame],
                       portfolio: List[PortfolioElement], filter_years: List[int]):  # noqa: WPS318,WPS319

        assert len(filter_years) == 1

        year = filter_years.pop()

        self._append_covering_letter(year)

        if trades is not None:
            self._append_trades_report(trades, fees, year)

        if dividends is not None:
            self._append_dividends_report(dividends, year)

        if interests is not None:
            self._append_interests_report(interests, year)

    def _append_summary(self, income: Decimal = None, expense: Decimal = None, total_tax: int = 0, paid_tax: int = 0):
        if income is None:
            income = Decimal(0)
        if expense is None:
            expense = Decimal(0)
        self._append_sub_header('Сводка')
        self._append_table(
            [
                ['Общая сумма доходов', income],
                ['Общая сумма расходов', expense],
                ['Налоговая база', income - expense],
                ['Исчисленный налог', total_tax],
                ['Сумма уплаченного налога в иностранном государстве', paid_tax],
                ['Налог к уплате', total_tax - paid_tax],
            ],
            headers='',
            floatfmt='.2f',
        )

    def _append_covering_letter(self, year: int):
        self._append_header('Пояснительная записка')
        self._append_paragraph('%s - %s' % (
            f'За {year} год мною были получены доходы от источника, находящегося за пределами Российской Федерации',
            ' - в частности, от американской брокерской компании Interactive Brokers LLC.',
        ))
        self._append_paragraph('Расчет налоговой базы и суммы налога сделан на основании отчетов брокера, прилагаемого к настоящей декларации, и представлен в данном документе.')
        self._append_paragraph('В расчете отражены доходы следующих видов: от реализации ЦБ, проценты на остаток, дивиденды.')
        self._append_paragraph('Стоимость приобретения реализованных ЦБ/ПФИ рассчитана по методу ФИФО в соответствии с НК РФ.')

    def _append_trades_report(self, trades: pandas.DataFrame, fees: Optional[pandas.DataFrame], year: int):
        trades_by_year = self.filter_by_year(trades, year)
        if trades_by_year is None:
            return

        trades_by_year['N'] -= trades_by_year['N'].iloc[0] - 1

        trades_presenter = trades_by_year.copy(deep=True).set_index(['N', 'ticker', 'trade_date'])
        trades_presenter['settle_date'] = trades_presenter['settle_date'].dt.date
        trades_presenter['ticker_name'] = trades_presenter.apply(lambda x: str(x.name[1].symbol), axis=1)
        trades_presenter['raw_total_amount'] = trades_presenter.apply(lambda x: (abs(x.quantity) * x.price).amount, axis=1)
        trades_presenter['raw_fee_amount'] = trades_presenter.apply(lambda x: abs(x.fee.amount), axis=1)
        trades_presenter['raw_settle_rate'] = trades_presenter.apply(lambda x: x.settle_rate.amount, axis=1)
        trades_presenter['raw_fee_rate'] = trades_presenter.apply(lambda x: x.fee_rate.amount, axis=1)
        trades_presenter['raw_total_amount_rub'] = trades_presenter.apply(lambda x: x.raw_settle_rate * x.raw_total_amount, axis=1)
        trades_presenter['raw_fee_amount_rub'] = trades_presenter.apply(lambda x: x.raw_fee_rate * x.raw_fee_amount, axis=1)
        trades_presenter['currency_code'] = trades_presenter.apply(lambda x: x.price.currency.iso_numeric_code, axis=1)
        trades_presenter['fee_currency_code'] = trades_presenter.apply(lambda x: x.fee.currency.iso_numeric_code, axis=1)

        columns = ['Дата операции', 'Код', 'Наименование', 'Количество ЦБ', 'Сумма в валюте', 'Код валюты', 'Курс ЦБ', 'Сумма в рублях']
        if self.rounding_enabled():
            apply_round_for_dataframe(trades_presenter, {'raw_settle_rate', 'raw_fee_rate'}, 4)
            apply_round_for_dataframe(trades_presenter, {'raw_total_amount', 'raw_fee_amount', 'raw_total_amount_rub', 'raw_fee_amount_rub'}, 2)

        self._append_header(f'Доходы от операций с ценными бумагами за {year} год')
        self._append_sub_header('Детализация')

        total_income = Decimal(0)
        total_expense = Decimal(0)

        for _, trade_operations in trades_presenter.groupby('N'):
            self._append_sub_header(f'Наименование ЦБ: {trade_operations["ticker_name"].iloc[0]}')
            operations = []
            for _, row in trade_operations.iterrows():
                operations.append([
                    row.settle_date,
                    self.TRADES_EXPENSE_CODE if row.quantity > 0 else self.TRADES_INCOME_CODE,
                    'Приобретение ЦБ' if row.quantity > 0 else 'Продажа ЦБ',
                    row.quantity,
                    row.raw_total_amount,
                    row.currency_code,
                    row.raw_settle_rate,
                    row.raw_total_amount_rub,
                ])

                operations.append([
                    row.date,
                    self.TRADES_EXPENSE_CODE,
                    'Комиссии брокера за сделку',
                    0,
                    row.raw_fee_amount,
                    row.fee_currency_code,
                    row.raw_fee_rate,
                    row.raw_fee_amount_rub,
                ])

            self._append_table(sorted(operations, key=operator.itemgetter(0)), headers=columns)

            income = sum((i[-1] for i in operations if i[1] == self.TRADES_INCOME_CODE))
            expense = sum((i[-1] for i in operations if i[1] == self.TRADES_EXPENSE_CODE))
            self._append_paragraph(f'Общая сумма доходов: {income} рублей')
            self._append_paragraph(f'Общая сумма расходов: {expense} рублей')
            self._append_paragraph(f'Финансовый результат: {income - expense} рублей')

            total_income += income
            total_expense += expense

        if fees is not None and not fees.empty:
            fees_expense = self._append_fees_report(fees, year)
            total_expense += fees_expense

        # суммы налогов округляются до целого рубля в соответствии с НК РФ
        tax = round((total_income - total_expense) * self.TAX_RATE)
        self._append_summary(total_income, total_expense, tax)

    def _append_fees_report(self, fees: pandas.DataFrame, year: int) -> Decimal:
        fees_by_year = self.filter_by_year(fees, year)
        if fees_by_year is None:
            return Decimal(0)

        feed_presenter = fees_by_year.copy(deep=True)

        feed_presenter['date'] = feed_presenter['date'].dt.date
        feed_presenter['income_code'] = self.TRADES_EXPENSE_CODE

        feed_presenter['raw_amount'] = feed_presenter.apply(lambda x: x.amount.amount * -1, axis=1)
        feed_presenter['raw_amount_rub'] = feed_presenter.apply(lambda x: x.amount_rub.amount * -1, axis=1)
        feed_presenter['currency_code'] = feed_presenter.apply(lambda x: x.amount.currency.iso_numeric_code, axis=1)
        feed_presenter['raw_rate'] = feed_presenter.apply(lambda x: 1 if x.amount.currency == Currency.RUB else x.rate.amount, axis=1)

        # это некоторая вольность трактовки, учитывая что в данных комиссиях в том числе встречается плата за актуальные снапшоты цен
        # однако кмк и эти комиссии можно подвести под НК РФ 214.1.10 пункт 12
        feed_presenter['description'] = feed_presenter.apply(lambda x: 'Комиссия за ведение счёта' if x.raw_amount > 0 else 'Возврат комиссии', axis=1)

        if self.rounding_enabled():
            apply_round_for_dataframe(feed_presenter, {'raw_rate'}, 4)
            apply_round_for_dataframe(feed_presenter, {'raw_amount', 'raw_amount_rub'}, 2)

        feed_presenter = feed_presenter[['date', 'income_code', 'description', 'raw_amount', 'currency_code', 'raw_rate', 'raw_amount_rub']]
        columns = ['Дата операции', 'Код', 'Наименование', 'Сумма в валюте', 'Код валюты', 'Курс ЦБ', 'Сумма в рублях']

        self._append_sub_header('Прочие расходы на ведение счёта')
        self._append_table(feed_presenter, headers=columns)
        expenses_summary = feed_presenter['raw_amount_rub'].sum()
        self._append_paragraph('Общая сумма доходов: 0 рублей')
        self._append_paragraph(f'Общая сумма расходов: {expenses_summary} рублей')
        self._append_paragraph(f'Финансовый результат: {expenses_summary * -1} рублей')

        return expenses_summary

    def _append_interests_report(self, interests: pandas.DataFrame, year: int):
        interests_by_year = self.filter_by_year(interests, year)
        if interests_by_year is None:
            return

        interests_presenter = interests_by_year.copy(deep=True)
        interests_presenter['date'] = interests_presenter['date'].dt.date
        interests_presenter['income_code'] = self.INTERESTS_INCOME_CODE
        interests_presenter['description'] = 'Начисление процентов на остаток по счёту'
        interests_presenter['raw_amount'] = interests_presenter.apply(lambda x: x.amount.amount, axis=1)
        interests_presenter['raw_amount_rub'] = interests_presenter.apply(lambda x: x.amount_rub.amount, axis=1)
        interests_presenter['currency_code'] = interests_presenter.apply(lambda x: x.amount.currency.iso_numeric_code, axis=1)
        interests_presenter['raw_rate'] = interests_presenter.apply(lambda x: 1 if x.amount.currency == Currency.RUB else x.rate.amount, axis=1)
        interests_presenter['total_tax'] = interests_presenter.apply(lambda x: x.raw_amount_rub * self.TAX_RATE, axis=1)
        interests_presenter['unpaid_tax'] = interests_presenter.apply(lambda x: x.total_tax, axis=1)

        if self.rounding_enabled():
            apply_round_for_dataframe(interests_presenter, {'raw_rate'}, 4)
            apply_round_for_dataframe(interests_presenter, {'raw_amount', 'raw_amount_rub'}, 2)

        # суммы налогов округляются до целого рубля в соответствии с НК РФ
        apply_round_for_dataframe(interests_presenter, {'total_tax', 'unpaid_tax'}, 0)

        interests_presenter = interests_presenter[[
            'date', 'income_code', 'description', 'raw_amount', 'currency_code', 'raw_rate',
            'raw_amount_rub', 'total_tax', 'unpaid_tax',
        ]]

        self._append_header(f'Иные доходы за {year} год')
        columns = [
            'Дата получения дохода', 'Код дохода', 'Наименование', 'Сумма дохода в валюте', 'Код валюты', 'Курс ЦБ', 'Сумма дохода в рублях',
            'Исчисленный налог в рублях', 'Налог к уплате в рублях',
        ]
        self._append_sub_header('Детализация')
        self._append_table(interests_presenter, headers=columns)
        self._append_summary(income=interests_presenter['raw_amount_rub'].sum(), total_tax=interests_presenter['total_tax'].sum())

    def _append_dividends_report(self, dividends: pandas.DataFrame, year: int):
        dividends_by_year = self.filter_by_year(dividends, year)
        if dividends_by_year is None:
            return

        dividends_presenter = dividends_by_year.copy(deep=True)
        dividends_presenter['date'] = dividends_presenter['date'].dt.date
        dividends_presenter['income_code'] = self.DIVIDENDS_INCOME_CODE
        dividends_presenter['ticker'] = dividends_presenter.apply(lambda x: x.ticker.symbol, axis=1)
        dividends_presenter['raw_amount'] = dividends_presenter.apply(lambda x: x.amount.amount, axis=1)
        dividends_presenter['currency_code'] = dividends_presenter.apply(lambda x: x.amount.currency.iso_numeric_code, axis=1)
        dividends_presenter['raw_rate'] = dividends_presenter.apply(lambda x: x.rate.amount, axis=1)
        dividends_presenter['raw_amount_rub'] = dividends_presenter.apply(lambda x: x.amount_rub.amount, axis=1)
        dividends_presenter['raw_tax_paid'] = dividends_presenter.apply(lambda x: x.tax_paid.amount, axis=1)
        dividends_presenter['raw_tax_paid_rub'] = dividends_presenter.apply(lambda x: x.tax_paid_rub.amount, axis=1)
        dividends_presenter['total_tax'] = dividends_presenter.apply(lambda x: x.raw_amount_rub * self.TAX_RATE, axis=1)
        dividends_presenter['unpaid_tax'] = dividends_presenter.apply(lambda x: x.total_tax - x.raw_tax_paid_rub, axis=1)

        if self.rounding_enabled():
            apply_round_for_dataframe(dividends_presenter, {'raw_rate'}, 4)
            apply_round_for_dataframe(dividends_presenter, {'raw_amount', 'raw_amount_rub', 'raw_tax_paid', 'raw_tax_paid_rub'}, 2)

        # суммы налогов округляются до целого рубля в соответствии с НК РФ
        apply_round_for_dataframe(dividends_presenter, {'total_tax', 'unpaid_tax'}, 0)

        dividends_presenter = dividends_presenter[[
            'date', 'income_code', 'ticker', 'raw_amount', 'currency_code', 'raw_rate', 'raw_amount_rub', 'raw_tax_paid', 'raw_tax_paid_rub',
            'total_tax', 'unpaid_tax',
        ]]

        self._append_header(f'Доходы в виде дивидендов за {year} год')
        columns = [
            'Дата получения дохода', 'Код дохода', 'Наименование', 'Сумма дохода в валюте', 'Код валюты',
            'Курс ЦБ', 'Сумма дохода в рублях', 'Сумма уплаченного налога в валюте', 'Сумма уплаченного налога в рублях',
            'Исчисленный налог в рублях', 'Налог к уплате в рублях',
        ]
        self._append_sub_header('Детализация')
        self._append_table(dividends_presenter, headers=columns)

        self._append_summary(
            income=dividends_presenter['raw_amount_rub'].sum(),
            total_tax=dividends_presenter['total_tax'].sum(),
            paid_tax=dividends_presenter['total_tax'].sum() - dividends_presenter['unpaid_tax'].sum(),
        )

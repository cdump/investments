"""
Утилита для подготовки отчёта о движении денежных средств для брокера Interactive Brokers (USA).

Актуальна на 15.01.2021
Отчёт нужно подавать каждый год до 1 июня или в течение месяца после закрытия счёта.
В будущем (уже в отчёте за 2021 год) обещают обновить требования в пользу большей детализации, но пока так.
@see статью 12 173-ФЗ «О валютном регулировании»

"""

import argparse
import csv
import logging
from typing import Any, List

from tabulate import tabulate

from investments.cash import Cash
from investments.money import Money
from investments.report_parsers.ib import InteractiveBrokersReportParser


class InteractiveBrokersCashReportParser(InteractiveBrokersReportParser):
    def parse_csv(self, *, activity_csvs: List[str], trade_confirmation_csvs: List[str]):
        assert len(activity_csvs) == 1
        with open(activity_csvs[0], newline='') as activity_fh:
            self._real_parse_activity_csv(csv.reader(activity_fh, delimiter=','), {
                'Cash Report': self._parse_cash_report,
            })


def parse_reports(activity_report_filepath: str) -> InteractiveBrokersCashReportParser:
    parser_object = InteractiveBrokersCashReportParser()

    logging.info(f'Activity report {activity_report_filepath}')

    logging.info('start reports parse')
    parser_object.parse_csv(activity_csvs=[activity_report_filepath], trade_confirmation_csvs=[])
    logging.info(f'end reports parse {parser_object}')

    return parser_object


def dds_specific_round(source_amount: Money) -> Money:
    return (source_amount / 1000).round(3)


def show_report(cash: List[Cash]):
    currencies = {x.amount.currency for x in cash}
    logging.info(f'currency={currencies}')

    for currency in currencies:
        operations = [op for op in cash if op.amount.currency == currency]
        begin_amount = dds_specific_round([op.amount for op in operations if op.description == 'Starting Cash'][0])
        end_amount = dds_specific_round([op.amount for op in operations if op.description == 'Ending Cash'][0])

        deposits_amount = Money(0, currency)
        withdrawals_amount = Money(0, currency)

        for op in operations:
            if 'Cash' not in op.description:
                if op.amount > Money(0, op.amount.currency):
                    deposits_amount += op.amount
                else:
                    withdrawals_amount += op.amount

        deposits_amount = dds_specific_round(deposits_amount)
        withdrawals_amount = dds_specific_round(withdrawals_amount)

        report: List[List[Any]] = [
            [f'{currency.name} {currency.iso_numeric_code}', 'Сумма в тысячах единиц'],
            ['Остаток денежных средств на счете на начало отчетного периода', begin_amount],
            ['Зачислено денежных средств за отчетный период', deposits_amount],
            ['Списано денежных средств за отчетный период', abs(withdrawals_amount)],
            ['Остаток денежных средств на счете на конец отчетного периода', end_amount],
        ]

        print('\n')
        print(tabulate(report, headers='firstrow', tablefmt='presto', colalign=('right', 'decimal')))
    print('\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--activity-report-filepath', type=str, required=True, help='InteractiveBrokers .csv activity report file path')
    parser.add_argument('--verbose', nargs='?', default=False, const=True, help='details mode')
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    parser_object = parse_reports(args.activity_report_filepath)

    cash_report = parser_object.cash
    logging.info(f'cash report={cash_report}')

    show_report(cash_report)


if __name__ == '__main__':
    main()

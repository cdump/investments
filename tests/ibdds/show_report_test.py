from investments.cash import Cash
from investments.currency import Currency
from investments.ibdds.ibdds import show_report
from investments.money import Money


def test_full_report(capsys):
    cash_operations = [
        Cash('deposit 1', Money(10.1, Currency.USD)),
        Cash('deposit 2', Money(178945.78915, Currency.USD)),
        Cash('wh 1', Money(-100.500, Currency.USD)),
        Cash('Starting Cash', Money(0.500, Currency.USD)),
        Cash('Ending Cash', Money(478.51, Currency.USD)),
        Cash('Unknown Cash', Money(100500, Currency.USD)),

        Cash('Starting Cash', Money(0., Currency.RUB)),
        Cash('deposit 1', Money(10.1, Currency.RUB)),
        Cash('Ending Cash', Money(17.89, Currency.RUB)),
    ]

    show_report(cash_operations)

    captured = capsys.readouterr()
    assert 'Остаток денежных средств на счете на начало отчетного периода |                   0.000₽' in captured.out
    assert 'Зачислено денежных средств за отчетный период |                   0.010₽' in captured.out
    assert 'Списано денежных средств за отчетный период |                   0.000₽' in captured.out
    assert 'Остаток денежных средств на счете на конец отчетного периода |                   0.018₽' in captured.out

    assert 'Остаток денежных средств на счете на начало отчетного периода |                   0.000$' in captured.out
    assert 'Зачислено денежных средств за отчетный период |                 178.956$' in captured.out
    assert 'Списано денежных средств за отчетный период |                   0.100$' in captured.out
    assert 'Остаток денежных средств на счете на конец отчетного периода |                   0.479$' in captured.out


def test_empty_report(capsys):
    cash_operations = [
        Cash('Starting Cash', Money(0, Currency.USD)),
        Cash('Ending Cash', Money(0, Currency.USD)),
        Cash('Starting Cash', Money(0, Currency.RUB)),
        Cash('Ending Cash', Money(0, Currency.RUB)),
    ]

    show_report(cash_operations)

    captured = capsys.readouterr()
    assert 'Остаток денежных средств на счете на начало отчетного периода |                   0.000$' in captured.out
    assert 'Зачислено денежных средств за отчетный период |                   0.000$' in captured.out
    assert 'Списано денежных средств за отчетный период |                   0.000$' in captured.out
    assert 'Остаток денежных средств на счете на конец отчетного периода |                   0.000$' in captured.out

    assert 'Остаток денежных средств на счете на начало отчетного периода |                   0.000₽' in captured.out
    assert 'Зачислено денежных средств за отчетный период |                   0.000₽' in captured.out
    assert 'Списано денежных средств за отчетный период |                   0.000₽' in captured.out
    assert 'Остаток денежных средств на счете на конец отчетного периода |                   0.000₽' in captured.out

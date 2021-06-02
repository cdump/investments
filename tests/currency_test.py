import pytest

from investments.currency import Currency


@pytest.mark.parametrize('search_value,res', [
    ('$', Currency.USD),
    ('EUR', Currency.EUR),
    ('RUR', Currency.RUB),
    ('RUB', Currency.RUB),
    ('₽', Currency.RUB),
    ('CAD', Currency.CAD),
])
def test_parse(search_value: str, res: Currency):
    assert Currency.parse(search_value) is res


def test_parse_failure():
    with pytest.raises(ValueError):
        assert Currency.parse('invalid')


@pytest.mark.parametrize('currency,expected_repr', [
    (Currency.USD, '$'),
    (Currency.RUB, '₽'),
    (Currency.CAD, 'CAD'),
])
def test_repr(currency: Currency, expected_repr: str):
    assert str(currency) == expected_repr


@pytest.mark.parametrize('currency,expected', [
    (Currency.USD, '840'),
    (Currency.RUB, '643'),
    (Currency.CAD, '124'),
])
def test_iso_numeric_code(currency: Currency, expected: str):
    assert currency.iso_numeric_code == expected


@pytest.mark.parametrize('currency,expected', [
    (Currency.USD, 'R01235'),
    (Currency.RUB, ''),
    (Currency.EUR, 'R01239'),
    (Currency.CAD, 'R01350'),
])
def test_cbr_code(currency: Currency, expected: str):
    assert currency.cbr_code == expected

import pytest

from investments.currency import Currency


@pytest.mark.parametrize('search_value,res', [
    ('$', Currency.USD),
    ('EUR', Currency.EUR),
    ('RUR', Currency.RUB),
    ('RUB', Currency.RUB),
    ('₽', Currency.RUB),
])
def test_parse(search_value: str, res: Currency):
    assert Currency.parse(search_value) is res


def test_parse_failure():
    with pytest.raises(ValueError):
        assert Currency.parse('invalid')


@pytest.mark.parametrize('currency,expected_repr', [
    (Currency.USD, '$'),
    (Currency.RUB, '₽'),
])
def test_repr(currency: Currency, expected_repr: str):
    assert str(currency) == expected_repr


@pytest.mark.parametrize('currency,expected', [
    (Currency.USD, '840'),
    (Currency.RUB, '643'),
])
def test_iso_numeric_code(currency: Currency, expected: str):
    assert currency.iso_numeric_code == expected

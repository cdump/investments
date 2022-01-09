import pytest  # type: ignore

from investments.data_providers.moex import get_board_candles
from investments.ticker import Ticker, TickerKind

def test_moex_get_board_candles():
    p = get_board_candles(Ticker('GAZP', TickerKind.Stock), None, start='2021-12-14', end='2021-12-14', interval=24)

    # reference data from https://www.moex.com/ru/issue.aspx?code=GAZP
    assert p['open'].item() == 307
    assert p['close'].item() == 319.35
    assert p['high'].item() == 320
    assert p['low'].item() == 289.78
    assert p['volume'].item() == 168689260

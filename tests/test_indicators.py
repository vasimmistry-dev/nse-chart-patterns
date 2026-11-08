import math

import pytest

from nse_chart_patterns import indicators as ind
from nse_chart_patterns.data import bars_from_tuples


def approx_list(values, expected, tol=1e-9):
    assert len(values) == len(expected)
    for v, e in zip(values, expected):
        if e is None:
            assert v is None
        else:
            assert v == pytest.approx(e, abs=tol)


def test_sma():
    approx_list(ind.sma([1, 2, 3, 4, 5], 3), [None, None, 2, 3, 4])


def test_sma_rejects_bad_period():
    with pytest.raises(ValueError):
        ind.sma([1, 2], 0)


def test_ema_seeded_with_sma():
    # period 3 -> alpha 0.5; seed = mean(1,2,3) = 2
    # idx3: 0.5*4 + 0.5*2 = 3 ; idx4: 0.5*10 + 0.5*3 = 6.5
    approx_list(ind.ema([1, 2, 3, 4, 10], 3), [None, None, 2, 3, 6.5])


def test_ema_short_input():
    assert ind.ema([1, 2], 3) == [None, None]


def test_rsi_wilder_hand_computed():
    closes = [1, 2, 3, 2, 3, 4]  # changes: +1 +1 -1 +1 +1
    out = ind.rsi(closes, 3)
    # seed avg gain 2/3, avg loss 1/3 -> RS 2 -> 66.667
    assert out[:3] == [None, None, None]
    assert out[3] == pytest.approx(100 - 100 / 3)
    # next: gain (2/3*2+1)/3 = 7/9, loss (1/3*2)/3 = 2/9 -> RS 3.5
    assert out[4] == pytest.approx(100 - 100 / 4.5)


def test_rsi_extremes():
    assert ind.rsi(list(range(20)), 14)[-1] == 100.0
    assert ind.rsi(list(range(20, 0, -1)), 14)[-1] == pytest.approx(0.0)
    assert ind.rsi([5] * 20, 14)[-1] == 50.0


def test_true_range_and_atr():
    bars = bars_from_tuples([
        (10, 11, 9, 10),     # TR 2 (first bar: high - low)
        (10, 12, 10, 11),    # TR 2
        (11, 11, 8, 9),      # TR max(3, 0, 3) = 3
        (12, 13, 12, 12.5),  # gap up: max(1, |13-9|, |12-9|) = 4
    ])
    assert ind.true_range(bars) == [2, 2, 3, 4]
    out = ind.atr(bars, 3)
    assert out[:2] == [None, None]
    assert out[2] == pytest.approx(7 / 3)
    assert out[3] == pytest.approx((7 / 3 * 2 + 4) / 3)


def test_bollinger_population_sd():
    mid, up, lo = ind.bollinger([1, 2, 3, 4, 5], 5, 2)
    assert mid[-1] == 3
    assert up[-1] == pytest.approx(3 + 2 * math.sqrt(2))
    assert lo[-1] == pytest.approx(3 - 2 * math.sqrt(2))
    assert up[0] is None


def test_bandwidth_and_volume_sma():
    bw = ind.bandwidth([1, 2, 3, 4, 5], 5, 2)
    assert bw[-1] == pytest.approx(4 * math.sqrt(2) / 3)
    bars = bars_from_tuples([(1, 1, 1, 1, v) for v in (100, 200, 300)])
    assert ind.volume_sma(bars, 2) == [None, 150, 250]

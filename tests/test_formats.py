import os
from contextlib import contextmanager

import numpy as np
import pytest

from oddslib.formats import (
    DEFAULT_INPUT_FORMAT,
    OddsFormat,
    convert_odds,
    decimal_to_odds,
    get_input_odds_format,
    get_output_odds_format,
    odds_to_decimal,
    resolve_input_format,
    resolve_output_format,
)


@contextmanager
def env_override(**values):
    backup = {key: os.environ.get(key) for key in values}
    try:
        os.environ.update(
            {key: value for key, value in values.items() if value is not None}
        )
        for key, value in values.items():
            if value is None and key in os.environ:
                del os.environ[key]
        yield
    finally:
        for key in values:
            if backup[key] is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = backup[key]


def test_default_env_fallbacks():
    with env_override(INPUT_ODDS_FORMAT=None, OUTPUT_ODDS_FORMAT=None):
        assert get_input_odds_format() is DEFAULT_INPUT_FORMAT
        assert get_output_odds_format() is DEFAULT_INPUT_FORMAT


def test_resolve_prefers_argument():
    with env_override(INPUT_ODDS_FORMAT="decimal"):
        assert resolve_input_format("american") is OddsFormat.AMERICAN
        assert resolve_input_format(OddsFormat.DECIMAL) is OddsFormat.DECIMAL
    with env_override(OUTPUT_ODDS_FORMAT="fractional"):
        assert resolve_output_format() is OddsFormat.FRACTIONAL


@pytest.mark.parametrize(
    "american, expected",
    [([150, -120], [2.5, 1.8333333333]), (100, 2.0)],
)
def test_american_to_decimal(american, expected):
    result = odds_to_decimal(american, odds_format=OddsFormat.AMERICAN)
    np.testing.assert_allclose(result, np.asarray(expected, dtype=np.float64))


@pytest.mark.parametrize(
    "fractional, expected",
    [(("5/2", "1/4"), [3.5, 1.25]), ((3, 1), [4.0])],
)
def test_fractional_to_decimal(fractional, expected):
    result = odds_to_decimal(fractional, odds_format=OddsFormat.FRACTIONAL)
    np.testing.assert_allclose(result, np.asarray(expected, dtype=np.float64))


def test_scalar_returns_scalar_float():
    american = odds_to_decimal(-120, odds_format=OddsFormat.AMERICAN)
    assert isinstance(american, float)
    assert american == pytest.approx(1.8333333333)


def test_scalar_fractional_to_decimal_returns_float():
    decimal = odds_to_decimal("5/2", odds_format=OddsFormat.FRACTIONAL)
    assert isinstance(decimal, float)
    assert decimal == pytest.approx(3.5)


def test_decimal_to_american_roundtrip():
    decimal = [2.1, 1.91]
    american = decimal_to_odds(decimal, target_format=OddsFormat.AMERICAN)
    roundtrip = odds_to_decimal(american, odds_format=OddsFormat.AMERICAN)
    np.testing.assert_allclose(roundtrip, np.asarray(decimal, dtype=np.float64))


def test_decimal_to_fractional_strings():
    decimal = [3.5, 1.25]
    fractional = decimal_to_odds(decimal, target_format=OddsFormat.FRACTIONAL)
    assert list(fractional) == ["5/2", "1/4"]


def test_decimal_to_odds_scalar_preserves_shape():
    american = decimal_to_odds(1.91, target_format=OddsFormat.AMERICAN)
    fractional = decimal_to_odds(3.5, target_format=OddsFormat.FRACTIONAL)
    assert isinstance(american, float)
    assert isinstance(fractional, str)
    assert american == pytest.approx(-109.89010989010989)
    assert fractional == "5/2"


def test_convert_router():
    american = [110, -200]
    fractional = convert_odds(
        american, from_format=OddsFormat.AMERICAN, to_format=OddsFormat.FRACTIONAL
    )
    assert list(fractional) == ["11/10", "1/2"]


def test_convert_scalar_router():
    fractional = convert_odds(110, from_format=OddsFormat.AMERICAN, to_format=OddsFormat.FRACTIONAL)
    assert isinstance(fractional, str)
    assert fractional == "11/10"


def test_scalar_american_roundtrip_exact():
    american = -110
    decimal = convert_odds(american, from_format=OddsFormat.AMERICAN, to_format=OddsFormat.DECIMAL)
    assert decimal == pytest.approx(1.9090909090909092)
    roundtrip = convert_odds(decimal, from_format=OddsFormat.DECIMAL, to_format=OddsFormat.AMERICAN)
    assert isinstance(roundtrip, float)
    assert roundtrip == american


def test_vector_roundtrip_exact_for_integer_books():
    american = np.asarray([150.0, -110.0, 100.0])
    decimal = convert_odds(american, from_format=OddsFormat.AMERICAN, to_format=OddsFormat.DECIMAL)
    restored = convert_odds(decimal, from_format=OddsFormat.DECIMAL, to_format=OddsFormat.AMERICAN)
    np.testing.assert_allclose(restored, american)


@pytest.mark.parametrize(
    "fractional, expected",
    [(["5/2", "11/4"], ["5/2", "11/4"]), (((3, 1), (5, 2)), ["3/1", "5/2"])],
)
def test_fractional_decimal_roundtrip_vector(fractional, expected):
    decimal = convert_odds(fractional, from_format=OddsFormat.FRACTIONAL, to_format=OddsFormat.DECIMAL)
    restored = convert_odds(decimal, from_format=OddsFormat.DECIMAL, to_format=OddsFormat.FRACTIONAL)
    assert list(restored) == expected


def test_fractional_decimal_roundtrip_scalar():
    fractional = "7/5"
    decimal = convert_odds(fractional, from_format=OddsFormat.FRACTIONAL, to_format=OddsFormat.DECIMAL)
    roundtrip = convert_odds(decimal, from_format=OddsFormat.DECIMAL, to_format=OddsFormat.FRACTIONAL)
    assert isinstance(roundtrip, str)
    assert roundtrip == fractional


def test_decimal_fractional_roundtrip_scalar():
    decimal = 2.75
    fractional = convert_odds(decimal, from_format=OddsFormat.DECIMAL, to_format=OddsFormat.FRACTIONAL)
    roundtrip = convert_odds(fractional, from_format=OddsFormat.FRACTIONAL, to_format=OddsFormat.DECIMAL)
    assert isinstance(roundtrip, float)
    assert roundtrip == pytest.approx(decimal)


def test_american_fractional_roundtrip_scalar():
    american = 150
    fractional = convert_odds(american, from_format=OddsFormat.AMERICAN, to_format=OddsFormat.FRACTIONAL)
    roundtrip = convert_odds(fractional, from_format=OddsFormat.FRACTIONAL, to_format=OddsFormat.AMERICAN)
    assert isinstance(roundtrip, float)
    assert roundtrip == pytest.approx(american)


def test_american_fractional_roundtrip_vector():
    american = np.asarray([-110.0, 145.0])
    fractional = convert_odds(american, from_format=OddsFormat.AMERICAN, to_format=OddsFormat.FRACTIONAL)
    restored = convert_odds(fractional, from_format=OddsFormat.FRACTIONAL, to_format=OddsFormat.AMERICAN)
    np.testing.assert_allclose(restored, american)


def test_invalid_american_zero():
    with pytest.raises(ValueError):
        odds_to_decimal(0, odds_format=OddsFormat.AMERICAN)


def test_invalid_decimal_low():
    with pytest.raises(ValueError):
        decimal_to_odds(0.99, target_format=OddsFormat.AMERICAN)

"""Odds format definitions and helpers."""

from __future__ import annotations

import os
from collections.abc import Iterable
from enum import Enum
from fractions import Fraction

import numpy as np
from numpy.typing import ArrayLike
from typing import cast, overload


class OddsFormat(str, Enum):
    """Supported odds representations for IO conversion layers."""

    DECIMAL = "decimal"
    AMERICAN = "american"
    FRACTIONAL = "fractional"

    @classmethod
    def parse(
        cls,
        value: str | None,
        *,
        default: "OddsFormat" | None = None,
    ) -> "OddsFormat":
        """Return the enum member for ``value`` or fall back to ``default``.

        Parsing is case-insensitive. ``default`` must be supplied when ``value`` is ``None``.
        """

        if value is None:
            if default is None:
                raise ValueError("Odds format value is required when no default is provided")
            return default

        normalized = value.strip().lower()

        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValueError(f"Unsupported odds format: {value}") from exc


_INPUT_ENV = "INPUT_ODDS_FORMAT"
_OUTPUT_ENV = "OUTPUT_ODDS_FORMAT"

DEFAULT_INPUT_FORMAT = OddsFormat.AMERICAN
DEFAULT_OUTPUT_FORMAT = OddsFormat.AMERICAN


ScalarOddsInput = int | float | Fraction | str | np.generic


def _ensure_1d(values: ArrayLike, *, dtype: type | None = None) -> np.ndarray:
    arr = np.asarray(values, dtype=dtype)
    if arr.ndim == 0:
        return np.expand_dims(arr, 0)
    if arr.ndim == 1:
        return arr
    raise ValueError("Odds converters expect scalars or 1-D arrays")


def _coerce_fractional_inputs(values: ArrayLike) -> list[object]:
    if isinstance(values, np.ndarray):
        if values.ndim == 0:
            return [cast(object, values.item())]
        if values.ndim == 1:
            return [cast(object, item) for item in values.tolist()]
        raise ValueError("Fractional odds expect scalars or 1-D arrays")

    if isinstance(values, (str, Fraction, int, float)):
        return [cast(object, values)]

    if isinstance(values, Iterable):
        seq = [cast(object, item) for item in values]
        if not seq:
            return []

        def _is_component(item: object) -> bool:
            return isinstance(item, (int, float, Fraction))

        if len(seq) == 2 and all(_is_component(item) for item in seq):
            return [cast(object, tuple(seq))]

        return seq

    return [cast(object, values)]


def _is_scalar_input(value: ArrayLike) -> bool:
    if isinstance(value, np.ndarray):
        return value.ndim == 0
    if isinstance(value, (np.generic, str, Fraction, int, float)):
        return True
    if isinstance(value, tuple):
        if len(value) == 2 and all(isinstance(item, (int, float, Fraction, np.generic)) for item in value):
            return True
    return np.isscalar(value)


def get_input_odds_format() -> OddsFormat:
    """Return the input odds format, falling back to the package default."""

    value = os.getenv(_INPUT_ENV)
    return OddsFormat.parse(value, default=DEFAULT_INPUT_FORMAT)


def get_output_odds_format() -> OddsFormat:
    """Return the output odds format, falling back to the package default."""

    value = os.getenv(_OUTPUT_ENV)
    return OddsFormat.parse(value, default=DEFAULT_OUTPUT_FORMAT)


def resolve_input_format(fmt: str | OddsFormat | None = None) -> OddsFormat:
    """Return a concrete input format, preferring explicit args over env defaults."""

    if isinstance(fmt, OddsFormat):
        return fmt
    if fmt is None:
        return get_input_odds_format()
    return OddsFormat.parse(fmt, default=DEFAULT_INPUT_FORMAT)


def resolve_output_format(fmt: str | OddsFormat | None = None) -> OddsFormat:
    """Return a concrete output format, preferring explicit args over env defaults."""

    if isinstance(fmt, OddsFormat):
        return fmt
    if fmt is None:
        return get_output_odds_format()
    return OddsFormat.parse(fmt, default=DEFAULT_OUTPUT_FORMAT)


@overload
def odds_to_decimal(
    odds: ScalarOddsInput,
    *,
    odds_format: str | OddsFormat | None = None,
) -> float:
    ...


@overload
def odds_to_decimal(
    odds: ArrayLike,
    *,
    odds_format: str | OddsFormat | None = None,
) -> np.ndarray:
    ...


def odds_to_decimal(
    odds: ArrayLike,
    *,
    odds_format: str | OddsFormat | None = None,
) -> float | np.ndarray:
    """Convert odds from the given format into decimal odds.

    Accepts scalars or 1-D array-likes. The return value mirrors the input shape:
    scalar inputs yield scalars; iterable inputs yield ``np.ndarray``.
    """

    scalar_input = _is_scalar_input(odds)
    fmt = resolve_input_format(odds_format)

    if fmt is OddsFormat.DECIMAL:
        result = _ensure_1d(odds, dtype=np.float64)
        return cast(float, result.item()) if scalar_input else result

    if fmt is OddsFormat.AMERICAN:
        a = _ensure_1d(odds, dtype=np.float64)
        if np.any(a == 0):
            raise ValueError("American odds cannot be zero")
        invalid = np.abs(a) < 100
        if np.any(invalid):
            bad_values = ", ".join(str(value) for value in a[invalid])
            raise ValueError(
                "American odds must be <= -100 or >= 100; received: " + bad_values
            )

        positive = a > 0
        dec = np.empty_like(a, dtype=np.float64)
        dec[positive] = (a[positive] / 100.0) + 1.0
        dec[~positive] = (100.0 / np.abs(a[~positive])) + 1.0
        return cast(float, dec.item()) if scalar_input else dec

    if fmt is OddsFormat.FRACTIONAL:
        arr = _coerce_fractional_inputs(odds)
        scalar_fractional = scalar_input or (len(arr) == 1)

        def _convert(value: object) -> float:
            if isinstance(value, Fraction):
                frac = value
            elif isinstance(value, str):
                frac = Fraction(value)
            elif isinstance(value, (int, float)):
                frac = Fraction(value).limit_denominator(1000)
            elif isinstance(value, Iterable):
                try:
                    num, den = value
                except ValueError as exc:
                    raise ValueError("Fractional odds iterables must have two elements") from exc
                frac = Fraction(num, den)
            else:
                raise TypeError(
                    "Fractional odds must be provided as str, Fraction, number, or length-2 iterable"
                )
            if frac.numerator <= 0 or frac.denominator <= 0:
                raise ValueError("Fractional odds require positive numerator and denominator")
            return float(frac) + 1.0

        converted = [_convert(item) for item in arr]
        result = np.asarray(converted, dtype=np.float64)
        return cast(float, result.item()) if scalar_fractional else result

    raise AssertionError(f"Unhandled odds format: {fmt}")


@overload
def decimal_to_odds(
    decimal_odds: ScalarOddsInput,
    *,
    target_format: str | OddsFormat | None = None,
) -> float | str:
    ...


@overload
def decimal_to_odds(
    decimal_odds: ArrayLike,
    *,
    target_format: str | OddsFormat | None = None,
) -> np.ndarray:
    ...


def decimal_to_odds(
    decimal_odds: ArrayLike,
    *,
    target_format: str | OddsFormat | None = None,
) -> float | str | np.ndarray:
    """Convert decimal odds into the requested format.

    Returns a scalar when ``decimal_odds`` is scalar; otherwise a 1-D array.
    """

    fmt = resolve_output_format(target_format)
    scalar_input = _is_scalar_input(decimal_odds)
    dec = _ensure_1d(decimal_odds, dtype=np.float64)
    if np.any(dec < 1.0):
        raise ValueError("Decimal odds must be >= 1.0")

    if fmt is OddsFormat.DECIMAL:
        return cast(float, dec.item()) if scalar_input else dec

    if fmt is OddsFormat.AMERICAN:

        def _convert(value: float) -> float:
            frac = Fraction(value).limit_denominator(1000)
            if frac >= 2:
                return float((frac - 1) * 100)
            ratio = frac - 1
            if ratio == 0:
                raise ValueError("Decimal odds of 1.0 cannot be represented as American odds")
            return float(-100 / ratio)

        vectorized = np.vectorize(_convert, otypes=[np.float64])
        american = vectorized(dec)
        return cast(float, american.item()) if scalar_input else american

    if fmt is OddsFormat.FRACTIONAL:
        arr = dec - 1.0

        def _convert(value: float) -> str:
            frac = Fraction(value).limit_denominator(1000)
            if frac.numerator <= 0 or frac.denominator <= 0:
                raise ValueError("Fractional odds require positive ratio")
            return f"{frac.numerator}/{frac.denominator}"

        vectorized = np.vectorize(_convert, otypes=[object])
        fractional = vectorized(arr)
        return cast(str, fractional.item()) if scalar_input else fractional

    raise AssertionError(f"Unhandled odds format: {fmt}")


@overload
def convert_odds(
    odds: ScalarOddsInput,
    *,
    from_format: str | OddsFormat | None = None,
    to_format: str | OddsFormat | None = None,
) -> float | str:
    ...


@overload
def convert_odds(
    odds: ArrayLike,
    *,
    from_format: str | OddsFormat | None = None,
    to_format: str | OddsFormat | None = None,
) -> np.ndarray:
    ...


def convert_odds(
    odds: ArrayLike,
    *,
    from_format: str | OddsFormat | None = None,
    to_format: str | OddsFormat | None = None,
) -> float | str | np.ndarray:
    """Convert odds from ``from_format`` into ``to_format`` via decimal odds.

    Mirrors the shape of the input odds.
    """

    intermediate = odds_to_decimal(odds, odds_format=from_format)
    return decimal_to_odds(intermediate, target_format=to_format)


__all__ = [
    "DEFAULT_INPUT_FORMAT",
    "DEFAULT_OUTPUT_FORMAT",
    "OddsFormat",
    "convert_odds",
    "decimal_to_odds",
    "get_input_odds_format",
    "get_output_odds_format",
    "odds_to_decimal",
    "resolve_input_format",
    "resolve_output_format",
]

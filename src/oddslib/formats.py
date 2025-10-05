"""Odds format definitions and helpers."""
from __future__ import annotations

import os
from enum import Enum


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

        Parsing is case-insensitive. ``default`` must be provided when ``value`` is ``None``.
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


def get_input_odds_format() -> OddsFormat:
    """Return the input odds format, falling back to the package default."""

    value = os.getenv(_INPUT_ENV)
    return OddsFormat.parse(value, default=DEFAULT_INPUT_FORMAT)


def get_output_odds_format() -> OddsFormat:
    """Return the output odds format, falling back to the package default."""

    value = os.getenv(_OUTPUT_ENV)
    return OddsFormat.parse(value, default=DEFAULT_OUTPUT_FORMAT)


__all__ = [
    "DEFAULT_INPUT_FORMAT",
    "DEFAULT_OUTPUT_FORMAT",
    "OddsFormat",
    "get_input_odds_format",
    "get_output_odds_format",
]

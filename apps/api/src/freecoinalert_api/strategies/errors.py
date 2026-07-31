"""Focused exceptions for impossible strategy-calculation invariants."""


class StrategyCalculationError(Exception):
    """Raised when an internally calculated value violates a strategy invariant."""

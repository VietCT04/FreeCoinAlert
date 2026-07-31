"""Local Decimal arithmetic rules for versioned strategy calculations."""

from decimal import Decimal, ROUND_HALF_EVEN, localcontext


PRICE_QUANTUM = Decimal("0.000000000000000001")
RSI_QUANTUM = Decimal("0.00000001")
CALCULATION_PRECISION = 50


def quantize_price(value: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = CALCULATION_PRECISION
        context.rounding = ROUND_HALF_EVEN
        return value.quantize(PRICE_QUANTUM)


def quantize_rsi(value: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = CALCULATION_PRECISION
        context.rounding = ROUND_HALF_EVEN
        return value.quantize(RSI_QUANTUM)


def calculate_price_average(total: Decimal, count: int) -> Decimal:
    with localcontext() as context:
        context.prec = CALCULATION_PRECISION
        context.rounding = ROUND_HALF_EVEN
        return quantize_price(total / Decimal(count))


def calculate_wilder_average(
    previous_average: Decimal,
    change: Decimal,
    period: int,
) -> Decimal:
    with localcontext() as context:
        context.prec = CALCULATION_PRECISION
        context.rounding = ROUND_HALF_EVEN
        numerator = (previous_average * Decimal(period - 1)) + change
        return quantize_price(numerator / Decimal(period))

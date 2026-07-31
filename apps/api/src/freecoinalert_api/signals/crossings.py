from decimal import Decimal
from typing import Literal


Relation = Literal["below", "equal", "above"]


def relation(left_value: Decimal, right_value: Decimal) -> Relation:
    if left_value < right_value:
        return "below"
    if left_value > right_value:
        return "above"
    return "equal"


def crosses(
    *,
    direction: str,
    previous_left_value: Decimal,
    previous_right_value: Decimal,
    current_left_value: Decimal,
    current_right_value: Decimal,
) -> bool:
    if direction == "cross_above":
        return (
            previous_left_value <= previous_right_value
            and current_left_value > current_right_value
        )
    if direction == "cross_below":
        return (
            previous_left_value >= previous_right_value
            and current_left_value < current_right_value
        )
    raise ValueError("Unsupported preset direction.")

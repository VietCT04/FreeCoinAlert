from decimal import Decimal
from typing import Literal

Relation = Literal["below", "equal", "above"]


def relation_for(*, price: Decimal, target: Decimal) -> Relation:
    if price < target:
        return "below"
    if price > target:
        return "above"
    return "equal"


def crosses_in_direction(*, direction: str, previous: Relation, current: Relation) -> bool:
    if direction == "cross_above":
        return previous in {"below", "equal"} and current == "above"
    if direction == "cross_below":
        return previous in {"above", "equal"} and current == "below"
    raise ValueError("Unsupported alert direction.")

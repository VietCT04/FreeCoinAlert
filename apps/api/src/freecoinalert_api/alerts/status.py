from typing import Literal

AlertStatus = Literal["active", "triggered", "disabled", "failed"]
DeliveryStatus = Literal[
    "not_queued",
    "queued",
    "sending",
    "retrying",
    "sent",
    "failed",
    "outcome_unknown",
]

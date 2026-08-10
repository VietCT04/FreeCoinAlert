"""Expand immutable Historical Analysis dataset bounds for 730-day runs."""

from collections.abc import Sequence

from alembic import op


revision: str = "20260810_0023"
down_revision: str | Sequence[str] | None = "20260810_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _dataset_count_constraint() -> str:
    return (
        "required_warmup_candles >= 0 "
        "AND warmup_candle_count >= 0 "
        "AND analysis_candle_count >= 0 "
        "AND total_candle_count >= 0 "
        "AND required_warmup_candles <= 200 "
        "AND ((timeframe = '1h' AND total_candle_count <= "
        "17520 + required_warmup_candles) "
        "OR (timeframe = '4h' AND total_candle_count <= "
        "4380 + required_warmup_candles))"
    )


def upgrade() -> None:
    op.drop_constraint(
        "ck_historical_analysis_datasets_counts_nonnegative",
        "historical_analysis_datasets",
        type_="check",
    )
    op.create_check_constraint(
        "ck_historical_analysis_datasets_counts_nonnegative",
        "historical_analysis_datasets",
        _dataset_count_constraint(),
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_historical_analysis_datasets_counts_nonnegative",
        "historical_analysis_datasets",
        type_="check",
    )
    op.create_check_constraint(
        "ck_historical_analysis_datasets_counts_nonnegative",
        "historical_analysis_datasets",
        "required_warmup_candles >= 0 "
        "AND warmup_candle_count >= 0 "
        "AND analysis_candle_count >= 0 "
        "AND total_candle_count >= 0 "
        "AND total_candle_count <= 2500",
    )

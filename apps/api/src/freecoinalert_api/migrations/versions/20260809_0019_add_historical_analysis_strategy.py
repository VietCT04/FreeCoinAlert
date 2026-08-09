"""Persist immutable historical-analysis strategy snapshots."""

from collections.abc import Sequence
import hashlib
import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260809_0019"
down_revision: str | Sequence[str] | None = "20260803_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "historical_analysis_runs",
        sa.Column("strategy_version", sa.String(64), nullable=True),
    )
    op.add_column(
        "historical_analysis_runs",
        sa.Column("strategy_snapshot", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "historical_analysis_runs",
        sa.Column("strategy_fingerprint", sa.String(64), nullable=True),
    )

    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, preset_code_snapshot, preset_version_snapshot, "
            "timeframe_snapshot, direction_snapshot, calculation_version_snapshot "
            "FROM historical_analysis_runs"
        )
    )
    for row in rows:
        snapshot = _legacy_snapshot(
            preset_code=row.preset_code_snapshot,
            preset_version=row.preset_version_snapshot,
            timeframe=row.timeframe_snapshot,
            signal_direction=row.direction_snapshot,
            calculation_version=row.calculation_version_snapshot,
        )
        canonical = json.dumps(
            snapshot,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        connection.execute(
            sa.text(
                "UPDATE historical_analysis_runs "
                "SET strategy_version = :strategy_version, "
                "strategy_snapshot = CAST(:strategy_snapshot AS jsonb), "
                "strategy_fingerprint = :strategy_fingerprint "
                "WHERE id = :id"
            ),
            {
                "id": row.id,
                "strategy_version": "legacy_fixed_horizon_v1",
                "strategy_snapshot": canonical,
                "strategy_fingerprint": fingerprint,
            },
        )

    op.alter_column(
        "historical_analysis_runs",
        "strategy_version",
        existing_type=sa.String(64),
        nullable=False,
    )
    op.alter_column(
        "historical_analysis_runs",
        "strategy_snapshot",
        existing_type=postgresql.JSONB(),
        nullable=False,
    )
    op.alter_column(
        "historical_analysis_runs",
        "strategy_fingerprint",
        existing_type=sa.String(64),
        nullable=False,
    )
    op.create_check_constraint(
        "ck_historical_analysis_runs_strategy_fingerprint",
        "historical_analysis_runs",
        "strategy_fingerprint ~ '^[0-9a-f]{64}$'",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_historical_analysis_runs_strategy_fingerprint",
        "historical_analysis_runs",
        type_="check",
    )
    op.drop_column("historical_analysis_runs", "strategy_fingerprint")
    op.drop_column("historical_analysis_runs", "strategy_snapshot")
    op.drop_column("historical_analysis_runs", "strategy_version")


def _legacy_snapshot(
    *,
    preset_code: str,
    preset_version: int,
    timeframe: str,
    signal_direction: str,
    calculation_version: str,
) -> dict[str, object]:
    position_direction = (
        "long" if signal_direction == "cross_above" else "synthetic_short"
    )
    return {
        "schema_version": "historical_strategy_snapshot_v1",
        "version": "legacy_fixed_horizon_v1",
        "entry": {
            "preset_code": preset_code,
            "preset_version": preset_version,
            "timeframe": timeframe,
            "signal_direction": signal_direction,
            "calculation_version": calculation_version,
        },
        "position_direction": position_direction,
        "exit_rules": [
            {"type": "max_holding_candles", "candles": 6},
        ],
    }

"""File-backed, E2E-only gates shared by the worker and control containers."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from threading import Lock

from freecoinalert_api.core.config import Settings
from freecoinalert_api.e2e import require_e2e_mode


DEFAULT_GATE_PATH = "/app/.e2e/worker-gates.json"
_WRITE_LOCK = Lock()


def _gate_path() -> Path:
    return Path(os.environ.get("E2E_WORKER_GATE_PATH", DEFAULT_GATE_PATH))


def _read_state() -> dict[str, object]:
    try:
        value = json.loads(_gate_path().read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {"gates": {}}
    return value if isinstance(value, dict) else {"gates": {}}


def _write_state(state: dict[str, object]) -> None:
    path = _gate_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(".tmp")
    temporary_path.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")
    temporary_path.replace(path)


def set_gates(settings: Settings, names: list[str]) -> None:
    require_e2e_mode(settings)
    with _WRITE_LOCK:
        state = _read_state()
        gates = state.get("gates")
        current = dict(gates) if isinstance(gates, dict) else {}
        current.update({name: False for name in names})
        _write_state({"gates": current})


def release_gates(settings: Settings, names: list[str]) -> None:
    require_e2e_mode(settings)
    with _WRITE_LOCK:
        state = _read_state()
        gates = state.get("gates")
        current = dict(gates) if isinstance(gates, dict) else {}
        current.update({name: True for name in names})
        _write_state({"gates": current})


def clear_gates(settings: Settings) -> None:
    require_e2e_mode(settings)
    with _WRITE_LOCK:
        _write_state({"gates": {}})


async def wait_for_historical_worker_gate(
    settings: Settings,
    *,
    gate_name: str,
    stop_event: asyncio.Event,
) -> None:
    if not settings.e2e_worker_gate_enabled:
        return
    require_e2e_mode(settings)
    while not stop_event.is_set():
        state = _read_state()
        gates = state.get("gates")
        if not isinstance(gates, dict) or gates.get(gate_name) is not False:
            return
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=0.25)
        except TimeoutError:
            continue

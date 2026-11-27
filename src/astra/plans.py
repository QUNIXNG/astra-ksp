"""Plan fingerprints: tie a burn back to the computation that proposed it.

A ``compute_*`` result is only a proposal. The numbers get copied into ``node_create`` or ``fly_burn``, and
nothing in that hand-off proves the burn still matches what was computed: a mistyped digit, a rounded value,
or a node edited ten minutes later all look identical afterwards.

A plan id closes that gap. ``compute_*`` records the burn it proposed and returns an 8-character id; the burn
tool takes the id back and compares it against the node it is about to execute. A drift is reported before
the engines light, and every call in ``log.jsonl`` carries the id, so a finished mission reads as a chain of
plans instead of a list of loose numbers.

The cache is advisory: if it cannot be written, ``remember`` still returns a usable id and the only thing
lost is the later comparison.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

from astra.config import CONFIG

_KEEP = 200  # enough for a long mission, small enough to stay readable
_LOCK = threading.Lock()


def _file() -> Path:
    return CONFIG.cache_dir / "plans.json"


def _load() -> dict[str, Any]:
    try:
        data = json.loads(_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _save(data: dict[str, Any]) -> None:
    try:
        path = _file()
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".plans-", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False)
        os.replace(tmp, path)
    except OSError:
        pass  # a missing cache costs traceability, never a burn


def make_id(kind: str, ut: float, prograde: float, normal: float, radial: float) -> str:
    """The id a given burn shape always gets: the same plan recomputed is the same plan."""
    key = f"{kind}|{ut:.3f}|{prograde:.4f}|{normal:.4f}|{radial:.4f}"
    return hashlib.sha256(key.encode()).hexdigest()[:8]


def remember(kind: str, ut: float, prograde: float, normal: float, radial: float, **extra: Any) -> str:
    """Record what a compute_* tool proposed and return its short id."""
    pid = make_id(kind, ut, prograde, normal, radial)
    record = {"id": pid, "kind": kind, "ut": round(ut, 3), "prograde_mps": round(prograde, 4),
              "normal_mps": round(normal, 4), "radial_mps": round(radial, 4), **extra}
    with _LOCK:
        data = _load()
        data[pid] = record
        if len(data) > _KEEP:
            for stale in sorted(data, key=lambda k: data[k].get("ut") or 0)[: len(data) - _KEEP]:
                data.pop(stale, None)
        _save(data)
    return pid


def get(pid: str) -> dict[str, Any] | None:
    record = _load().get(pid)
    return record if isinstance(record, dict) else None


def mismatch(pid: str, *, ut: float, prograde: float, normal: float, radial: float,
             tol_dv: float = 0.05, tol_ut: float = 1.0) -> str | None:
    """``None`` when the burn still matches the plan, else a sentence naming what drifted."""
    plan = get(pid)
    if plan is None:
        return f"plan {pid} is not in the local cache (cache cleared, or recorded on another machine)"
    diffs = [
        f"{label} {now:+.3f} vs planned {plan[key]:+.3f}"
        for label, now, key in (("ut", ut, "ut"), ("prograde", prograde, "prograde_mps"),
                                ("normal", normal, "normal_mps"), ("radial", radial, "radial_mps"))
        if abs(now - plan[key]) > (tol_ut if key == "ut" else tol_dv)
    ]
    if not diffs:
        return None
    return f"plan {pid} ({plan.get('kind', '?')}) does not match this burn: " + ", ".join(diffs)


def describe(pid: str) -> dict[str, Any] | None:
    """The stored plan, for echoing next to a burn that used it."""
    plan = get(pid)
    if plan is None:
        return None
    return {k: plan.get(k) for k in ("id", "kind", "ut", "prograde_mps", "normal_mps", "radial_mps", "dv_mps") if k in plan}

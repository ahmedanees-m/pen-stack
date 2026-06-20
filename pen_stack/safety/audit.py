"""Append-only, hash-chained safety audit log, the Guardian (v5.7, WS-POLICY).

Every safety decision is recorded as a JSON line whose hash chains to the previous record, so the log is
tamper-evident: altering any past record breaks the chain from that point forward (`verify_chain`). The log
stores a design DIGEST (sha256), not the design itself, it is an accountability trail, not a hazard store.

Path resolution: `PEN_STACK_SAFETY_AUDIT` env var, else `<project_root>/out/safety_audit.log`.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pen_stack._resources import project_root

_GENESIS = "0" * 64


def audit_path() -> Path:
    env = os.environ.get("PEN_STACK_SAFETY_AUDIT")
    if env:
        return Path(env).expanduser()
    return project_root() / "out" / "safety_audit.log"


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _last_hash(path: Path) -> str:
    if not path.exists():
        return _GENESIS
    last = _GENESIS
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                last = json.loads(line)["this_hash"]
            except (json.JSONDecodeError, KeyError):
                continue
    return last


def audit_log(*, actor: str, design_digest: str, verdict, path: Path | None = None) -> dict:
    """Append one hash-chained record for a SafetyVerdict. Returns the written record."""
    p = path or audit_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    prev = _last_hash(p)
    body = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "design_digest": design_digest,
        "decision": verdict.decision,
        "reason": verdict.reason,
        "n_hits": len(verdict.hits),
        "hit_ids": [h.provenance.get("signature_id") for h in verdict.hits],
        "registry_version": next((h.provenance.get("registry_version") for h in verdict.hits), None),
        "prev_hash": prev,
    }
    record = {**body, "this_hash": _digest({**body})}
    with p.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def verify_chain(path: Path | None = None) -> dict:
    """Verify the hash chain is intact (tamper-evident). Returns {ok, n, broken_at}."""
    p = path or audit_path()
    if not p.exists():
        return {"ok": True, "n": 0, "broken_at": None, "reason": "no log yet"}
    prev = _GENESIS
    n = 0
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        rec = json.loads(line)
        body = {k: rec[k] for k in rec if k != "this_hash"}
        if rec.get("prev_hash") != prev or _digest(body) != rec.get("this_hash"):
            return {"ok": False, "n": n, "broken_at": i, "reason": "hash chain broken"}
        prev = rec["this_hash"]
        n += 1
    return {"ok": True, "n": n, "broken_at": None}


def digest_design(design: dict) -> str:
    """Stable digest of a design for the audit trail (does not store the design itself)."""
    return _digest(design)

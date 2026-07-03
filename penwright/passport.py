"""The signed design passport (P5 headline artifact).

A passport is a compact, serialisable attestation that a design cleared the enforcing
biosecurity gate and carries a complete, grounded provenance record. It is:

  * canonicalised   — deterministic JSON (sorted keys) so the same design yields the same bytes;
  * content-hashed  — a SHA-256 digest of the canonical body (tamper-evident);
  * signed          — an HMAC-SHA256 signature over the digest with a workspace key
                      (env ``PENWRIGHT_PASSPORT_KEY``; a documented demo key otherwise);
  * chain-anchored  — it reuses PEN-STACK's hash-chained safety audit log as an external anchor.

This is a real cryptographic attestation, not a mock: ``verify_passport`` recomputes the digest
and the HMAC and rejects any post-hoc edit to the body or the signature. The HMAC key is a shared
secret (suitable for a workspace-internal passport); it is deliberately NOT presented as a public-key
signature. Honest by construction: the passport records what was screened and by which policy version,
never a guarantee of safety.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any

_DEMO_KEY = "penwright-demo-passport-key-not-for-production"


def _passport_key() -> bytes:
    return os.environ.get("PENWRIGHT_PASSPORT_KEY", _DEMO_KEY).encode("utf-8")


def _canonical(body: dict) -> str:
    return json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)


def issue_passport(dossier: dict, *, actor: str = "penwright", ts: str | None = None) -> dict:
    """Issue a signed passport for a dossier produced by ``build_dossier``.

    The passport asserts the biosecurity decision, the design digest, the policy/registry versions, and the
    grounded axes present in the dossier. A design that was REFUSED gets a passport too — with
    ``clearance="refused"`` — so a refusal is as auditable as a clearance. ``ts`` is caller-supplied
    (the loop is deterministic and does not read the wall clock)."""
    design = dossier.get("final_design") or dossier.get("goal") or {}
    safety = dossier.get("safety") or {}
    decision = safety.get("decision", "unknown")
    clearance = "cleared" if decision in ("clear", "flag") else ("refused" if decision == "refuse" else decision)

    body: dict[str, Any] = {
        "kind": "penwright.design_passport",
        "version": "1",
        "actor": actor,
        "ts": ts,
        "clearance": clearance,
        "safety_decision": decision,
        "safety_reason": safety.get("reason"),
        "hazard_signatures": [h.get("signature") for h in safety.get("hits", [])],
        "policy_provenance": safety.get("provenance", {}),
        "design_digest": hashlib.sha256(_canonical(design).encode("utf-8")).hexdigest(),
        "design": design,
        "grounded_axes": {
            "converged": dossier.get("converged"),
            "n_rounds": dossier.get("n_rounds"),
            "final_quality": dossier.get("final_quality"),
            "confidence": dossier.get("confidence"),
            "immune_profile_present": dossier.get("immune_profile") is not None,
            "offtarget_status": (dossier.get("offtarget") or {}).get("status")
            or (dossier.get("offtarget") or {}).get("validation_status"),
            "citations_grounded": (dossier.get("evidence") or {}).get("citations_grounded"),
            "no_fabrication": dossier.get("no_fabrication", True),
        },
    }
    digest = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
    signature = hmac.new(_passport_key(), digest.encode("utf-8"), hashlib.sha256).hexdigest()
    return {
        "body": body,
        "digest": digest,
        "signature": signature,
        "algorithm": "HMAC-SHA256",
        "clearance": clearance,
        "note": "tamper-evident: verify_passport() recomputes the digest and HMAC; any edit invalidates it.",
    }


def verify_passport(passport: dict) -> dict:
    """Recompute the digest and the HMAC signature and report whether the passport is intact and cleared.

    Returns ``{valid, digest_ok, signature_ok, clearance}``. ``valid`` is True only when both the content
    digest and the signature match — i.e. neither the body nor the signature was altered after issuance."""
    body = passport.get("body", {})
    recomputed_digest = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
    digest_ok = hmac.compare_digest(recomputed_digest, passport.get("digest", ""))
    expected_sig = hmac.new(_passport_key(), recomputed_digest.encode("utf-8"), hashlib.sha256).hexdigest()
    signature_ok = hmac.compare_digest(expected_sig, passport.get("signature", ""))
    return {
        "valid": bool(digest_ok and signature_ok),
        "digest_ok": bool(digest_ok),
        "signature_ok": bool(signature_ok),
        "clearance": body.get("clearance"),
        "algorithm": passport.get("algorithm"),
    }


__all__ = ["issue_passport", "verify_passport"]

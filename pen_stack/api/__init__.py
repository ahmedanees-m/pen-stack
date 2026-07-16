"""pen_stack.api, the self-describing AI integration surface (v6.1).

A machine-readable capability manifest (what PEN-STACK can do) and, the differentiator, a machine-readable
scope manifest (what it refuses to answer: the known-unknowns + the oracle scope cards). An external agent can
ask "what can you do, and what do you refuse to answer?" and get a typed, valid answer it can route on. The
grounding machinery becomes an API, versioned under the 1.0 stability commitment.
"""
from __future__ import annotations

from pen_stack.api.manifest import capability_manifest, scope_manifest

__all__ = ["capability_manifest", "scope_manifest"]

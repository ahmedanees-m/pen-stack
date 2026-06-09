"""Verification service (v3.3, WS-V): verify(design) -> Verdict over the rule engine + L4 trust layer."""
from pen_stack.verify.schema import Verdict
from pen_stack.verify.service import verify

__all__ = ["verify", "Verdict"]

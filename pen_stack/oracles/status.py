"""Live-oracle status + latency surface (PEN-STACK v6.4).

Reports, for every foundation-model oracle, HOW it executes, its per-query LATENCY CLASS, and whether it is
currently LIVE (or why not), so the assistant can tell the user the cost up front ("this runs on the GPU,
~1 min" / "this is a long cloud job, run it separately") and never silently blocks. The static map lives in
`configs/oracles/execution.yaml`; this module adds the runtime liveness check (key present? server up?).
"""
from __future__ import annotations

import os
from functools import lru_cache

from pen_stack._resources import resource


@lru_cache(maxsize=1)
def execution_map() -> dict:
    import yaml
    return yaml.safe_load(resource("configs/oracles/execution.yaml").read_text(encoding="utf-8"))["oracles"]


def _net_on() -> bool:
    return os.getenv("PEN_STACK_ORACLE_NET") == "1"


def _alphagenome_key() -> bool:
    if os.getenv("ALPHAGENOME_API_KEY"):
        return True
    try:
        return resource("configs/alphagenome_api_key.txt").exists()
    except Exception: # noqa: BLE001
        return False


def _nvidia_key() -> bool:
    if os.getenv("NVIDIA_API_KEY"):
        return True
    try:
        return resource("configs/nvidia_api_key.txt").exists()
    except Exception: # noqa: BLE001
        return False


_SERVER_ENV = {"proteinmpnn": ("PEN_STACK_PROTEINMPNN_URL", "http://localhost:9011"),
               "esm3": ("PEN_STACK_ESM3_URL", "http://localhost:9012"),
               "rfdiffusion": ("PEN_STACK_RFDIFFUSION_URL", "http://localhost:9013")}


def _server_up(model: str) -> bool:
    env, default = _SERVER_ENV[model]
    url = os.getenv(env, default).rstrip("/")
    try:
        import requests
        return requests.get(f"{url}/health", timeout=2).status_code == 200
    except Exception: # noqa: BLE001
        return False


def _is_live(model: str, card: dict, probe: bool) -> tuple[bool, str]:
    ex = card.get("execution")
    if ex == "in_process":
        return True, "runs in-process"
    if card.get("live") is False or ex in {"deferred", "cloud_a100"}:
        return False, card.get("note", "not active")
    if ex == "hosted_api":
        if not _net_on():
            return False, "set PEN_STACK_ORACLE_NET=1 to enable live calls"
        if model == "alphagenome":
            if not _alphagenome_key():
                return False, "add configs/alphagenome_api_key.txt"
            try:
                from pen_stack.wgenome.providers import package_available
                if not package_available():
                    return False, "pip install alphagenome"
            except Exception: # noqa: BLE001
                return False, "alphagenome package unavailable"
        if model == "evo2" and not _nvidia_key():
            return False, "add configs/nvidia_api_key.txt"
        return True, "hosted API ready"
    if ex == "local_gpu":
        if not _net_on():
            return False, "set PEN_STACK_ORACLE_NET=1"
        if probe:
            return (_server_up(model), "server up" if _server_up(model) else "model server not running (start it on demand)")
        return True, "enabled (start the model server on demand)"
    return False, "unknown execution"


def oracle_status(probe: bool = False) -> dict:
    """Per-oracle execution + latency_class + live status + published reliability. `probe=True` pings the local
    model servers (adds a short network check); default is config-level only. Reliability is the wrapped model's
    PUBLISHED benchmark accuracy, reported verbatim with citation, never a claim about this stack's accuracy."""
    try:
        from pen_stack.oracles.reliability import all_reliability
        rel = all_reliability()
    except Exception: # noqa: BLE001
        rel = {}
    out = {}
    for model, card in execution_map().items():
        live, why = _is_live(model, card, probe)
        out[model] = {"execution": card.get("execution"), "latency_class": card.get("latency_class"),
                      "live": live, "status": why, "note": card.get("note", ""),
                      "server": card.get("server"), "reliability": rel.get(model)}
    return out


def summary() -> dict:
    """Compact roll-up for the capability manifest + the chat meta facts."""
    st = oracle_status(probe=False)
    live = sorted(m for m, s in st.items() if s["live"])
    held = sorted(m for m, s in st.items() if s["execution"] == "cloud_a100")
    deferred = sorted(m for m, s in st.items() if s["execution"] == "deferred")
    out = {"live": live, "held_cloud": held, "deferred": deferred,
           "latency_classes": {m: s["latency_class"] for m, s in st.items()},
           "note": ("Live oracles answer in seconds, ~2 min; held cloud jobs (AF3/Boltz/Chai/Protenix) are run "
                    "separately and never block; deferred outcomes are known-unknowns, never fabricated.")}
    try:
        from pen_stack.oracles.reliability import disagreement_widens_monotonically, disclaimer
        out["reliability_note"] = disclaimer()
        out["disagreement_to_interval"] = disagreement_widens_monotonically()
    except Exception: # noqa: BLE001
        pass
    return out

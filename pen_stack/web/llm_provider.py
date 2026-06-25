"""Swappable LLM provider abstraction (PEN-CHAT P-WS2).

ONE interface over the local Ollama and cloud Nemotron backends (and any future provider). The LLM is
NON-LOAD-BEARING: the grounding guard, the engine tool results, and the retrieved sources carry truth, so the
system's GROUNDED outputs - the lane, the provenance, the cited sources, and every number - are INVARIANT to which
provider answers; only the prose phrasing changes. Centralising provider selection here makes that invariance
testable and the default documented.

Selection:
  * PEN_STACK_LLM_PROVIDER pins a single provider (used by the invariance test);
  * else PEN_STACK_LLM_ORDER (default "ollama,nemotron") is tried in order;
  * PEN_STACK_NO_LLM=1 disables the LLM entirely (the deterministic narrators take over).
The default provider is **ollama** (local, reproducible, no key); Nemotron is the cloud fallback.
"""
from __future__ import annotations

import os
from pathlib import Path

DEFAULT_ORDER = "ollama,nemotron"


def _ollama_base() -> str:
    return os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")


# v7.1.2 latency fix: the General / Social lane never needs the long-form 450-token answer the engine-grounded lanes
# may need, and it does not benefit from a 150 s hang waiting on a stalled provider. The kind="general" path uses a
# shorter timeout AND a shorter num_predict; the default path (engine-grounded design / explain / meta) is unchanged.
def _llm_timeout(kind: str = "default") -> float:
    if kind == "general":
        return float(os.getenv("PEN_STACK_LLM_TIMEOUT_GENERAL", "45"))
    return float(os.getenv("PEN_STACK_LLM_TIMEOUT", "90"))


def _ollama_num_predict(kind: str = "default") -> int:
    if kind == "general":
        return int(os.getenv("OLLAMA_NUM_PREDICT_GENERAL", "280"))
    return int(os.getenv("OLLAMA_NUM_PREDICT", "450"))


def _nemotron_max_tokens(kind: str = "default") -> int:
    if kind == "general":
        return int(os.getenv("NEMOTRON_MAX_TOKENS_GENERAL", "400"))
    return int(os.getenv("NEMOTRON_MAX_TOKENS", "700"))


def _call_ollama(prompt: str, system: str, kind: str = "default") -> str:
    import requests
    r = requests.post(
        f"{_ollama_base()}/api/generate",
        json={"model": os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct"), "prompt": prompt, "system": system,
              "stream": False, "keep_alive": os.getenv("OLLAMA_KEEP_ALIVE", "30m"),
              "options": {"temperature": 0.2, "num_predict": _ollama_num_predict(kind)}},
        timeout=_llm_timeout(kind))
    r.raise_for_status()
    return r.json()["response"]


def _nvidia_key() -> str | None:
    key = os.getenv("NVIDIA_API_KEY")
    if key:
        return key.strip()
    f = Path(__file__).resolve().parents[2] / "configs" / "nvidia_api_key.txt"
    return f.read_text(encoding="utf-8").strip() if f.exists() else None


def _call_nemotron(prompt: str, system: str, kind: str = "default") -> str:
    import requests
    key = _nvidia_key()
    if not key:
        raise RuntimeError("no NVIDIA_API_KEY")
    r = requests.post(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": os.getenv("NEMOTRON_MODEL", "nvidia/llama-3.3-nemotron-super-49b-v1"),
              "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
              "temperature": 0.2, "max_tokens": _nemotron_max_tokens(kind)}, timeout=_llm_timeout(kind))
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


_BACKENDS = {"ollama": _call_ollama, "nemotron": _call_nemotron}


def providers() -> list[str]:
    """The registered providers (names accepted by `run_llm(provider=...)`)."""
    return list(_BACKENDS.keys())


def _order() -> list[str]:
    pinned = os.getenv("PEN_STACK_LLM_PROVIDER")
    if pinned:
        return [pinned.strip().lower()]
    return [b.strip().lower() for b in os.getenv("PEN_STACK_LLM_ORDER", DEFAULT_ORDER).split(",")]


def default_provider() -> str:
    return _order()[0]


def run_llm(prompt: str, system: str, provider: str | None = None,
            kind: str = "default") -> tuple[str | None, str | None]:
    """Return (text, backend_name) or (None, None). If `provider` is given, use ONLY it (invariance testing);
    otherwise try the configured order. `kind="general"` selects the fast-path timeout / token cap (Social / General
    lane); `kind="default"` (the engine-grounded lanes) keeps the longer budget. The downstream guard makes the
    GROUNDED result invariant to which provider fired."""
    if os.getenv("PEN_STACK_NO_LLM") == "1":
        return None, None
    order = [provider.strip().lower()] if provider else _order()
    for name in order:
        fn = _BACKENDS.get(name)
        if fn is None:
            continue
        try:
            return fn(prompt, system, kind=kind), name
        except Exception:  # noqa: BLE001 - a dead provider falls through to the next, else the deterministic path
            continue
    return None, None

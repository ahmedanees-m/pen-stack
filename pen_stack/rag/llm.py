"""Provider-agnostic LLM layer for PEN-STACK services (RAG, agent, PEN-MONITOR).

Hybrid backend: a strong hosted model for reasoning/agent/Q&A (default NVIDIA Nemotron, OpenAI-compatible)
with automatic fallback to a local, free, private model (Ollama). The single switch is `configs/llm.yaml`.

This is strictly an orchestration/phrasing layer. Every quantitative claim and every citation still comes
from the deterministic validated-tool path; the LLM never introduces a number, gene, or citation. The
choice of model therefore does not affect scientific reproducibility - only the quality of orchestration
and prose. If no provider is reachable, the callers fall back to the deterministic answer (LLM optional).

Secrets: the API key is read from the env var named in `api_key_env`, then from the gitignored
`api_key_file`. Keys are NEVER committed.
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

import yaml

_CFG = Path(__file__).resolve().parents[2] / "configs" / "llm.yaml"
_ROOT = Path(__file__).resolve().parents[2]

_SYSTEM = ("You rephrase already-verified genome-writing facts into one clear paragraph for a wet-lab "
           "scientist. Use ONLY the facts provided. Do NOT invent or alter any number, gene, or citation. "
           "Do not give clinical advice. Keep it under 90 words.")


def load_llm_config(path: str | Path = _CFG) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _provider_cfg(cfg: dict, name: str) -> dict | None:
    return (cfg.get("providers") or {}).get(name)


def _resolve_key(pcfg: dict) -> str | None:
    env = pcfg.get("api_key_env")
    if env and os.environ.get(env):
        return os.environ[env].strip()
    f = pcfg.get("api_key_file")
    if f:
        p = Path(f)
        if not p.is_absolute():
            p = _ROOT / f
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
    return pcfg.get("api_key")


def _norm_tool_calls(raw: list | None) -> list:
    out = []
    for c in raw or []:
        fn = c.get("function", {})
        args = fn.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args or "{}")
            except json.JSONDecodeError:
                args = {}
        out.append({"function": {"name": fn.get("name"), "arguments": args}})
    return out


def _chat_openai(pcfg: dict, messages: list, tools: list | None, temperature: float,
                 timeout: int) -> dict | None:
    """OpenAI-compatible /v1/chat/completions (NVIDIA NIM, OpenAI, vLLM, Ollama /v1)."""
    base = pcfg["api_base"].rstrip("/")
    key = _resolve_key(pcfg)
    payload = {"model": pcfg["model"], "messages": messages, "temperature": temperature,
               "max_tokens": int(pcfg.get("max_tokens", 1024))}
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(f"{base}/chat/completions", data=json.dumps(payload).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    msg = d["choices"][0]["message"]
    return {"content": (msg.get("content") or "").strip(), "tool_calls": _norm_tool_calls(msg.get("tool_calls")),
            "raw": msg, "style": "openai"}


def _chat_ollama(pcfg: dict, messages: list, tools: list | None, temperature: float,
                 timeout: int) -> dict | None:
    """Ollama native /api/chat."""
    base = pcfg["api_base"].rstrip("/")
    payload = {"model": str(pcfg["model"]).split("/")[-1], "messages": messages, "stream": False,
               "options": {"temperature": temperature}}
    if tools:
        payload["tools"] = tools
    req = urllib.request.Request(f"{base}/api/chat", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    msg = d.get("message", {})
    return {"content": (msg.get("content") or "").strip(), "tool_calls": _norm_tool_calls(msg.get("tool_calls")),
            "raw": msg, "style": "ollama"}


def _call_provider(name: str, cfg: dict, messages: list, tools: list | None, timeout: int) -> dict | None:
    pcfg = _provider_cfg(cfg, name)
    if not pcfg:
        return None
    temp = float(cfg.get("temperature", 0.1))
    style = pcfg.get("style", "openai")
    try:
        if style == "ollama":
            return _chat_ollama(pcfg, messages, tools, temp, timeout)
        return _chat_openai(pcfg, messages, tools, temp, timeout)
    except Exception:  # noqa: BLE001 - any provider failure -> let the caller try the fallback
        return None


def chat(messages: list, tools: list | None = None, cfg: dict | None = None,
         timeout: int = 120) -> dict | None:
    """Provider-agnostic chat. Tries the active provider, then the configured fallback. Returns a
    normalised message dict {content, tool_calls, provider} or None if every provider fails."""
    cfg = cfg or load_llm_config()
    order = [cfg.get("provider", "ollama")]
    fb = cfg.get("fallback")
    if fb and fb not in order:
        order.append(fb)
    for name in order:
        res = _call_provider(name, cfg, messages, tools, timeout)
        if res is not None:
            res["provider"] = name
            return res
    return None


def active_provider(cfg: dict | None = None, timeout: int = 30) -> str | None:
    """Name of the first reachable provider (active, then fallback), or None. The timeout is generous
    because hosted reasoning models (Nemotron) can take several seconds for the first token."""
    cfg = cfg or load_llm_config()
    r = chat([{"role": "user", "content": "ok"}], cfg=cfg, timeout=timeout)
    return r.get("provider") if r else None


def available(cfg: dict | None = None, timeout: int = 30) -> bool:
    return active_provider(cfg, timeout) is not None


def phrase(facts: str, cfg: dict | None = None, timeout: int = 120) -> str | None:
    """Rephrase grounded facts. Returns None on any failure (caller keeps the deterministic answer)."""
    msgs = [{"role": "system", "content": _SYSTEM},
            {"role": "user", "content": f"Facts:\n{facts}\n\nRephrase as one paragraph."}]
    r = chat(msgs, cfg=cfg, timeout=timeout)
    return (r.get("content") or None) if r else None

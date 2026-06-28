"""
AI Registry — discovers provider modules, routes completions, tracks spend.

Providers register via @register. The default provider is chosen by the
AI_PROVIDER env var, else the first available provider in preference order
(local first, so you don't accidentally spend on cloud tokens).
"""
import os
import json
from datetime import datetime

from ai.base import AIProvider, AIResponse, LOCAL, CLOUD

_PROVIDERS: dict[str, AIProvider] = {}

# Preference order when no explicit provider is requested: local before cloud.
_PREFERENCE = ["ollama", "anthropic", "openai", "grok"]

_COST_LOG = os.path.join(os.path.dirname(__file__), "..", "state", "ai_costs.json")


def register(cls):
    inst = cls()
    _PROVIDERS[inst.name] = inst
    return cls


def all_providers() -> list[AIProvider]:
    return list(_PROVIDERS.values())


def get_provider(name: str | None = None) -> AIProvider | None:
    if name:
        return _PROVIDERS.get(name)
    # Explicit env override
    env_choice = os.getenv("AI_PROVIDER")
    if env_choice and env_choice in _PROVIDERS:
        return _PROVIDERS[env_choice]
    # First available in preference order
    for pname in _PREFERENCE:
        p = _PROVIDERS.get(pname)
        if p and p.available():
            return p
    # Any available at all
    for p in _PROVIDERS.values():
        if p.available():
            return p
    return None


def available_providers() -> list[str]:
    return [p.name for p in _PROVIDERS.values() if p.available()]


def complete(prompt: str, system: str | None = None, provider: str | None = None,
             model: str | None = None, max_tokens: int = 2048,
             temperature: float = 0.2) -> AIResponse:
    """Route a completion to the chosen (or default) provider and log cost."""
    p = get_provider(provider)
    if p is None:
        return AIResponse(text="", provider="none", model="none",
                          error="No AI provider configured (set an API key or run Ollama)")
    if not p.available():
        return p._unavailable(f"provider '{p.name}' not available (missing SDK or credentials)")

    resp = p.complete(prompt, system=system, model=model,
                      max_tokens=max_tokens, temperature=temperature)
    if resp.ok and resp.cost_usd:
        _log_cost(resp)
    return resp


def registry_summary() -> list[dict]:
    rows = []
    for p in _PROVIDERS.values():
        rows.append({
            "name": p.name,
            "cost_tier": p.cost_tier,
            "default_model": p.default_model,
            "available": p.available(),
            "description": p.description,
        })
    return rows


# ── Cost tracking ─────────────────────────────────────────────────────────────

def _log_cost(resp: AIResponse):
    log = _load_costs()
    log["total_usd"] = round(log.get("total_usd", 0.0) + resp.cost_usd, 6)
    log["calls"] = log.get("calls", 0) + 1
    by_provider = log.setdefault("by_provider", {})
    pdata = by_provider.setdefault(resp.provider, {"usd": 0.0, "calls": 0,
                                                   "input_tokens": 0, "output_tokens": 0})
    pdata["usd"] = round(pdata["usd"] + resp.cost_usd, 6)
    pdata["calls"] += 1
    pdata["input_tokens"] += resp.input_tokens
    pdata["output_tokens"] += resp.output_tokens
    log["last_updated"] = datetime.utcnow().isoformat()
    _save_costs(log)


def cost_summary() -> dict:
    return _load_costs()


def _load_costs() -> dict:
    if os.path.exists(_COST_LOG):
        with open(_COST_LOG) as f:
            return json.load(f)
    return {"total_usd": 0.0, "calls": 0, "by_provider": {}}


def _save_costs(log: dict):
    os.makedirs(os.path.dirname(_COST_LOG), exist_ok=True)
    with open(_COST_LOG, "w") as f:
        json.dump(log, f, indent=2)

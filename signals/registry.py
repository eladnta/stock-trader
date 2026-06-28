"""
Signal Registry — discovers signal modules and combines their results.

Signals register themselves via the @register decorator. The engine calls
evaluate_all() to run every enabled, applicable signal and combine them into
a single overlay on the base opportunity score.

Tier gating: by default only FREE signals run. To enable paid/LLM signals
later, just add their tier to config.allowed_costs — no code changes.
"""
from signals.base import Signal, SignalContext, SignalResult, FREE, ALL_TIERS

_REGISTRY: dict[str, Signal] = {}


def register(cls):
    """Class decorator: instantiate and register a signal module."""
    inst = cls()
    if inst.name in _REGISTRY:
        raise ValueError(f"Duplicate signal name: {inst.name}")
    _REGISTRY[inst.name] = inst
    return cls


def all_signals() -> list[Signal]:
    return list(_REGISTRY.values())


def get_signal(name: str) -> Signal | None:
    return _REGISTRY.get(name)


class SignalConfig:
    """Controls which signals run and how heavily they weigh.

    Defaults: only FREE-tier signals enabled. Each signal uses its own
    default_weight/default_enabled unless overridden here.
    """
    def __init__(self, allowed_costs: set | None = None,
                 weights: dict | None = None,
                 enabled_overrides: dict | None = None,
                 max_overlay: float = 3.0):
        self.allowed_costs = allowed_costs if allowed_costs is not None else {FREE}
        self.weights = weights or {}
        self.enabled_overrides = enabled_overrides or {}
        self.max_overlay = max_overlay

    def is_enabled(self, sig: Signal) -> bool:
        if sig.cost not in self.allowed_costs:
            return False
        return self.enabled_overrides.get(sig.name, sig.default_enabled)

    def weight(self, sig: Signal) -> float:
        return self.weights.get(sig.name, sig.default_weight)


# Module-level default config used by the engine; can be swapped.
DEFAULT_CONFIG = SignalConfig()


def evaluate_all(ctx: SignalContext, config: SignalConfig | None = None) -> dict:
    """Run all enabled+applicable signals and combine into an overlay."""
    config = config or DEFAULT_CONFIG
    results: list[dict] = []
    total = 0.0

    for sig in _REGISTRY.values():
        if not config.is_enabled(sig):
            continue
        if not sig.applicable(ctx):
            continue
        try:
            res = sig.evaluate(ctx)
        except Exception as e:
            res = SignalResult(name=sig.name, available=False, narrative=f"error: {e}")

        weight = config.weight(sig)
        contribution = 0.0
        if res.available:
            contribution = res.impact * weight * res.confidence
            total += contribution

        results.append({
            "name": res.name,
            "cost": sig.cost,
            "impact": round(res.impact, 2),
            "confidence": round(res.confidence, 2),
            "weight": weight,
            "contribution": round(contribution, 2),
            "narrative": res.narrative,
            "available": res.available,
            "details": res.details,
        })

    total = max(-config.max_overlay, min(config.max_overlay, total))
    adjusted = round(min(10, max(1, ctx.base_score + total)), 1)

    # Sort by absolute contribution for readable output
    results.sort(key=lambda r: abs(r["contribution"]), reverse=True)

    return {
        "symbol": ctx.symbol,
        "base_score": ctx.base_score,
        "total_overlay": round(total, 2),
        "adjusted_score": adjusted,
        "signals": results,
        "narrative": _summarize(results, total),
    }


def _summarize(results: list[dict], total: float) -> str:
    active = [r for r in results if r["available"] and abs(r["contribution"]) > 0.1]
    if not active:
        return f"Overlay {total:+.1f} — no significant signals"
    parts = [f"{r['name']} {r['contribution']:+.1f}" for r in active[:4]]
    return f"Overlay {total:+.1f} pts — " + ", ".join(parts)


def registry_summary() -> list[dict]:
    """For CLI display: list all registered signals and their metadata."""
    return [
        {
            "name": s.name,
            "cost": s.cost,
            "applies_to": list(s.applies_to),
            "weight": s.default_weight,
            "enabled": s.default_enabled,
            "description": s.description,
        }
        for s in _REGISTRY.values()
    ]

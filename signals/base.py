"""
Signal module interface — every signal is a self-contained, pluggable module.

To add a new signal: create a file in signals/modules/, subclass Signal,
decorate with @register, and it's automatically picked up by the engine.
No other code changes needed.

Each signal declares:
  - cost tier (free / paid / llm) → lets you toggle whole tiers on/off
  - applies_to → which asset classes it's relevant for
  - default_weight → its baseline weight in the combined overlay
  - default_enabled → whether it runs unless explicitly disabled

Each signal returns a SignalResult: an impact in score-points (roughly
-2..+2), a confidence (0..1), a human-readable narrative, and details.
The registry combines results as: sum(impact × weight × confidence),
clamped, then applied to the base opportunity score.
"""
from dataclasses import dataclass, field

# ── Cost tiers ────────────────────────────────────────────────────────────────
FREE = "free"   # public/free data, no per-call cost (yfinance, EDGAR)
PAID = "paid"   # paid data feeds (options flow, alt-data, sentiment APIs)
LLM = "llm"     # costs Claude tokens (filing/transcript reading)

ALL_TIERS = (FREE, PAID, LLM)


@dataclass
class SignalContext:
    """Everything a signal needs to evaluate a single instrument.
    Shared market data (macro/alternatives/news) is fetched ONCE by the engine
    and passed in, so signals never refetch."""
    symbol: str
    asset_class: str
    sector: str
    base_score: float
    info: dict = field(default_factory=dict)
    history: object = None              # price history DataFrame
    macro: dict = field(default_factory=dict)
    alternatives: dict = field(default_factory=dict)
    news: dict = field(default_factory=dict)
    extra: dict = field(default_factory=dict)   # signal-specific scratch space


@dataclass
class SignalResult:
    name: str
    impact: float = 0.0          # contribution in score-points (-2..+2 typical)
    confidence: float = 1.0      # 0..1, scales the impact
    narrative: str = ""
    details: dict = field(default_factory=dict)
    available: bool = True        # False = no data, skip from combination


class Signal:
    """Base class for all signal modules."""
    name: str = "base"
    description: str = ""
    cost: str = FREE
    applies_to: tuple = ("all",)
    default_weight: float = 1.0
    default_enabled: bool = True

    def applicable(self, ctx: SignalContext) -> bool:
        return "all" in self.applies_to or ctx.asset_class in self.applies_to

    def evaluate(self, ctx: SignalContext) -> SignalResult:
        raise NotImplementedError

    # convenience for subclasses
    def _result(self, impact=0.0, confidence=1.0, narrative="", available=True, **details):
        return SignalResult(
            name=self.name, impact=impact, confidence=confidence,
            narrative=narrative, available=available, details=details,
        )

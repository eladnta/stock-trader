---
name: add-signal
description: Add a new signal module to the stock-trader system. Use when the user wants to add a new market signal, indicator, or factor (e.g. PEAD, insider buying, options flow, RSI) to the analysis engine.
---

# Add a Signal Module

In this project a **signal is a module**. Every signal is a self-contained file
in `signals/modules/` that subclasses `Signal`, registers itself, and is
auto-combined by the engine. Adding one never requires editing the core.

## Steps

### 1. Capture intent
Clarify: what does the signal measure, which asset classes it applies to
(`equity`, `commodity`, `currency`, `index_etf`, ... or `all`), what data it
needs (already in `SignalContext`? price history? a new fetch?), and its cost
tier (`free` = public data, `paid` = paid feed, `llm` = uses the AI layer).

### 2. Create the module
Create `signals/modules/<name>.py`:

```python
from signals.base import Signal, SignalContext, FREE   # or PAID / LLM
from signals.registry import register


@register
class MySignal(Signal):
    name = "my_signal"               # unique
    description = "One-line what + when"
    cost = FREE
    applies_to = ("equity",)         # or ("all",)
    default_weight = 1.0

    def evaluate(self, ctx: SignalContext):
        # ctx gives: symbol, asset_class, sector, base_score, info, history,
        #            macro, alternatives, news
        if not ctx.history:                      # graceful degradation
            return self._result(available=False, narrative="no data")
        impact = ...      # roughly -2..+2 score points (+ = bullish)
        confidence = ...  # 0..1, scales the impact
        return self._result(impact=impact, confidence=confidence,
                            narrative="short human explanation")
```

### 3. Register it
Add an import line to `signals/modules/__init__.py`:

```python
from signals.modules import my_signal  # noqa: F401
```

### 4. Verify
```bash
python monitor.py modules     # your signal should appear with its tier/weight
python -c "import engine"     # confirms it loads and registers cleanly
```

For a `free` signal it runs immediately. `paid`/`llm` signals are gated off
until that tier is added to `SignalConfig.allowed_costs` — that's intentional.

## Conventions
- Return impact in score-points, not raw indicator values; clamp it.
- Set `confidence` honestly (e.g. scale by sample size / data quality).
- Reuse shared market data from `ctx` (macro/alternatives/news) — don't refetch.
- Document the source and any lookahead-bias caveat in the docstring.

## Reference
- `signals/base.py` — the interface
- `signals/registry.py` — registration + combination
- `signals/modules/trend_confirmation.py` — a clean free example
- `signals/modules/llm_thesis.py` — an LLM-tier example using the AI layer

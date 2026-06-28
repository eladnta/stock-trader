# stock-trader — project guide for Claude

A modular cross-asset market analysis and **paper-trading** system (virtual
$10,000). It analyzes stocks and ETFs (indices, sectors, countries,
commodities, currencies, bonds, crypto), scores risk and time horizons,
overlays news/macro/alternative-asset signals, and simulates realistic trades
to compare itself against the market (SPY/QQQ).

> Educational / personal use. Built on free public data (Yahoo Finance via
> `yfinance`, SEC EDGAR). Not financial advice.

## Architecture

```
universe.py   → registry of tradeable instruments + asset-class routing
engine.py     → central orchestrator: analyze(symbol) routes to the right pipeline
analysis/     → fundamental scorers (risk, horizon, analyst) + technical analysis
signals/      → pluggable signal modules + SQLite event DB
ai/           → pluggable LLM providers (Ollama, Anthropic, OpenAI, Grok)
trading/      → portfolio, position sizing, order engine, conviction tracker, benchmark
trader.py     → paper-trading CLI
monitor.py    → continuous signal monitoring CLI
ai_cli.py     → AI provider CLI
demo.py       → offline demo with mock data
```

`engine.analyze("AAPL")` (equity) and `engine.analyze("GLD")` (commodity) both
return the **same recommendation shape**, so the trader works across all asset
classes unchanged.

## Two plugin systems — the core design

1. **A signal is a module.** Each signal lives in `signals/modules/`, subclasses
   `Signal`, and registers with `@register`. It declares a cost tier
   (`free`/`paid`/`llm`), the asset classes it applies to, and a weight. The
   engine combines all enabled signals: `adjusted = base + Σ(impact × weight ×
   confidence)`. Only `free` signals run by default.
2. **An AI provider is a module.** Each provider in `ai/providers/` implements
   `AIProvider`. AI-backed signals call `ai.complete(...)` and get whichever
   provider is configured. Local (Ollama) is preferred over cloud so tokens are
   never spent by accident.

To extend the system, add a module — don't edit the core. See the
`/add-signal` and `/add-ai-provider` skills.

## Running

```bash
pip install -r requirements.txt
python demo.py                 # offline demo, no network
python trader.py demo          # dry-run trading cycle (mock data)
python trader.py run           # full cycle on live data (needs internet)
python trader.py status        # portfolio + P&L
python trader.py performance   # Sharpe, drawdown, alpha vs SPY/QQQ
python trader.py conviction    # prediction accuracy by horizon/sector/risk
python monitor.py signals      # market macro + alternatives snapshot
python monitor.py modules      # list registered signal modules
python ai_cli.py providers     # list AI providers + availability
```

## Conventions & guardrails

- **No tokens are spent unless an AI provider is configured** (API key present).
  The free signal path imports no provider.
- **Runtime state** (`state/*.json`, `state/events.db`) is gitignored — never
  commit it. `python trader.py reset` wipes it for a fresh $10k.
- **Beware lookahead bias.** `yfinance` returns *restated* fundamentals, not
  point-in-time. Any backtest built on it will be optimistic. Prefer SEC EDGAR
  filing dates when timestamping fundamentals.
- Match the surrounding style: small focused modules, dataclasses for results,
  clamp scores to documented ranges, graceful degradation on missing data.
- This environment may block outbound network — if `yfinance`/EDGAR calls fail
  with connection errors, use `demo.py` / the `demo` subcommands to verify logic.

## Roadmap (see README.md)

Fundamental alpha signals (PEAD, analyst revisions, insider Form 4, accruals);
point-in-time fundamentals; calibration layer (Brier score) + adaptive signal
weighting; LLM filing reader (ROI-gated); web dashboard.

# Financial Analysis & Paper Trading System (POC)

A cross-asset analysis and paper-trading system. Starts with a virtual $10,000,
allocates by risk and conviction, trades at realistic human pace (minutes-to-days,
not HFT), and measures its own prediction accuracy over time — then compares
itself against the market (SPY/QQQ).

> **Private use.** Built entirely on free/public data (Yahoo Finance, SEC EDGAR).
> No API keys required for the POC. Everything runs locally; nothing is sent out.
> Not financial advice.

## Architecture

```
                          ┌──────────────┐
                          │  engine.py   │  ← central orchestrator
                          │  analyze()   │     routes by asset class
                          └──────┬───────┘
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
      ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
      │  EQUITY      │  │  ETF/INDEX   │  │  SIGNAL OVERLAY   │
      │  fundamental │  │  COMMODITY   │  │  news + macro +   │
      │  risk/horizon│  │  CURRENCY    │  │  alternatives →   │
      │  /analyst    │  │  BOND/CRYPTO │  │  per-STOCK impact │
      │              │  │  technical   │  │                   │
      └──────────────┘  └──────────────┘  └──────────────────┘
              └──────────────────┬──────────────────┘
                                 ▼
                    Unified Recommendation (same shape)
                                 ▼
              ┌──────────────────────────────────┐
              │  TRADER  position-sizing → order │
              │  engine (delay+slippage) → P&L   │
              │  conviction tracker → benchmark  │
              └──────────────────────────────────┘
```

## Tradeable Universe

Beyond individual stocks, the system trades **indices, sectors, countries,
commodities, currencies, bonds, and crypto** — all via ETFs on US exchanges.
This also gives multi-country exposure (Japan `EWJ`, Germany `EWG`, India
`INDA`, Israel `EIS`) without foreign data feeds.

| Asset class | Examples | Analysis |
|---|---|---|
| Equity | AAPL, NVDA, JPM | Fundamental: risk + horizon + analyst consensus |
| Index ETF | SPY, QQQ, IWM | Technical: trend + momentum + relative strength |
| Country ETF | EWJ, EWG, INDA, EIS | Technical + country macro |
| Sector ETF | XLK, XLF, XLE | Technical + sector rotation |
| Commodity | GLD, USO, CPER | Technical + supply/macro |
| Currency | UUP, FXE, FXY | Technical + rate-differential |
| Bond | TLT, HYG, TIP | Technical + rate regime |
| Crypto | BTC-USD, ETH-USD | Technical + risk appetite |

## Modules

| Module | Role |
|---|---|
| `universe.py` | Registry of all tradeable instruments + asset-class routing |
| `engine.py` | Central orchestrator — analyze any symbol, apply signal overlay |
| `analysis/` | Equity scorers (risk, horizon, analyst) + technical analyzer |
| `signals/` | Macro monitor, news analyzer, alternatives, stock-impact, event DB |
| `trading/` | Portfolio, position sizer, order engine, conviction tracker, benchmark |
| `trader.py` | Paper-trading CLI |
| `monitor.py` | Continuous signal monitoring CLI |
| `demo.py` | Offline demo with mock data |

## Usage

```bash
pip install -r requirements.txt

# Analysis
python main.py analyze AAPL          # single equity, full report
python monitor.py signals            # market-wide macro + alternatives snapshot
python monitor.py stock XOM          # full signal overlay for one stock
python monitor.py news NVDA          # news + entity sentiment + event tags

# Paper trading ($10,000 virtual)
python trader.py demo                # dry-run with mock data
python trader.py run                 # full cycle (mixed equity + cross-asset)
python trader.py run --universe cross-asset   # ETFs/commodities/FX/crypto only
python trader.py status              # portfolio + P&L
python trader.py performance         # Sharpe, drawdown, alpha vs SPY/QQQ
python trader.py conviction          # prediction accuracy by horizon/sector/risk

# Continuous monitoring
python monitor.py run --interval 30  # refresh signals every 30 min
python monitor.py db                 # event database stats
```

## Signals are Modules (plugin architecture)

Every signal is a **self-contained, pluggable module** with its own cost tier,
weight, and asset-class scope. The engine auto-discovers all registered signals
and combines them: `adjusted = base + Σ(impact × weight × confidence)`.

```python
# signals/modules/my_new_signal.py — that's all it takes to add a signal
from signals.base import Signal, FREE
from signals.registry import register

@register
class MyNewSignal(Signal):
    name = "my_signal"
    cost = FREE                  # free | paid | llm
    applies_to = ("equity",)     # or ("all",), or specific asset classes
    default_weight = 1.0

    def evaluate(self, ctx):
        return self._result(impact=+1.2, confidence=0.7, narrative="...")
```

**Cost tiers gate whole categories.** Only `free` signals run by default. When
you later want paid data feeds or LLM-based signals (10-K reading, earnings-call
analysis), you add that tier to `SignalConfig.allowed_costs` — no code changes,
no rewrites. The paid/LLM modules plug into the exact same interface.

Current free signals: `macro_regime`, `vix_fear`, `alternatives_impact`,
`news_events`, `trend_confirmation`. List them with `python monitor.py modules`.

| Layer | Module | Role |
|---|---|---|
| Interface | `signals/base.py` | `Signal` base class, `SignalContext`, `SignalResult`, cost tiers |
| Registry | `signals/registry.py` | Registration, config (tiers/weights/enable), combination |
| Modules | `signals/modules/*.py` | One file per signal — drop-in, auto-discovered |

## AI Model Layer (pluggable LLM providers)

The same plug-in philosophy applied to LLM backends. Each provider is an
adapter behind one interface; AI-based signals call `ai.complete(...)` and get
whichever provider is configured — swap or add a provider without touching
signal code.

| Provider | Tier | Default model | Needs |
|---|---|---|---|
| `ollama` | local | `llama3.1` | Ollama running locally (zero per-token cost) |
| `anthropic` | cloud | `claude-opus-4-8` | `anthropic` SDK + `ANTHROPIC_API_KEY` |
| `openai` | cloud | configurable | `openai` SDK + `OPENAI_API_KEY` |
| `grok` | cloud | `grok-2-latest` | `openai` SDK + `XAI_API_KEY` (xAI OpenAI-compatible API) |

**Nothing spends tokens by default.** No keys → every provider reports
unavailable and `ai.complete()` fails gracefully. The default provider is
chosen by `AI_PROVIDER`, else the first available one — **local before cloud**,
so you never accidentally spend on cloud tokens. All spend is logged to
`state/ai_costs.json` and viewable with `python ai_cli.py cost`.

Adding a provider = one file in `ai/providers/` implementing `AIProvider`.

```bash
python ai_cli.py providers          # list providers + availability
python ai_cli.py test "..."         # run a completion (--provider X to pick)
python ai_cli.py cost               # accumulated token spend
```

The two modular layers connect via `signals/modules/llm_thesis.py` — an
`llm`-tier signal that reads news through the AI layer. It's registered but
**dormant** until the LLM cost tier is enabled (`SignalConfig.allowed_costs`),
so the free path never imports a provider or spends a token.

| Layer | Module | Role |
|---|---|---|
| Interface | `ai/base.py` | `AIProvider`, `AIResponse`, cost tiers |
| Registry | `ai/registry.py` | Provider discovery, routing, cost tracking |
| Adapters | `ai/providers/*.py` | One file per provider — Ollama, Anthropic, OpenAI, Grok |

## Design Principles

1. **Realistic pace** — orders execute after a 5–45 min human delay + slippage.
   Horizons span minutes to months, never HFT.
2. **Gets smarter over time** — the SQLite event DB caches signals (faster each
   run) and accumulates event→outcome history (accuracy patterns per
   event-type/sector).
3. **Reliability over hype** — the goal is calibrated, measurable prediction
   accuracy, benchmarked against the market.

## Roadmap

- [ ] Fundamental alpha signals (PEAD, analyst revisions, insider Form 4, accruals)
- [ ] Point-in-time fundamentals from EDGAR (avoid lookahead bias)
- [ ] Calibration layer (Brier score) + adaptive signal weighting
- [ ] LLM filing reader (10-K/earnings call) — first paid module, ROI-gated
- [ ] Web dashboard (portfolio vs market, signal heatmap, event timeline)

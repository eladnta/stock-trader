---
name: run-system
description: Launch and operate the stock-trader system. Use when the user wants to run the analyzer, paper trader, or monitor, or to verify a change works end to end.
---

# Run the stock-trader System

## First time
```bash
pip install -r requirements.txt
```

## If the network is restricted (offline check)
The analyzers need Yahoo Finance / SEC EDGAR. If those are blocked (you'll see
connection / 403 errors), verify logic with the offline paths instead:
```bash
python demo.py             # full analysis pipeline on 5 mock stocks
python trader.py demo      # one trading cycle on mock data, no state written
```

## Analysis (live data)
```bash
python main.py analyze AAPL          # single equity, full report
python monitor.py signals            # macro + alternatives snapshot
python monitor.py stock XOM          # full signal overlay for one symbol
python monitor.py news NVDA          # news + entity sentiment + event tags
python monitor.py modules            # list registered signal modules
```

## Paper trading ($10,000 virtual)
```bash
python trader.py run                 # full cycle: analyze → size → queue orders
python trader.py run --universe cross-asset   # ETFs/commodities/FX/crypto only
python trader.py status              # holdings + P&L
python trader.py performance         # Sharpe, drawdown, alpha vs SPY/QQQ
python trader.py conviction          # prediction accuracy by horizon/sector/risk
python trader.py pending             # orders queued (execute on next run)
python trader.py reset               # wipe state, fresh $10k (asks confirmation)
```

Orders execute on a realistic delay (5–45 min) with slippage — they are queued
on one `run` and filled on a later `run`, so run it on a schedule (e.g. a few
times a day) rather than expecting instant fills.

## AI layer
```bash
python ai_cli.py providers           # providers + availability
python ai_cli.py test "..."          # test a completion (--provider X)
python ai_cli.py cost                # accumulated token spend
```
Set a provider key (e.g. `ANTHROPIC_API_KEY`) or run Ollama locally to enable
AI-backed signals; nothing spends tokens until then.

## Continuous monitoring
```bash
python monitor.py run --interval 30  # refresh signals every 30 min, alert on portfolio
```

## Verify a change worked
After editing, the fastest confidence check:
```bash
python -c "import engine"            # everything imports + registers
python demo.py                       # pipeline produces recommendations
```

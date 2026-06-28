---
name: add-ai-provider
description: Add a new LLM provider to the stock-trader AI layer. Use when the user wants to plug in another AI backend (e.g. Gemini, Mistral, a local model, an internal endpoint) for AI-backed signals.
---

# Add an AI Provider

An **AI provider is a module**. Each adapter in `ai/providers/` implements the
`AIProvider` interface and registers itself. AI-backed signals call
`ai.complete(...)` and get whichever provider is configured — providers are
interchangeable.

## Steps

### 1. Create the adapter
Create `ai/providers/<name>.py`:

```python
import os
from ai.base import AIProvider, AIResponse, CLOUD   # or LOCAL
from ai.registry import register

PRICING = {  # per 1M tokens (input, output) — for cost tracking
    "model-id": (1.00, 3.00),
}

@register
class MyProvider(AIProvider):
    name = "myprovider"
    cost_tier = CLOUD                  # LOCAL for on-machine models (zero cost)
    description = "One-line description"
    default_model = os.getenv("MYPROVIDER_MODEL", "model-id")
    pricing = PRICING

    def available(self) -> bool:
        # True only if SDK importable AND credentials present
        if not os.getenv("MYPROVIDER_API_KEY"):
            return False
        try:
            import myprovider_sdk  # noqa: F401  (lazy)
            return True
        except Exception:
            return False

    def complete(self, prompt, system=None, model=None, max_tokens=2048, temperature=0.2):
        model = model or self.default_model
        try:
            # ... call the API, lazy-import the SDK inside ...
            text = ...
            in_tok, out_tok = ..., ...
            return AIResponse(text=text, provider=self.name, model=model,
                              input_tokens=in_tok, output_tokens=out_tok,
                              cost_usd=self.estimate_cost(in_tok, out_tok, model))
        except Exception as e:
            return self._unavailable(f"call failed: {e}", model)
```

### 2. Register it
Add to `ai/providers/__init__.py`:

```python
from ai.providers import myprovider  # noqa: F401
```

If the provider should be auto-selected by preference, add its `name` to
`_PREFERENCE` in `ai/registry.py` (local providers should come before cloud).

### 3. Verify
```bash
python ai_cli.py providers           # appears; available=False until a key is set
python ai_cli.py test "hello" --provider myprovider
```

## Anthropic SDK note
If adding/maintaining the Anthropic provider, the current model is
`claude-opus-4-8` with `thinking={"type": "adaptive"}`. Do not use
`budget_tokens` (removed) or `temperature`/`top_p` on Opus 4.7/4.8 (they 400).
Use the official `anthropic` SDK, not raw HTTP.

## Conventions
- Lazy-import the SDK inside methods so a missing package never breaks loading.
- `available()` must be honest — no key/SDK → False (so the engine skips it).
- Always populate token counts + `cost_usd`; spend is logged to
  `state/ai_costs.json` and shown by `python ai_cli.py cost`.
- Never spend cloud tokens by default — local is preferred in selection.

## Reference
- `ai/base.py`, `ai/registry.py`
- `ai/providers/anthropic_provider.py`, `ai/providers/local_ollama.py`

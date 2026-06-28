"""
LLM thesis signal — example of an AI-backed signal module.

Cost tier = LLM, so it is OFF by default (SignalConfig only enables FREE).
When you enable the LLM tier later, this signal asks the configured AI provider
(Ollama / Anthropic / OpenAI / Grok) to read the recent news and return a
directional view. It runs only on equities and only when news is present —
keeping token spend to high-value, low-frequency calls.

This is the bridge between the two modular layers: signals (this module) and
AI providers (the ai package). Swapping the provider never touches this file.
"""
import json

from signals.base import Signal, SignalContext, LLM
from signals.registry import register


@register
class LLMThesisSignal(Signal):
    name = "llm_thesis"
    description = "AI-read news thesis (uses configured LLM provider) — paid tier"
    cost = LLM
    applies_to = ("equity",)
    default_weight = 1.2
    default_enabled = True   # still gated off by cost tier until LLM is allowed

    def evaluate(self, ctx: SignalContext):
        import ai  # lazy import so the FREE-only path never imports providers

        provider = ai.get_provider()
        if provider is None:
            return self._result(available=False, narrative="no AI provider configured")

        news = ctx.news or {}
        headlines = news.get("top_positive", []) + news.get("top_negative", [])
        if not headlines:
            return self._result(available=False, narrative="no news to analyze")

        system = ("You are an equity analyst. Given recent headlines for a stock, "
                  "respond ONLY with compact JSON: "
                  '{"impact": <-2.0..2.0>, "confidence": <0..1>, "reason": "<short>"}. '
                  "Positive impact = bullish, negative = bearish.")
        prompt = (f"Ticker {ctx.symbol} ({ctx.sector}). Recent headlines:\n"
                  + "\n".join(f"- {h}" for h in headlines[:8]))

        resp = ai.complete(prompt, system=system, max_tokens=300)
        if not resp.ok:
            return self._result(available=False, narrative=f"AI error: {resp.error}")

        try:
            parsed = json.loads(_extract_json(resp.text))
            impact = max(-2.0, min(2.0, float(parsed.get("impact", 0))))
            confidence = max(0.0, min(1.0, float(parsed.get("confidence", 0.5))))
            reason = str(parsed.get("reason", ""))[:80]
        except Exception:
            return self._result(available=False, narrative="AI returned unparseable output")

        return self._result(
            impact=impact, confidence=confidence,
            narrative=f"{resp.provider}: {reason}",
            provider=resp.provider, cost_usd=resp.cost_usd,
        )


def _extract_json(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    return text[start:end + 1] if start >= 0 and end > start else text

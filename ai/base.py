"""
AI provider interface — every LLM backend is a pluggable adapter.

Same modular philosophy as the signal layer: each provider (local Ollama,
Anthropic, OpenAI, Grok) implements one interface and registers itself.
AI-based signals call `ai.complete(...)` and get whichever provider is
configured — swap or add a provider without touching signal code.

Providers report a cost tier so spend is visible:
  local  — runs on your machine, no per-token cost (Ollama)
  cloud  — paid API per token (Anthropic, OpenAI, Grok)

Nothing here spends money unless a provider is configured (API key present).
Until then providers report available=False and are skipped.
"""
from dataclasses import dataclass, field

LOCAL = "local"
CLOUD = "cloud"


@dataclass
class AIResponse:
    text: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


class AIProvider:
    """Base class for all LLM provider adapters."""
    name: str = "base"
    cost_tier: str = CLOUD
    description: str = ""
    default_model: str = ""

    # Pricing per 1M tokens (input, output). Override per provider.
    pricing: dict[str, tuple[float, float]] = {}

    def available(self) -> bool:
        """True if this provider can actually be called (SDK + credentials)."""
        raise NotImplementedError

    def complete(self, prompt: str, system: str | None = None,
                 model: str | None = None, max_tokens: int = 2048,
                 temperature: float = 0.2) -> AIResponse:
        raise NotImplementedError

    def estimate_cost(self, input_tokens: int, output_tokens: int,
                      model: str | None = None) -> float:
        model = model or self.default_model
        rates = self.pricing.get(model)
        if not rates:
            # fall back to the first configured price, else 0
            rates = next(iter(self.pricing.values()), (0.0, 0.0))
        in_rate, out_rate = rates
        return round(input_tokens / 1e6 * in_rate + output_tokens / 1e6 * out_rate, 6)

    def _unavailable(self, reason: str, model: str | None = None) -> AIResponse:
        return AIResponse(text="", provider=self.name,
                          model=model or self.default_model, error=reason)

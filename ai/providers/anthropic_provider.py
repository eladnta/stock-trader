"""
Anthropic provider — Claude via the official `anthropic` SDK.

Defaults to Claude Opus 4.8 (claude-opus-4-8) with adaptive thinking, per
Anthropic's current API. Requires `pip install anthropic` and ANTHROPIC_API_KEY.
Until that key is set, available() returns False and no tokens are spent.
"""
import os

from ai.base import AIProvider, AIResponse, CLOUD
from ai.registry import register

# Pricing per 1M tokens (input, output) — Claude model lineup.
ANTHROPIC_PRICING = {
    "claude-opus-4-8":   (5.00, 25.00),
    "claude-opus-4-7":   (5.00, 25.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5":  (1.00, 5.00),
    "claude-fable-5":    (10.00, 50.00),
}


@register
class AnthropicProvider(AIProvider):
    name = "anthropic"
    cost_tier = CLOUD
    description = "Claude (Opus 4.8 default) via the Anthropic SDK"
    default_model = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")
    pricing = ANTHROPIC_PRICING

    def _client(self):
        import anthropic  # lazy import so missing SDK doesn't break module load
        return anthropic.Anthropic()

    def available(self) -> bool:
        if not os.getenv("ANTHROPIC_API_KEY"):
            return False
        try:
            import anthropic  # noqa: F401
            return True
        except Exception:
            return False

    def complete(self, prompt, system=None, model=None, max_tokens=2048, temperature=0.2):
        model = model or self.default_model
        try:
            client = self._client()
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                thinking={"type": "adaptive"},          # current Claude default
                output_config={"effort": "medium"},
                system=system or "You are a precise financial analysis assistant.",
                messages=[{"role": "user", "content": prompt}],
            )
            # response.content is a list of blocks; collect text blocks only
            text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
            in_tok = resp.usage.input_tokens
            out_tok = resp.usage.output_tokens
            return AIResponse(
                text=text, provider=self.name, model=model,
                input_tokens=in_tok, output_tokens=out_tok,
                cost_usd=self.estimate_cost(in_tok, out_tok, model),
            )
        except Exception as e:
            return self._unavailable(f"Anthropic call failed: {e}", model)

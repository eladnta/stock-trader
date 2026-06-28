"""
OpenAI provider — GPT models via the official `openai` SDK.

Requires `pip install openai` and OPENAI_API_KEY. Model is configurable via
OPENAI_MODEL (set it to whatever GPT model your account uses). Pricing is
configurable below — update to match the model you select.
"""
import os

from ai.base import AIProvider, AIResponse, CLOUD
from ai.registry import register

# Pricing per 1M tokens (input, output). Approximate / configurable —
# update to the rates for the model you actually use.
OPENAI_PRICING = {
    "gpt-4o":      (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
}


@register
class OpenAIProvider(AIProvider):
    name = "openai"
    cost_tier = CLOUD
    description = "OpenAI GPT models via the openai SDK"
    default_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    pricing = OPENAI_PRICING

    def available(self) -> bool:
        if not os.getenv("OPENAI_API_KEY"):
            return False
        try:
            import openai  # noqa: F401
            return True
        except Exception:
            return False

    def complete(self, prompt, system=None, model=None, max_tokens=2048, temperature=0.2):
        model = model or self.default_model
        try:
            from openai import OpenAI
            client = OpenAI()
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            resp = client.chat.completions.create(
                model=model, messages=messages,
                max_tokens=max_tokens, temperature=temperature,
            )
            text = resp.choices[0].message.content or ""
            in_tok = resp.usage.prompt_tokens
            out_tok = resp.usage.completion_tokens
            return AIResponse(
                text=text, provider=self.name, model=model,
                input_tokens=in_tok, output_tokens=out_tok,
                cost_usd=self.estimate_cost(in_tok, out_tok, model),
            )
        except Exception as e:
            return self._unavailable(f"OpenAI call failed: {e}", model)

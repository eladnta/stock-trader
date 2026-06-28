"""
Grok provider — xAI Grok via its OpenAI-compatible API.

xAI exposes an OpenAI-compatible endpoint at https://api.x.ai/v1, so we reuse
the `openai` SDK with a custom base_url. Requires `pip install openai` and
XAI_API_KEY. Model configurable via XAI_MODEL.
"""
import os

from ai.base import AIProvider, AIResponse, CLOUD
from ai.registry import register

XAI_BASE_URL = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")

# Pricing per 1M tokens (input, output). Approximate / configurable.
GROK_PRICING = {
    "grok-2-latest": (2.00, 10.00),
}


@register
class GrokProvider(AIProvider):
    name = "grok"
    cost_tier = CLOUD
    description = "xAI Grok via the OpenAI-compatible API"
    default_model = os.getenv("XAI_MODEL", "grok-2-latest")
    pricing = GROK_PRICING

    def available(self) -> bool:
        if not os.getenv("XAI_API_KEY"):
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
            client = OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url=XAI_BASE_URL)
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
            return self._unavailable(f"Grok call failed: {e}", model)

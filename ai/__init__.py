"""
AI model layer — pluggable LLM providers (local Ollama, Anthropic, OpenAI, Grok).

Usage:
    import ai
    resp = ai.complete("Summarize this 10-Q ...", system="You are an analyst.")
    if resp.ok:
        print(resp.text, resp.cost_usd)

The default provider is chosen by AI_PROVIDER, else the first available one
(local before cloud, so cloud tokens are never spent by accident).
"""
from ai import providers  # noqa: F401  registers all provider modules
from ai.registry import (
    complete, get_provider, available_providers,
    registry_summary, cost_summary, all_providers,
)
from ai.base import AIResponse, LOCAL, CLOUD

__all__ = [
    "complete", "get_provider", "available_providers",
    "registry_summary", "cost_summary", "all_providers",
    "AIResponse", "LOCAL", "CLOUD",
]

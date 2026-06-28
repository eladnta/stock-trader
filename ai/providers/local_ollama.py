"""
Local provider — Ollama (runs models on your own machine, no per-token cost).

Talks to the Ollama HTTP API at http://localhost:11434. Set OLLAMA_MODEL to
choose the model (default llama3.1). cost_tier=local, pricing is zero.
"""
import os
import requests

from ai.base import AIProvider, AIResponse, LOCAL
from ai.registry import register

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")


@register
class OllamaProvider(AIProvider):
    name = "ollama"
    cost_tier = LOCAL
    description = "Local models via Ollama (no per-token cost)"
    default_model = os.getenv("OLLAMA_MODEL", "llama3.1")
    pricing = {}  # local = free

    def available(self) -> bool:
        try:
            r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def complete(self, prompt, system=None, model=None, max_tokens=2048, temperature=0.2):
        model = model or self.default_model
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "system": system or "",
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }
            r = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=120)
            r.raise_for_status()
            data = r.json()
            return AIResponse(
                text=data.get("response", ""),
                provider=self.name,
                model=model,
                input_tokens=data.get("prompt_eval_count", 0),
                output_tokens=data.get("eval_count", 0),
                cost_usd=0.0,  # local
            )
        except Exception as e:
            return self._unavailable(f"Ollama call failed: {e}", model)

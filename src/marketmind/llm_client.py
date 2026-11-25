"""MarketMind AI - LLM client.

Sends chat requests to local Ollama or, optionally, OpenRouter.
OpenRouter needs OPENROUTER_API_KEY and OPENROUTER_MODEL environment variables.
"""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from marketmind.settings import load_config


def ollama_status() -> dict:
    llm = load_config()["llm"]
    base = llm["ollama_url"].split("/api/")[0]
    try:
        with urlopen(f"{base}/api/tags", timeout=3) as response:
            models = [m.get("name") for m in json.loads(response.read().decode("utf-8")).get("models", [])]
    except (URLError, OSError, ValueError):
        return {"reachable": False, "model": llm["ollama_model"], "model_installed": False}
    return {"reachable": True, "model": llm["ollama_model"], "model_installed": llm["ollama_model"] in models}


def chat(messages: list[dict], *, provider: str | None = None, model: str | None = None) -> str:
    config = load_config()
    llm = config["llm"]
    selected_provider = provider or llm["provider"]
    if selected_provider == "openrouter":
        url = "https://openrouter.ai/api/v1/chat/completions"
        selected_model = model or llm.get("openrouter_model")
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not api_key or not selected_model:
            raise RuntimeError("OpenRouter requires OPENROUTER_API_KEY and OPENROUTER_MODEL environment variables.")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
    else:
        url = llm["ollama_url"]
        selected_model = model or llm["ollama_model"]
        headers = {"Content-Type": "application/json"}

    payload = {
        "model": selected_model,
        "messages": messages,
        "stream": False,
        "temperature": llm.get("temperature", 0.2),
    }
    request = Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urlopen(request, timeout=int(llm.get("timeout_seconds", 240))) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM HTTP {exc.code}: {detail[:500]}") from exc
    except URLError as exc:
        raise RuntimeError(f"LLM provider is unreachable: {exc.reason}") from exc

    if selected_provider == "openrouter":
        return result["choices"][0]["message"]["content"].strip()
    return result["message"]["content"].strip()

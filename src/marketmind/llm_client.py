"""LiteLLM routes for the local Ollama model and optional OpenRouter models."""

from __future__ import annotations

import json
import os
from urllib.error import URLError
from urllib.request import urlopen

from openai import OpenAIError

from marketmind.settings import load_config


def ollama_status() -> dict:
    llm = load_config()["llm"]
    base = llm["ollama_url"].split("/api/")[0]
    try:
        with urlopen(f"{base}/api/tags", timeout=3) as response:
            models = [item.get("name") for item in json.loads(response.read().decode("utf-8")).get("models", [])]
    except (URLError, OSError, ValueError):
        return {"reachable": False, "model": llm["ollama_model"], "model_installed": False}
    return {"reachable": True, "model": llm["ollama_model"], "model_installed": llm["ollama_model"] in models}


def chat(
    messages: list[dict],
    *,
    provider: str | None = None,
    model: str | None = None,
    json_mode: bool = False,
) -> str:
    os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
    from litellm import completion

    config = load_config()
    llm = config["llm"]
    routes = config.get("litellm", {}).get("routes", {})
    selected_provider = provider or llm["provider"]
    if selected_provider == "ollama":
        selected_model = model or llm["ollama_model"]
        route = routes.get("ollama", {})
        model_id = route.get("model", "ollama_chat/{model}").format(model=selected_model)
        api_base = route.get("api_base") or llm["ollama_url"].split("/api/")[0]
        kwargs = {"model": model_id, "api_base": api_base}
    elif selected_provider == "openrouter":
        selected_model = model or llm.get("openrouter_model", "")
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not api_key or not selected_model:
            raise RuntimeError("OpenRouter requires OPENROUTER_API_KEY and OPENROUTER_MODEL.")
        route = routes.get("openrouter", {})
        model_id = route.get("model_prefix", "openrouter/") + selected_model
        kwargs = {"model": model_id, "api_key": api_key}
        if route.get("api_base"):
            kwargs["api_base"] = route["api_base"]
    else:
        raise ValueError(f"Unsupported LLM provider: {selected_provider}")

    try:
        result = completion(
            **kwargs,
            messages=messages,
            temperature=float(llm.get("temperature", 0.2)),
            timeout=int(llm.get("timeout_seconds", 240)),
            max_tokens=int(llm.get("num_predict", 700)),
            response_format={"type": "json_object"} if json_mode else None,
        )
    except OpenAIError as exc:
        raise RuntimeError(f"LiteLLM provider request failed: {exc}") from exc
    content = result.choices[0].message.content
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("LLM provider returned an empty response.")
    return content.strip()

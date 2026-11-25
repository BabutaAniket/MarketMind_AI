"""MarketMind AI - Ollama connection test.

Sends one short request to the local Qwen3 model to check Ollama is working.

Steps:
    1. ollama serve
    2. python scripts/check_ollama.py
"""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from marketmind.settings import load_config


def main() -> None:
    llm = load_config()["llm"]
    url = llm.get("ollama_url", "http://localhost:11434/api/chat")
    model = llm.get("ollama_model", "qwen3:4b")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
        "stream": False,
        "options": {"temperature": 0},
    }
    request = Request(
        url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
        answer = result.get("message", {}).get("content", "").strip()
        print("Ollama reachable: YES")
        print(f"Model: {model}")
        print(f"Response received: {bool(answer)}")
        print(f"Reply preview: {answer[:80]}")
    except HTTPError as exc:
        print(f"Ollama HTTP error: {exc.code}")
        print(exc.read().decode("utf-8", errors="replace")[:400])
    except (URLError, TimeoutError) as exc:
        print("Ollama reachable: NO")
        print(f"Reason: {exc}")


if __name__ == "__main__":
    main()

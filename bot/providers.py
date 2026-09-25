"""HTTP adapters for the supported provider protocols."""
import asyncio
import json
import urllib.error
import urllib.parse
import urllib.request
from .config import settings

class ProviderError(Exception):
    pass

def _post(url, headers, payload):
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", **headers}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        # Never expose a provider response body: some services echo user input.
        raise ProviderError(f"Provider returned HTTP {exc.code}.") from None
    except (urllib.error.URLError, TimeoutError):
        raise ProviderError("Provider connection timed out or failed.") from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ProviderError("Provider returned invalid JSON.") from None

def _generate(key, prompt):
    p, model, api_key, base = settings(key)
    if p.kind == "openai":
        headers = {"Authorization": "Bearer " + api_key} if api_key else {}
        data = _post(base + "/chat/completions", headers, {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 500})
        result = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if isinstance(result, list):
            result = "\n".join(item.get("text", "") for item in result if isinstance(item, dict))
    elif p.kind == "anthropic":
        data = _post(base + "/messages", {"x-api-key": api_key, "anthropic-version": "2023-06-01"}, {"model": model, "max_tokens": 500, "messages": [{"role": "user", "content": prompt}]})
        result = "\n".join(part.get("text", "") for part in data.get("content", []) if part.get("type") == "text")
    elif p.kind == "gemini":
        endpoint = base + "/models/" + urllib.parse.quote(model, safe="") + ":generateContent"
        data = _post(endpoint, {"x-goog-api-key": api_key}, {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": 500}})
        result = "\n".join(part.get("text", "") for candidate in data.get("candidates", [])[:1] for part in candidate.get("content", {}).get("parts", []) if "text" in part)
    else:
        raise ProviderError("Unknown provider protocol.")
    if not isinstance(result, str) or not result.strip():
        raise ProviderError("Provider returned no text (check the selected model and response policy).")
    return result.strip()

async def generate(key, prompt):
    return await asyncio.to_thread(_generate, key, prompt)

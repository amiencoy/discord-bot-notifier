"""Catalog, environment configuration, and copyable templates."""
from dataclasses import dataclass
import os
from urllib.parse import urlsplit

@dataclass(frozen=True)
class Provider:
    key: str
    label: str
    kind: str
    base: str
    needs_key: bool = True
    needs_base: bool = False

CATALOG = {
    p.key: p for p in (
        Provider("gpt", "GPT", "openai", "https://api.openai.com/v1"),
        Provider("claude", "Claude", "anthropic", "https://api.anthropic.com/v1"),
        Provider("gemini", "Gemini", "gemini", "https://generativelanguage.googleapis.com/v1beta"),
        Provider("mistral", "Mistral", "openai", "https://api.mistral.ai/v1"),
        Provider("grok", "Grok", "openai", "https://api.x.ai/v1"),
        Provider("llama", "Llama", "openai", "", False, True),
        Provider("local", "Local / OpenAI-compatible", "openai", "", False, True),
    )
}

def prefix(key: str) -> str:
    return "MODEL_" + key.upper()

def is_configured(key: str, env=None) -> bool:
    env = os.environ if env is None else env
    p = CATALOG[key]
    pre = prefix(key)
    if not env.get(pre + "_ID", "").strip():
        return False
    api_key = env.get(pre + "_API_KEY", "").strip()
    if p.needs_key and (not api_key or api_key.startswith("PASTE_YOUR_")):
        return False
    if p.needs_base and not env.get(pre + "_BASE_URL", "").strip():
        return False
    if p.needs_base:
        try:
            parsed = urlsplit(env[pre + "_BASE_URL"].strip())
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                return False
        except ValueError:
            return False
    return True

def settings(key: str, env=None):
    env = os.environ if env is None else env
    if not is_configured(key, env):
        raise ValueError("model hasn't been added")
    p = CATALOG[key]
    pre = prefix(key)
    base = env.get(pre + "_BASE_URL", p.base).strip().rstrip("/")
    parsed = urlsplit(base)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("invalid provider base URL")
    if parsed.scheme != "https" and key not in ("llama", "local"):
        raise ValueError("remote provider base URL must use HTTPS")
    return p, env[pre + "_ID"].strip(), env.get(pre + "_API_KEY", "").strip(), base

def template(key: str, model_id: str, base_url: str = "") -> str:
    p = CATALOG[key]
    pre = prefix(key)
    model_id = model_id.strip()
    if not model_id or any(c in model_id for c in "\r\n#=`\\"):
        raise ValueError("invalid model ID")
    rows = [f"{pre}_ID={model_id}"]
    if p.needs_key:
        rows.append(f"{pre}_API_KEY=PASTE_YOUR_{p.label.upper()}_API_KEY_HERE")
    elif key in ("llama", "local"):
        rows.append(f"{pre}_API_KEY=")  # Optional for authenticated local endpoints.
    if p.needs_base:
        base_url = base_url.strip() or "http://127.0.0.1:11434/v1"
        parsed = urlsplit(base_url)
        if any(c in base_url for c in "\r\n#=") or parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("invalid base URL")
        rows.append(f"{pre}_BASE_URL={base_url}")
    return "\n".join(rows)

import os
import tempfile
import unittest
from unittest.mock import patch

from bot.config import CATALOG, is_configured, template
from bot.providers import _generate
from bot.store import Store


class ConfigTests(unittest.TestCase):
    def test_templates_require_real_keys_and_local_url(self):
        for key in ("gpt", "claude", "gemini", "mistral", "grok"):
            snippet = template(key, "a-model")
            values = dict(line.split("=", 1) for line in snippet.splitlines())
            self.assertFalse(is_configured(key, values))
            values[f"MODEL_{key.upper()}_API_KEY"] = "secret"
            self.assertTrue(is_configured(key, values))
        values = dict(line.split("=", 1) for line in template("llama", "llama-test").splitlines())
        self.assertTrue(is_configured("llama", values))
        self.assertIn("local", CATALOG)

    def test_template_rejects_newlines_in_untrusted_inputs(self):
        with self.assertRaises(ValueError):
            template("gpt", "model\nDISCORD_BOT_TOKEN=stolen")
        with self.assertRaises(ValueError):
            template("local", "model", "http://localhost/v1\nTOKEN=bad")

class ProviderTests(unittest.TestCase):
    def test_all_adapters_route_and_parse(self):
        examples = {
            "gpt": ("chat/completions", {"choices": [{"message": {"content": "GPT OK"}}]}),
            "mistral": ("chat/completions", {"choices": [{"message": {"content": "Mistral OK"}}]}),
            "grok": ("chat/completions", {"choices": [{"message": {"content": "Grok OK"}}]}),
            "llama": ("chat/completions", {"choices": [{"message": {"content": "Llama OK"}}]}),
            "local": ("chat/completions", {"choices": [{"message": {"content": "Local OK"}}]}),
            "claude": ("/messages", {"content": [{"type": "text", "text": "Claude OK"}]}),
            "gemini": (":generateContent", {"candidates": [{"content": {"parts": [{"text": "Gemini OK"}]}}]}),
        }
        for key, (endpoint, response) in examples.items():
            with self.subTest(key=key):
                pre = f"MODEL_{key.upper()}"
                env = {pre + "_ID": "test-model", pre + "_API_KEY": "secret"}
                if key in ("llama", "local"):
                    env[pre + "_BASE_URL"] = "http://127.0.0.1:11434/v1"
                with patch.dict(os.environ, env, clear=True), patch("bot.providers._post", return_value=response) as post:
                    self.assertEqual(_generate(key, "ping"), f"{CATALOG[key].label.split(' / ')[0]} OK")
                    self.assertIn(endpoint, post.call_args.args[0])
                    self.assertEqual(post.call_args.args[2].get("model", "test-model"), "test-model")

class StateTests(unittest.TestCase):
    def test_per_guild_switches_and_recovery(self):
        with tempfile.TemporaryDirectory() as folder:
            s = Store(folder + "/state.sqlite3")
            s.turn(1, "gpt", True)
            self.assertTrue(s.enabled(1, "gpt"))
            self.assertFalse(s.enabled(2, "gpt"))
            s.alert(1, "gpt", "test_failure", True)
            self.assertTrue(s.alert(1, "gpt", "test_failure"))
            self.assertFalse(s.alert(1, "gpt", "recovered"))
            self.assertFalse(s.outcome(1, "gpt", False))
            self.assertTrue(s.outcome(1, "gpt", True))
            self.assertFalse(s.outcome(1, "gpt", True))

if __name__ == "__main__":
    unittest.main()

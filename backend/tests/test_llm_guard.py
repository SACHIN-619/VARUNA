"""The optional briefing LLM may only rephrase computed facts; invented numbers fall back to the template."""
import subprocess
import sys

from app.services import llm_provider as lp

FACTS = {"region_id": "IN_TELANGANA_DECCAN", "variable": "rainfall", "lead_hours": 48, "weather_regime": "NORMAL",
         "fused_value": 22.84, "dominant_model": "ECMWF_IFS", "dominant_weight_pct": 45.9, "probability": 1.0,
         "confidence": "HIGH", "disagreement_level": "LOW", "positive_factors": [], "negative_factors": []}


def test_number_guard():
    assert lp.invented_numbers("Fused 22.8 mm; ECMWF_IFS 45.9 % at 48 h.", FACTS) == []
    assert lp.invented_numbers("Expect 85 mm with a 60 % chance.", FACTS) == ["85", "60"]


class _Resp:
    status_code = 200

    def __init__(self, text):
        self._t = text

    def json(self):
        return {"choices": [{"message": {"content": self._t}}]}


class _Client:
    reply = ""

    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, *a, **k):
        return _Resp(_Client.reply)


def test_llm_output_with_invented_numbers_is_rejected(monkeypatch):
    monkeypatch.setattr(lp.httpx, "Client", _Client)
    p = lp.GrokLLMProvider(api_key="gsk_test", model="m")
    _Client.reply = "Blend is 22.8 mm, ECMWF_IFS carries 45.9 % weight."
    assert p.generate_briefing(dict(FACTS)) == _Client.reply
    _Client.reply = "Heavy rain of 150 mm is likely."
    out = p.generate_briefing(dict(FACTS, fused_value=22.85))
    assert "150" not in out and ("22.9" in out or "22.8" in out)


def test_groq_key_switches_endpoint():
    code = ("import os; os.environ['GROK_API_KEY']='gsk_x'; os.environ.pop('LLM_BASE_URL', None); "
            "os.environ.pop('GROK_MODEL', None); os.environ.pop('XAI_MODEL', None);"
            "from app.core.config import settings as s; print(s.LLM_BASE_URL, s.GROK_MODEL)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=".").stdout
    assert "api.groq.com" in out and "grok" not in out.split()[-1].lower()

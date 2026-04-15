from __future__ import annotations


class _DummyMessage:
    def __init__(self, content: str):
        self.content = content


class _DummyChoice:
    def __init__(self, content: str):
        self.message = _DummyMessage(content)


class _DummyResponse:
    def __init__(self, content: str):
        self.choices = [_DummyChoice(content)]


def test_ai_client_passes_extra_params_without_overriding_core(monkeypatch):
    import trendradar.ai.client as client_mod
    from trendradar.ai.client import AIClient

    captured = {}

    def fake_completion(**params):
        captured.update(params)
        return _DummyResponse("ok")

    monkeypatch.setattr(client_mod, "completion", fake_completion)

    client = AIClient(
        {
            "MODEL": "openai/gpt-4o-mini",
            "API_KEY": "k",
            "API_BASE": "http://127.0.0.1:8317/v1",
            "TEMPERATURE": 1.0,
            "EXTRA_PARAMS": {"top_p": 0.5, "temperature": 0.2},
        }
    )

    out = client.chat([{"role": "user", "content": "ping"}])
    assert out == "ok"

    # Extra param should be present
    assert captured.get("top_p") == 0.5

    # Core params should not be overridden by EXTRA_PARAMS
    assert captured.get("temperature") == 1.0

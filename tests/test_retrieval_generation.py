from unittest.mock import Mock

from ecommbot.retrieval_genreation import _invoke_with_fallback


def test_generation_uses_fallback_after_primary_failure():
    primary = Mock()
    primary.invoke.side_effect = RuntimeError("primary unavailable")
    fallback = Mock()
    fallback.invoke.return_value = "grounded fallback answer"
    payload = {"context": "review context", "question": "How is the battery?"}

    result, provider = _invoke_with_fallback(primary, fallback, payload)

    assert result == "grounded fallback answer"
    assert provider == "openrouter"
    primary.invoke.assert_called_once_with(payload)
    fallback.invoke.assert_called_once_with(payload)


def test_generation_does_not_call_fallback_when_primary_succeeds():
    primary = Mock()
    primary.invoke.return_value = "primary answer"
    fallback = Mock()
    payload = {"context": "review context", "question": "How is the battery?"}

    result, provider = _invoke_with_fallback(primary, fallback, payload)

    assert result == "primary answer"
    assert provider == "gemini"
    fallback.invoke.assert_not_called()

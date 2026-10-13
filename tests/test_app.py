from unittest.mock import Mock

import app


def test_chat_rejects_empty_question():
    client = app.app.test_client()

    response = client.post("/get", data={"msg": "   "})

    assert response.status_code == 400
    assert "Please enter a question" in response.get_json()["error"]


def test_chat_returns_answer_and_sources(monkeypatch):
    chain = Mock()
    chain.invoke.return_value = {
        "answer": "Customers generally praise the battery life.",
        "sources": [{"product_name": "Example Headset", "rating": 5}],
    }
    monkeypatch.setattr(app, "_chain", chain)
    client = app.app.test_client()

    response = client.post("/get", data={"msg": "How is the battery life?"})

    assert response.status_code == 200
    assert response.get_json() == {
        "answer": "Customers generally praise the battery life.",
        "sources": [{"product_name": "Example Headset", "rating": 5}],
    }


def test_chat_hides_unexpected_chain_errors(monkeypatch):
    chain = Mock()
    chain.invoke.side_effect = RuntimeError("secret provider details")
    monkeypatch.setattr(app, "_chain", chain)
    client = app.app.test_client()

    response = client.post("/get", data={"msg": "Tell me about the product"})

    assert response.status_code == 503
    assert response.get_json() == {
        "error": "The chatbot could not answer right now. Please try again."
    }

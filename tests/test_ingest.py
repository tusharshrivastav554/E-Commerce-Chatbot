import pytest

import ecommbot.ingest as ingest
from ecommbot.ingest import validate_configuration


def test_validate_configuration_requires_supabase_settings(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    with pytest.raises(ValueError, match="GOOGLE_API_KEY") as error:
        validate_configuration()

    message = str(error.value)
    assert "SUPABASE_URL" in message
    assert "SUPABASE_SERVICE_ROLE_KEY" in message


def test_validate_configuration_returns_supabase_settings(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")

    configuration = validate_configuration()

    assert configuration == {
        "GOOGLE_API_KEY": "test-google-key",
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
    }


def test_create_vector_store_uses_supabase_table_and_rpc(monkeypatch):
    fake_embedding = object()
    fake_client = object()
    fake_store = object()

    embedding_factory = lambda **kwargs: fake_embedding
    client_factory = lambda url, key: fake_client

    class FakeVectorStore:
        def __new__(cls, **kwargs):
            assert kwargs["client"] is fake_client
            assert kwargs["embedding"] is fake_embedding
            assert kwargs["table_name"] == "reviews"
            assert kwargs["query_name"] == "match_documents"
            return fake_store

    monkeypatch.setattr(ingest, "GoogleGenerativeAIEmbeddings", embedding_factory)
    monkeypatch.setattr(ingest, "create_client", client_factory)
    monkeypatch.setattr(ingest, "SupabaseVectorStore", FakeVectorStore)

    result = ingest._create_vector_store(
        {
            "GOOGLE_API_KEY": "google-key",
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "service-key",
        },
        table_name="reviews",
    )

    assert result is fake_store

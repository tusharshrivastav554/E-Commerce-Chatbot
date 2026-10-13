import os
from pathlib import Path
from typing import Iterable, Mapping, Optional, Union

from dotenv import load_dotenv

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_astradb import AstraDBVectorStore
from ecommbot.data_converter import dataconveter

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

REQUIRED_ENVIRONMENT = (
    "GOOGLE_API_KEY",
    "ASTRA_DB_API_ENDPOINT",
    "ASTRA_DB_APPLICATION_TOKEN",
    "ASTRA_DB_KEYSPACE",
)


def validate_configuration(
    required_variables: Iterable[str] = REQUIRED_ENVIRONMENT,
) -> Mapping[str, str]:
    """Validate service configuration before constructing external clients."""
    configuration = {name: os.getenv(name, "").strip() for name in required_variables}
    missing = [name for name, value in configuration.items() if not value]
    if missing:
        missing_names = ", ".join(missing)
        raise ValueError(
            "Missing required environment variable(s): "
            f"{missing_names}. Add them to .env before using Gemini or Astra DB."
        )
    return configuration


def _create_vector_store(
    configuration: Mapping[str, str],
    collection_name: str = "chatbotecomm",
):
    embedding = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=configuration["GOOGLE_API_KEY"],
    )
    return AstraDBVectorStore(
        embedding=embedding,
        collection_name=collection_name,
        api_endpoint=configuration["ASTRA_DB_API_ENDPOINT"],
        token=configuration["ASTRA_DB_APPLICATION_TOKEN"],
        namespace=configuration["ASTRA_DB_KEYSPACE"],
    )


def connect_to_vector_store(collection_name: str = "chatbotecomm"):
    """Connect to an existing Astra collection without loading or inserting data."""
    configuration = validate_configuration()
    return _create_vector_store(configuration, collection_name=collection_name)


def ingest_documents(
    csv_path: Optional[Union[str, os.PathLike]] = None,
    collection_name: str = "chatbotecomm",
):
    """Convert and insert source documents as an explicit ingestion operation."""
    configuration = validate_configuration()
    vstore = _create_vector_store(configuration, collection_name=collection_name)
    docs = dataconveter(csv_path)
    inserted_ids = vstore.add_documents(docs)
    return vstore, inserted_ids


def ingestdata(status=None):
    """Backward-compatible wrapper for the original status-based API.

    Existing callers passing a non-None status connect to the collection. The
    legacy ``None`` path still performs ingestion, but new code should call
    ``ingest_documents`` or ``connect_to_vector_store`` explicitly.
    """
    if status is None:
        return ingest_documents()
    return connect_to_vector_store()

if __name__ == '__main__':
    vstore, inserted_ids = ingest_documents()
    print(f"\nSuccessfully inserted {len(inserted_ids)} documents using text-embedding-004.")
    
    # Verification Search
    results = vstore.similarity_search("can you tell me the low budget sound basshead.")
    for res in results:
        print(f"* {res.page_content} [{res.metadata}]")

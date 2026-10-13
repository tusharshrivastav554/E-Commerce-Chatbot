import os
from pathlib import Path
from typing import Iterable, Mapping, Optional, Union

from dotenv import load_dotenv
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from supabase import create_client
from ecommbot.data_converter import dataconveter

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

REQUIRED_ENVIRONMENT = (
    "GOOGLE_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
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
            f"{missing_names}. Add them to .env before using Gemini or Supabase."
        )
    return configuration


def _create_vector_store(
    configuration: Mapping[str, str],
    table_name: str = "chatbotecomm",
):
    embedding = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=configuration["GOOGLE_API_KEY"],
        output_dimensionality=768,
    )

    supabase_client = create_client(
        configuration["SUPABASE_URL"],
        configuration["SUPABASE_SERVICE_ROLE_KEY"],
    )
    return SupabaseVectorStore(
        client=supabase_client,
        embedding=embedding,
        table_name=table_name,
        query_name="match_documents",
    )


def connect_to_vector_store(table_name: str = "chatbotecomm"):
    """Connect to an existing Supabase vector table without inserting data."""
    configuration = validate_configuration()
    return _create_vector_store(configuration, table_name=table_name)


def ingest_documents(
    csv_path: Optional[Union[str, os.PathLike]] = None,
    table_name: str = "chatbotecomm",
    batch_size: int = 20,
    batch_delay: float = 65.0,
):
    """Convert and insert source documents as an explicit ingestion operation.

    Documents are inserted in batches to stay within the free-tier embedding
    quota of 100 requests per minute for gemini-embedding-001.
    """
    import time

    configuration = validate_configuration()
    vstore = _create_vector_store(configuration, table_name=table_name)
    docs = dataconveter(csv_path)

    all_ids = []
    total = len(docs)
    for start in range(0, total, batch_size):
        batch = docs[start : start + batch_size]
        batch_num = start // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size
        print(f"Inserting batch {batch_num}/{total_batches} ({len(batch)} docs)...", flush=True)
        ids = vstore.add_documents(batch)
        all_ids.extend(ids)
        if start + batch_size < total:
            print(f"  Waiting {int(batch_delay)}s for rate-limit cooldown...", flush=True)
            time.sleep(batch_delay)

    return vstore, all_ids


def ingestdata(status=None):
    """Backward-compatible wrapper for the original status-based API.

    Existing callers passing a non-None status connect to the table. The
    legacy ``None`` path still performs ingestion, but new code should call
    ``ingest_documents`` or ``connect_to_vector_store`` explicitly.
    """
    if status is None:
        return ingest_documents()
    return connect_to_vector_store()

if __name__ == '__main__':
    vstore, inserted_ids = ingest_documents()
    print(f"\nSuccessfully inserted {len(inserted_ids)} documents into Supabase using gemini-embedding-001.")

    # Verification Search
    results = vstore.similarity_search("can you tell me the low budget sound basshead.")
    for res in results:
        print(f"* {res.page_content} [{res.metadata}]")


import logging
from pathlib import Path
from typing import Optional, Union

import pandas as pd
from langchain_core.documents import Document


logger = logging.getLogger(__name__)

DEFAULT_DATA_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "flipkart_product_review.csv"
)
REQUIRED_COLUMNS = {
    "product_id",
    "product_title",
    "rating",
    "summary",
    "review",
}


def _clean_value(value: object) -> str:
    """Return a CSV value as trimmed text without exposing pandas NaN values."""
    if pd.isna(value):
        return ""
    return str(value).strip()


def _normalise_rating(value: object) -> Optional[Union[int, float]]:
    """Keep ratings numeric when possible, while representing missing values as None."""
    if pd.isna(value):
        return None

    numeric_rating = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric_rating):
        return None

    numeric_rating = float(numeric_rating)
    return int(numeric_rating) if numeric_rating.is_integer() else numeric_rating


def dataconveter(csv_path: Optional[Union[str, Path]] = None):
    """Convert product reviews into metadata-rich LangChain documents.

    The default data path is resolved from this module's location, so callers do
    not need to start the process from a particular working directory. Rows with
    no customer review are skipped because they cannot provide retrieval context.
    """
    data_path = Path(csv_path) if csv_path is not None else DEFAULT_DATA_PATH
    try:
        product_data = pd.read_csv(data_path)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Product review CSV was not found: {data_path}") from exc

    missing_columns = REQUIRED_COLUMNS.difference(product_data.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Product review CSV is missing required column(s): {missing}")

    docs = []
    skipped_reviews = 0
    for _, row in product_data.iterrows():
        product_id = _clean_value(row["product_id"])
        product_name = _clean_value(row["product_title"])
        summary = _clean_value(row["summary"])
        review = _clean_value(row["review"])
        rating = _normalise_rating(row["rating"])

        if not review:
            skipped_reviews += 1
            continue

        rating_text = f"{rating}/5" if rating is not None else "Not provided"
        page_content = "\n".join(
            [
                f"Product: {product_name or 'Not provided'}",
                f"Rating: {rating_text}",
                f"Review summary: {summary or 'Not provided'}",
                f"Customer review: {review}",
            ]
        )
        metadata = {
            "product_id": product_id,
            "product_name": product_name,
            "rating": rating,
        }
        docs.append(Document(page_content=page_content, metadata=metadata))

    if skipped_reviews:
        logger.warning("Skipped %d product row(s) with an empty review", skipped_reviews)

    return docs

import pandas as pd
import pytest

from ecommbot.data_converter import dataconveter


def test_dataconveter_builds_metadata_rich_documents(tmp_path):
    csv_path = tmp_path / "reviews.csv"
    pd.DataFrame(
        [
            {
                "product_id": "p1",
                "product_title": "Example Headset",
                "rating": 5,
                "summary": "Good battery",
                "review": "The battery lasts all day.",
            },
            {
                "product_id": "p2",
                "product_title": "Empty Review",
                "rating": 3,
                "summary": "",
                "review": "",
            },
        ]
    ).to_csv(csv_path, index=False)

    documents = dataconveter(csv_path)

    assert len(documents) == 1
    assert "Product: Example Headset" in documents[0].page_content
    assert "Rating: 5/5" in documents[0].page_content
    assert "Review summary: Good battery" in documents[0].page_content
    assert documents[0].metadata == {
        "product_id": "p1",
        "product_name": "Example Headset",
        "rating": 5,
    }
    assert "nan" not in documents[0].page_content.lower()


def test_dataconveter_validates_required_columns(tmp_path):
    csv_path = tmp_path / "invalid.csv"
    pd.DataFrame([{"product_title": "Only title"}]).to_csv(csv_path, index=False)

    with pytest.raises(ValueError, match="missing required column"):
        dataconveter(csv_path)

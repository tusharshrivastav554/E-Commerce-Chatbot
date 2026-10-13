import logging
import os
from typing import Any, Mapping

from flask import Flask, jsonify, render_template, request


logger = logging.getLogger(__name__)

app = Flask(__name__)
_chain = None


def get_chain():
    """Create the retrieval chain on first use, rather than during module import."""
    global _chain
    if _chain is None:
        from ecommbot.ingest import connect_to_vector_store
        from ecommbot.retrieval_genreation import generation

        vector_store = connect_to_vector_store()
        _chain = generation(vector_store)
    return _chain


def _normalise_result(result: Any) -> dict[str, Any]:
    """Keep the HTTP contract stable if a legacy chain returns a plain string."""
    if isinstance(result, Mapping):
        answer = str(result.get("answer", "")).strip()
        sources = result.get("sources", [])
        if not isinstance(sources, list):
            sources = []
        return {"answer": answer, "sources": sources}
    return {"answer": str(result).strip(), "sources": []}


@app.route("/")
def index():
    return render_template("chat.html")


@app.route("/get", methods=["POST"])
def chat():
    question = request.form.get("msg", "").strip()
    if not question:
        return jsonify({"error": "Please enter a question about the available product reviews."}), 400

    try:
        result = get_chain().invoke(question)
    except Exception:
        logger.exception("Chat request failed")
        return jsonify({"error": "The chatbot could not answer right now. Please try again."}), 503

    response = _normalise_result(result)
    if not response["answer"]:
        return jsonify({"error": "The chatbot returned an empty answer. Please try again."}), 502
    return jsonify(response)


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "false").strip().lower() in {"1", "true", "yes"}
    app.run(debug=debug)

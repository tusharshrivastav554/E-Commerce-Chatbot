import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
# Replaced OpenAI with Google GenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from ecommbot.ingest import ingestdata

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

def generation(vstore):
    # Configure retriever to fetch the top 3 most relevant product snippets
    retriever = vstore.as_retriever(search_kwargs={"k": 3})

    PRODUCT_BOT_TEMPLATE = """
    You are an ecommerce product-review assistant. Answer the customer's question
    using only the supplied customer-review context. Do not invent or infer facts
    that are not present in the context, including price, stock, delivery,
    warranty, or technical specifications.

    Clearly distinguish review-based observations from verified facts. If the
    context does not answer the question, say that there is not enough information
    in the available customer reviews and explain what is missing instead of
    guessing. Keep the answer concise and customer-friendly.

    CONTEXT:
    {context}

    QUESTION: {question}

    YOUR ANSWER:
    """

    prompt = ChatPromptTemplate.from_template(PRODUCT_BOT_TEMPLATE)

    google_api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not google_api_key:
        raise ValueError(
            "Missing required environment variable: GOOGLE_API_KEY. "
            "Add it to .env before creating the Gemini generation chain."
        )

    # temperature=0.3 keeps the bot factual and consistent for e-commerce
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.3,
        google_api_key=google_api_key,
    )

    answer_chain = prompt | llm | StrOutputParser()

    def generate_result(question):
        documents = retriever.invoke(question)
        context = _format_context(documents)
        answer = answer_chain.invoke({"context": context, "question": question})
        return {"answer": answer, "sources": format_sources(documents)}

    return RunnableLambda(generate_result)


def _format_context(documents):
    """Label retrieved documents so the model can attribute its context."""
    context_parts = []
    for index, document in enumerate(documents, start=1):
        context_parts.append(f"[Source {index}]\n{document.page_content}")
    return "\n\n".join(context_parts) or "No relevant customer reviews were found."


def format_sources(documents):
    """Return compact, JSON-friendly evidence references for retrieved documents."""
    sources = []
    seen = set()
    for document in documents:
        metadata = getattr(document, "metadata", {}) or {}
        product_name = str(metadata.get("product_name", "")).strip()
        rating = metadata.get("rating")
        key = (product_name, rating)
        if key in seen:
            continue
        seen.add(key)

        source = {"product_name": product_name or "Unknown product"}
        if rating is not None and str(rating).strip():
            source["rating"] = rating

        excerpt = " ".join(str(getattr(document, "page_content", "")).split())
        if excerpt:
            source["review_excerpt"] = excerpt[:180].rstrip()
            if len(excerpt) > 180:
                source["review_excerpt"] += "..."
        sources.append(source)
    return sources

if __name__ == '__main__':
    # Load the existing Supabase vector store
    vstore = ingestdata("done")
    
    # Initialize the generation chain
    chain = generation(vstore)
    
    # Test query
    print(chain.invoke("can you tell me the best bluetooth buds?"))

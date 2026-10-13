# E-Commerce Product-Review Assistant

A lightweight retrieval-augmented generation (RAG) chatbot that answers customer questions using product reviews from a Flipkart-style CSV dataset.

The application combines:

- **Flask** for the web application and HTTP API.
- **LangChain** for document handling, retrieval, and chain orchestration.
- **Google Gemini** for text embeddings and answer generation.
- **Supabase** as the hosted Postgres/pgvector store.
- **Vanilla JavaScript and Bootstrap** for the browser chat interface.

The project is intentionally scoped as a practical proof of concept. It is not a live e-commerce catalog, an order-management system, or a personalized recommendation engine.

---

## Contents

- [What the application does](#what-the-application-does)
- [Architecture](#architecture)
- [Project structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Prepare the vector store](#prepare-the-vector-store)
- [Run the application](#run-the-application)
- [Using the chatbot](#using-the-chatbot)
- [HTTP API](#http-api)
- [Testing](#testing)
- [Data preparation details](#data-preparation-details)
- [Design decisions](#design-decisions)
- [Limitations](#limitations)
- [Troubleshooting](#troubleshooting)
- [Possible next improvements](#possible-next-improvements)

---

## What the application does

The chatbot lets a user ask questions such as:

- “What do customers say about the battery life?”
- “Which products are praised for strong bass?”
- “Are customers satisfied with the sound quality?”
- “What are the common complaints about this headset?”

For each question, the application:

1. Receives the question through the browser.
2. Searches the Supabase pgvector store for semantically relevant product-review documents.
3. Sends the retrieved context and question to Gemini 2.5 Flash.
4. Generates a concise answer grounded in the retrieved review context.
5. Displays lightweight evidence references containing product names and ratings.

The chatbot is instructed not to invent unsupported information such as current price, availability, delivery time, warranty, or technical specifications that are not present in the retrieved reviews.

---

## Architecture

### Ingestion flow

```text
data/flipkart_product_review.csv
                |
                v
       pandas CSV validation
                |
                v
    Metadata-enriched LangChain Documents
                |
                v
       Gemini text embeddings
                |
                v
       Supabase pgvector table
```

### Question-answering flow

```text
Browser question
        |
        v
Flask POST /get endpoint
        |
        v
Supabase semantic retriever, top 3 results
        |
        v
Grounded prompt + retrieved context
        |
        v
Gemini 2.5 Flash
        |
        v
JSON answer and evidence sources
        |
        v
Browser chat interface
```

### Runtime behavior

The application connects to the existing Supabase vector table lazily when the first question is submitted. Importing `app.py` does not automatically read or ingest the CSV. Ingestion is an explicit operation performed separately.

---

## Project structure

```text
E-Commerce-Chatbot-main/
├── app.py
├── requirements.txt
├── setup.py
├── .gitignore
├── data/
│   └── flipkart_product_review.csv
├── ecommbot/
│   ├── __init__.py
│   ├── data_converter.py
│   ├── ingest.py
│   └── retrieval_genreation.py
├── templates/
│   └── chat.html
├── static/
│   └── style.css
├── supabase/
│   └── schema.sql
├── tests/
│   ├── conftest.py
│   ├── test_app.py
│   ├── test_data_converter.py
│   └── test_ingest.py
└── notebook/
    └── trails.ipynb
```

### Important module responsibilities

| File | Responsibility |
|---|---|
| `app.py` | Flask app, web route, chat endpoint, response normalization, error handling |
| `ecommbot/data_converter.py` | Stable CSV path resolution, validation, cleaning, document creation |
| `ecommbot/ingest.py` | Environment validation, Gemini embeddings, Supabase connection, explicit ingestion |
| `ecommbot/retrieval_genreation.py` | Retriever, grounded prompt, Gemini generation, source formatting |
| `templates/chat.html` | Accessible chat UI, fetch request, loading state, safe text rendering |
| `static/style.css` | Chat layout and visual styling |
| `tests/` | Local tests that do not call real Gemini or Supabase services |

> Note: The existing module name `retrieval_genreation.py` contains the original spelling `genreation`. It is kept unchanged to avoid breaking imports.

---

## Prerequisites

- Python **3.10 or newer**.
- A Google AI/Gemini API key.
- A Supabase project with the pgvector extension available.
- A Supabase project URL and server-side service-role key.
- Network access to Google’s Gemini API and Supabase when ingesting or chatting.

The project can run its local unit tests without external API credentials, but real ingestion and chat requests require valid credentials.

---

## Installation

Open a terminal in the application directory:

```text
E:\something new\e commerce chat bot\E-Commerce-Chatbot-main\E-Commerce-Chatbot-main
```

### Windows PowerShell

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, you can run the virtual-environment interpreter directly:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

### macOS or Linux

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The `-e .` entry in `requirements.txt` installs the local `Ecommercebot` package in editable mode.

---

## Configuration

Create a file named `.env` in this directory:

```text
E-Commerce-Chatbot-main/.env
```

Use this template and replace each placeholder locally:

```dotenv
GOOGLE_API_KEY=your_google_gemini_api_key
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_server_only_service_role_key
FLASK_DEBUG=false
```

### Configuration variables

| Variable | Required for | Description |
|---|---|---|
| `GOOGLE_API_KEY` | Ingestion and chat | Google Gemini API authentication |
| `SUPABASE_URL` | Ingestion and chat | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Ingestion and chat | Server-only Supabase service-role key |
| `FLASK_DEBUG` | Optional | Enables Flask debug mode only when set to `true`, `1`, or `yes` |

Never commit `.env`, API keys, application tokens, or private service configuration. `.env` is already included in `.gitignore`.

The application validates the three required service variables before creating Gemini or Supabase clients. If a variable is missing, it raises an actionable configuration error rather than failing later with an opaque provider error.

### Service-role key security

`SUPABASE_SERVICE_ROLE_KEY` bypasses Supabase Row Level Security and must remain server-side. Do not place it in `templates/`, `static/`, browser JavaScript, public repositories, or client-side environment variables. The Flask backend uses it for ingestion and retrieval; the browser communicates only with the Flask `/get` endpoint.

---

## Prepare the Supabase vector store

The source dataset is located at:

```text
data/flipkart_product_review.csv
```

The ingestion module resolves this path relative to the project files, so it does not depend on the terminal’s current working directory.

### Inspect and ingest the dataset

From the project directory, run:

```powershell
python -m ecommbot.ingest
```

This operation:

1. Validates the required environment variables.
2. Reads and validates the CSV.
3. Converts usable rows into LangChain documents.
4. Creates Gemini embeddings using `models/text-embedding-004`.
5. Inserts the documents into the Supabase table named `chatbotecomm`.
6. Runs a small verification similarity search and prints the retrieved documents.

### Create the Supabase schema

Before ingestion, open the Supabase dashboard’s **SQL Editor** and run the contents of:

```text
supabase/schema.sql
```

The schema creates:

- The `vector` extension in the `extensions` schema.
- The `public.chatbotecomm` document table.
- A 768-dimensional embedding column for Gemini `text-embedding-004` embeddings.
- The `match_documents` RPC function required by LangChain’s `SupabaseVectorStore`.
- An HNSW cosine-similarity index.

The SQL function must return columns named `content`, `metadata`, and `similarity`. These names are used by the LangChain Supabase adapter when reconstructing retrieved `Document` objects.

### Required CSV columns

The converter expects these columns:

```text
product_id
product_title
rating
summary
review
```

Rows with an empty customer review are skipped because they do not provide useful retrieval context. Missing values in other fields are normalized so that the text does not contain the literal string `nan`.

### Important ingestion note

Ingestion is explicit and should normally be run once for a dataset and table. Running it repeatedly with the same data inserts duplicate rows unless you clear the table or add a separate deduplication strategy. If the dataset changes substantially, use a deliberate table refresh or a new table rather than repeatedly appending the same CSV.

The table name can be changed programmatically by calling:

```python
from ecommbot.ingest import ingest_documents

vector_store, inserted_ids = ingest_documents(
    table_name="my_product_reviews"
)
```

To use a different table, create the same table/function pattern from `supabase/schema.sql` and update the table name in the function call.

---

## Run the application

After the Supabase vector table has been populated:

```powershell
python app.py
```

Open the address shown by Flask, normally:

```text
http://127.0.0.1:5000/
```

The application does not ingest the CSV when it starts. It connects to the existing Supabase vector table only when the first question is submitted.

### Alternative Flask command

```powershell
flask --app app run
```

For local debugging only:

```powershell
$env:FLASK_DEBUG="true"
python app.py
```

Do not enable Flask debug mode for a publicly accessible deployment.

---

## Using the chatbot

Ask questions that can be answered from the available customer reviews:

- “What do customers say about the battery life?”
- “Which products have positive comments about bass?”
- “What are the common complaints?”
- “Is this headset comfortable according to the reviews?”

The interface displays:

- The generated answer.
- A loading status while the request is being processed.
- An error message if the request fails.
- An **Evidence used** section containing product names and ratings from the retrieved documents.

The interface does not claim that it has live product information. Questions about current price, stock, shipping, warranty, or orders should receive a limitation response because those fields are not part of the dataset.

---

## HTTP API

### `GET /`

Returns the browser chat page.

### `POST /get`

Accepts a form-encoded question:

```text
msg=What do customers say about the battery life%3F
```

Example PowerShell request:

```powershell
Invoke-RestMethod `
  -Uri http://127.0.0.1:5000/get `
  -Method Post `
  -Body @{ msg = "What do customers say about the battery life?" }
```

Successful response:

```json
{
  "answer": "Customers generally praise the battery life in the available reviews.",
  "sources": [
    {
      "product_name": "Example Headset",
      "rating": 5,
      "review_excerpt": "..."
    }
  ]
}
```

### Error responses

| Status | Meaning |
|---:|---|
| `400` | The submitted question is empty or missing |
| `502` | The generation chain returned an empty answer |
| `503` | A runtime or external-provider failure occurred |

Provider exception details are logged server-side and are not exposed to the browser.

---

## Testing

Install the dependencies first, then run:

```powershell
pytest -q
```

The current tests cover:

- Metadata-enriched document creation.
- Required CSV-column validation.
- Handling of missing/empty review content.
- Empty chat-question validation.
- Successful API response shape.
- Controlled handling of retrieval-chain failures.

The tests mock the chatbot chain and use temporary CSV fixtures. They do not call Gemini or Supabase, so they can run without credentials or network access.

### Syntax check

```powershell
python -m compileall -q app.py ecommbot tests
```

### Local data-conversion smoke check

```powershell
python -c "from ecommbot.data_converter import dataconveter; docs = dataconveter(); print(len(docs)); print(docs[0].metadata)"
```

### Real provider smoke test

With a valid `.env`, the Supabase schema applied, and an accessible Supabase project, run the ingestion command and then submit a browser question. This is separate from the automated test suite because it depends on external services, credentials, quotas, and network availability.

---

## Data preparation details

Each usable CSV row is converted into a document with labeled content similar to:

```text
Product: BoAt Rockerz 235v2 with ASAP charging Version 5.0 Bluetooth Headset
Rating: 5/5
Review summary: Terrific purchase
Customer review: The bass is very high and the battery backup is good...
```

The document metadata contains:

```json
{
  "product_id": "ACCFZGAQJGYCYDCM",
  "product_name": "BoAt Rockerz 235v2 with ASAP charging Version 5.0 Bluetooth Headset",
  "rating": 5
}
```

This design keeps important structured fields available for evidence display while also placing them in the embedded text so semantic retrieval can use the product title and rating context.

---

## Design decisions

### Why RAG instead of fine-tuning?

The reviews are external knowledge that may change. RAG allows the application to update the searchable content by ingesting new documents without retraining a language model.

### Why Supabase?

Supabase provides hosted Postgres with pgvector support, a familiar relational data model, and an SQL-defined retrieval function. This makes the document store and similarity-search contract explicit while keeping the project relevant to cloud data ecosystems and client-facing GenAI implementations.

### Why top-3 retrieval?

The chatbot uses the three most relevant review documents as a small context window. This keeps the proof of concept simple and limits unrelated context. A production system should evaluate different values of `k` using a labeled question set rather than choosing one solely by intuition.

### Why lazy application startup?

The Flask module can be imported for tests and route inspection without immediately requiring live provider credentials or opening external connections. The vector store and generation chain are created on first use.

### Why show sources?

Source references make the answer easier to inspect and demonstrate an important RAG property: the response should be traceable to retrieved information rather than appearing as an unsupported model output.

---

## Limitations

This project should be described accurately as a focused RAG proof of concept.

- It is not a live product catalog.
- It does not retrieve current prices or stock availability.
- It does not support orders, payments, returns, or user accounts.
- It does not maintain multi-turn conversation memory; each question is handled independently.
- It does not provide statistically validated product rankings.
- It does not personalize recommendations to a user’s profile.
- It relies on the quality, coverage, and bias of the review dataset.
- It does not yet include a formal retrieval precision/recall evaluation set.
- Repeated ingestion may create duplicate documents in the Supabase vector table.
- Real requests depend on external Gemini and Supabase credentials, connectivity, quotas, and service availability.

---

## Troubleshooting

### `ModuleNotFoundError`

Make sure the virtual environment is active and dependencies are installed:

```powershell
python -m pip install -r requirements.txt
```

Confirm that the terminal is using the expected interpreter:

```powershell
python -c "import sys; print(sys.executable)"
```

### Missing environment-variable error

Check that `.env` exists in the same directory as `app.py` and contains all three required service variables:

```text
GOOGLE_API_KEY
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
```

Do not add quotes unless they are intentionally part of the value, and do not include extra spaces around the assignment.

### Supabase connection failure

Check:

1. `SUPABASE_URL` is the project URL, not a dashboard URL.
2. `SUPABASE_SERVICE_ROLE_KEY` is active and is being used only by the backend.
3. The SQL in `supabase/schema.sql` has been executed successfully.
4. The `public.chatbotecomm` table and `public.match_documents` function exist.
5. The embedding column is `extensions.vector(768)`, matching `text-embedding-004`.
6. The machine can reach Supabase over the network.

### Chat starts but returns a provider error

Check the terminal output for the server-side traceback. Common causes include:

- An invalid or expired Google API key.
- Gemini quota or model access restrictions.
- A missing Supabase table or `match_documents` function.
- A network or TLS issue.
- Incorrect environment-variable values.

The browser intentionally receives only a general retry message rather than private provider details.

### No useful answer for a product question

The answer depends on the retrieved review context. Try a question that matches the available fields, such as battery life, bass, sound quality, comfort, or common complaints. Questions about live business data cannot be answered from this dataset.

### Duplicate documents after ingestion

The current ingestion function adds the converted documents to the selected Supabase table. Do not repeatedly run ingestion against the same table unless duplicate data is acceptable. To clear the default table before a deliberate reload, run this in the Supabase SQL Editor:

```sql
truncate table public.chatbotecomm restart identity;
```

---

## Possible next improvements

1. Add a small labeled evaluation set for retrieval quality and grounded-answer behavior.
2. Add a deterministic deduplication or table-refresh workflow for repeated ingestion.
3. Add optional conversation history with a clear context-length limit.
4. Add structured filtering by rating or product ID.
5. Add a proper product catalog source for price and availability.
6. Add observability for latency, retrieval count, and provider errors without logging private user data.
7. Add deployment configuration after the local workflow is stable.

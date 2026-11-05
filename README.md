# Trip Planning RAG Assistant

A Retrieval-Augmented Generation (RAG) application for discovering hotels, destinations, parks, and trip-planning information across Kenya. The project combines web-sourced travel data, semantic search, and LLM-based generation to answer user questions in a grounded and source-aware way.

## Features

- Ask questions about Kenyan destinations and travel planning.
- Retrieve relevant content using sentence embeddings and a vector store.
- Return answers with source references and URLs.
- Use the web interface or the FastAPI endpoint.
- Process tourism content from Magical Kenya and Kenya Wildlife Service (KWS) sources.

## Overview

The project ingests content from official tourism and wildlife websites, parses it into structured records, chunks it into retrievable segments, embeds those chunks using a sentence transformer, and stores them in a vector database. When a user asks a question, the system retrieves the most relevant chunks and passes them to a model for answer generation.

This project includes:
- A Python-based knowledge pipeline
- A RAG retrieval layer with ChromaDB
- A FastAPI backend
- A lightweight browser frontend
- Local data generation folders for raw HTML and processed embeddings

## File and Folder Structure

```text
Hotel-Discovery-and-Trip-Planning-RAG-Assistant/
├── app/
│   └── config.py                 # Shared project configuration and destination source lists
├── frontend/
│   ├── app.js                    # Frontend logic for communicating with the backend
│   ├── index.html                # User interface
│   ├── styles.css                # UI styling
│   └── assets/                   # Static assets
├── src/
│   ├── KWS/
│   │   ├── PageDownload.py       # Downloads KWS park pages
│   │   └── kws_parser.py         # Parses KWS HTML into structured JSON
│   ├── MagicalKenya/
│   │   ├── Parser.py             # Parses Magical Kenya destination pages
│   │   └── RawPageDownload.py    # Downloads source pages
│   └── rag/
│       ├── chunking.py           # Chunking logic for Magical Kenya documents
│       ├── kws_chunking.py       # Chunking logic for KWS content
│       ├── rag.py                # Retrieval + LLM answer generation
│       └── vector_store.py       # ChromaDB embedding and similarity search functions
├── .gitignore                    # Ignores local data, env files, and generated artifacts
├── main.py                       # End-to-end pipeline: parse -> chunk -> embed -> query
├── server.py                     # FastAPI app that runs the backend API and serves frontend
├── README.md                     # Project documentation
├── raw/                          # Downloaded HTML source pages (not committed)
├── Data/                         # Generated processed files and vector database (not committed)
├── .env                          # Local API key config (not committed)
└── .venv/                        # Local Python environment (not committed)
```

## How the Project Works

1. Source pages are downloaded from Magical Kenya and Kenya Wildlife Service (KWS).
2. HTML content is parsed into structured JSON.
3. Documents are chunked into smaller segments for retrieval.
4. Chunks are embedded into vectors using Sentence Transformers.
5. ChromaDB stores and retrieves relevant chunks using semantic similarity.
6. The user question is matched against the vector store.
7. The most relevant chunks are sent to a model alongside the user question.
8. The model answers using only the retrieved context, with source references returned to the frontend.

## Tech Stack

- **Python** - data processing and backend application
- **FastAPI** - HTTP API and frontend serving
- **Uvicorn** - ASGI server
- **ChromaDB** - persistent vector storage and similarity search
- **Sentence Transformers** - text embeddings
- **NVIDIA API** - language-model answer generation through an OpenAI-compatible client
- **HTML parsing tools** - extraction of structured content from downloaded pages
- **JavaScript, HTML, and CSS** - browser-based user interface
- **JSON and JSONL** - processed documents and chunks

## Setup

### Requirements

- Python 3.10 or newer
- [`uv`](https://docs.astral.sh/uv/) for dependency management
- An NVIDIA API key
- The source HTML files required by the data-processing pipeline

Install the dependencies from the project root:

```bash
uv sync
```

Create a `.env` file in the project root:

```env
NVIDIA_API_KEY=your_nvidia_api_key
```

## Prepare the Data

The processing pipeline expects the source HTML files in the locations configured by the project. Make sure the required Magical Kenya and KWS source files are available before running it.

**NOTE: The Magical kenya and KWS raw page downloaders are not included in the main.py to avoid scrapping limits and allow for as many executions as possible for the existing pipeline using already saved raw.html files
**
Run the following to download the raw.html files:

1. Download raw Magical Kenya html files. From the directory /src/MagicalKenya run: 
```bash
uv run python RawPageDownload.py
```
2. Download raw KWS html files. From the location /src/KWS run:
```bash
uv run python PageDownload.py
```
## Configuration

- `NVIDIA_API_KEY` - required for model access.
- The embedding model, vector-store path, collection name, and source-data paths are configured in the project code.

Run the pipeline:

```bash
uv run python main.py
```

The pipeline parses available HTML, creates document chunks, and builds or updates the vector store. It also starts a command-line question loop when processing completes. Type `exit` or `quit` to leave it.

<img width="2202" height="962" alt="image" src="https://github.com/user-attachments/assets/cd4ad321-e8b0-4f42-bbd4-3292e14f77ae" />


## Run the Web Application
> The API server expects a populated vector store. If the required source files have not been processed, the server may fail to start because the collection is empty.

Start the FastAPI server:

```bash
uv run python server.py
```

Open the application at [http://127.0.0.1:8080](http://127.0.0.1:8080).

<img width="2529" height="1191" alt="image" src="https://github.com/user-attachments/assets/ffacd4a6-ef52-4290-a19d-ad0215c60e21" />

FastAPI's interactive API documentation is available at [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs).

<img width="1917" height="1047" alt="image" src="https://github.com/user-attachments/assets/84c0ee12-c081-4d68-951f-98fd77c9cbd3" />

<img width="1181" height="1051" alt="image" src="https://github.com/user-attachments/assets/6851e47b-80b2-45ab-83a4-c108c8194fb6" />

<img width="1185" height="1390" alt="image" src="https://github.com/user-attachments/assets/a9da50f9-7aef-4d38-9b93-c53141eed96f" />

## API

### Health check

```http
GET /api/health
```
<img width="2032" height="400" alt="image" src="https://github.com/user-attachments/assets/3a23dd46-fa73-4a89-8d7b-127afa66a040" />

### Ask a question

```http
POST /api/ask
Content-Type: application/json
```

Example request:

```bash
curl -X POST http://127.0.0.1:8080/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are some places to visit in Kenya?",
    "n_results": 5
  }'
```
<img width="2456" height="536" alt="image" src="https://github.com/user-attachments/assets/f49f767e-3762-42f4-8413-db1f0bb593cd" />


The response contains an `answer` and a list of `sources`. Each source may include a reference, destination, section, source URL, and retrieval distance.

## Conclusion

The project demonstrates how retrieval-augmented generation can be leveraged to make travel information easier to find and use. Since answers depend on the locally collected source data, keep that data up to date and confirm time-sensitive details—such as park fees and entry rules—with the relevant official sources before travelling.



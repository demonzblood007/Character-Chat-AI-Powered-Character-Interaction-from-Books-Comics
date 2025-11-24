# Character Chat – AI-Powered Character Interaction from Books/Comics

FastAPI + LangChain service that transforms PDF books and comics into fully-interactive character agents. Upload any book or comic, and the worker pipeline automatically extracts characters, builds a knowledge graph (Neo4j), creates a vector store (Qdrant), and enables natural conversations with every character through a retrieval-augmented generation (RAG) interface.

## Highlights
- End-to-end ingestion pipeline (PDF ➜ chunks ➜ embeddings ➜ character graph)
- Secure multi-tenant APIs (per-user headers, file isolation, chat history persistence)
- Background processing via Redis/RQ workers with retry + monitoring hooks
- Streaming and non-streaming chat endpoints with contextual memory

## Architecture
- **FastAPI** (`app/server.py`): upload endpoints, chat APIs, and health checks
- **Worker pipeline** (`app/workers_queue/workers.py`): LangGraph workflow that validates PDFs, extracts characters, stores graph data, and seeds Qdrant
- **Data stores**
  - MongoDB: file metadata + chat sessions
  - Neo4j: character graph and relationships
  - Qdrant: semantic chunks used for retrieval
  - Redis: job queue backend for RQ
- **LangChain / LangGraph**: orchestrate LLM + embedding calls with OpenAI (or compatible) models

## Project Layout
```
├── app/
│   ├── db/                # Mongo helpers + collections
│   ├── utils/             # Async file helpers
│   └── workers_queue/     # Redis queue + worker pipeline
├── tests/                 # End-to-end happy-path test suite
├── env.example            # Copy to .env and configure
├── requirements.txt       # Python dependencies
└── README.md
```

## Prerequisites
- Python 3.11+
- Running services: MongoDB, Redis, Neo4j, Qdrant
- OpenAI (or OpenAI-compatible) API keys for both chat + embedding models

You can spin up the backing services via Docker (preferred) or point the app to cloud instances—only the Python process lives on your machine.

## Setup
```bash
git clone https://github.com/<you>/character_chat.git
cd character_chat
python -m venv .venv && source .venv/bin/activate  # PowerShell: .venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
cp env.example .env
```

Edit `.env` (or export the variables) with at least:

| Variable | Purpose |
| --- | --- |
| `LLM_API_KEY` / `EMBEDDING_API_KEY` | Provider credentials |
| `MONGODB_URI` / `MONGODB_DB` | Mongo connection + database name |
| `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | Neo4j auth |
| `QDRANT_HOST`, `QDRANT_PORT` | Vector database endpoint |
| `REDIS_HOST`, `REDIS_PORT` | Job queue |
| `UPLOAD_ROOT` | Where PDFs are stored locally (defaults to `./uploads`) |

Advanced controls: `LLM_MODEL`, `EMBEDDING_MODEL`, `CHUNK_SIZE`, `RAG_RETRIEVAL_K`, `VECTOR_SIZE`, etc. See `env.example` for the full list.

## Running the stack
1. **Bootstrap data stores** (example using Docker):
   ```bash
   docker run -d --name mongo -p 27017:27017 mongo:7
   docker run -d --name redis -p 6379:6379 redis:7
   docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:5
   docker run -d --name qdrant -p 6333:6333 qdrant/qdrant:latest
   ```
2. **Start the API**
   ```bash
   uvicorn app.server:app --reload
   # http://localhost:8000/docs for OpenAPI
   ```
3. **Run the worker**
   ```bash
   # Ensure the project root is on PYTHONPATH so RQ can import app.*
   set PYTHONPATH=%cd%        # PowerShell / CMD on Windows
   export PYTHONPATH=$PWD     # macOS/Linux
   rq worker default --with-scheduler
   ```
   The worker consumes jobs enqueued by `/upload`, processes PDFs, updates Mongo, Neo4j, and Qdrant, and emits progress logs.

## Testing
The E2E test simulates the happy path (upload ➜ processing ➜ chat). It requires all backing services plus real API keys.
```bash
pytest tests/test_e2e.py -v
```
Environment knobs for the test runner:
- `API_BASE_URL` (default `http://localhost:8000`)
- `TEST_USER_ID` (defaults to `demo-user`)

## Key API Endpoints
- `POST /upload` – upload PDF with header `X-User-ID`
- `GET /files`, `/files/{id}` – check processing status
- `GET /characters?file_id=` – list extracted characters
- `GET /characters/{name}` – detailed profile + relationships
- `POST /chat` – blocking character chat (body must include `user_id`, `character_name`, `message`)
- `POST /chat/stream` – SSE stream of the chat response
- `GET/DELETE /chat/history` – inspect or reset stored conversations

All user-facing endpoints require the `X-User-ID` header; responses are scoped to the supplied user.

## Troubleshooting
- Verify `/health` before uploading; it pings Mongo, Neo4j, Qdrant, and Redis.
- If background jobs appear stuck, make sure Redis is reachable and the worker logs show “Listening for jobs”.
- Uploaded files land under `UPLOAD_ROOT/<user>/<file_id>/`—clear this folder if you need to reclaim disk space.

Happy hacking! If you build on top of this project, keep the single README pattern—document your changes here so reviewers can understand the work quickly.
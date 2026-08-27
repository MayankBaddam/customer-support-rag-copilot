# Customer Support RAG Copilot

A full-stack personal portfolio project that demonstrates secure document ingestion, semantic
retrieval, and grounded answer generation for a fictional customer-support workspace. Support agents
can upload approved knowledge documents, inspect deterministic chunks, search embedded evidence, and
ask a Gemini-powered copilot for answers with server-verified citations.

This is an independent engineering project built with fictional data. It is not a client project and
is not connected to a production helpdesk.

[Live demo](https://customer-support-rag-copilot-btsyg2qbm-goblin2.vercel.app) ·
[GitHub repository](https://github.com/MayankBaddam/customer-support-rag-copilot)

## Highlights

- Supabase Auth protects the workspace and backend APIs.
- PDF, Markdown, and TXT documents are validated, stored privately, extracted, cleaned, and chunked.
- Gemini `gemini-embedding-001` produces 768-dimensional embeddings stored in PostgreSQL with pgvector.
- Owner-scoped cosine search returns only completed documents belonging to the authenticated user.
- Gemini generates single-turn answers from retrieved context and abstains when evidence is missing.
- Citations are assembled from retrieved database rows rather than trusted from model output.
- Structured errors and request logs avoid tokens, API keys, prompts, embeddings, and document bodies.
- Backend and frontend regression suites cover authentication, ingestion, retrieval, answers, and UI states.

## Screenshots

### Knowledge Base

Uploaded documents, ingestion status, chunk counts, and document actions are available from one
owner-scoped workspace.

![Knowledge Base document list](docs/screenshots/01-knowledge-base.png.png)

### Grounded Copilot answer

The single-turn Copilot answers from retrieved knowledge and displays the supporting document and
chunk citations returned by the backend.

![Grounded Copilot answer with citations](docs/screenshots/02-copilot-answer.png.png)

### Retrieval Debug

The retrieval interface exposes ranked evidence, metadata, similarity scores, and latency without
exposing embedding vectors.

![Retrieval Debug interface](docs/screenshots/03-retrieval-debug.png.png)

### Evaluation and dashboard surfaces

The evaluation view is an intentionally labeled placeholder for future benchmark reporting; it does
not claim completed evaluation results. Dashboard summary values illustrate the workspace UI and are
not presented as production analytics.

![Evaluation placeholder](docs/screenshots/04-evaluation.png.png)

![Workspace dashboard](docs/screenshots/05-dashboard.png.png)

## Architecture

```mermaid
flowchart LR
    Agent["Support agent"] --> UI["Next.js frontend"]
    UI -->|"Supabase session"| Auth["Supabase Auth"]
    UI -->|"Bearer token + JSON/multipart"| API["FastAPI backend"]
    API -->|"Validate token"| Auth
    API --> DB["Supabase PostgreSQL"]
    DB --> Vector["pgvector embeddings + HNSW cosine index"]
    API --> Storage["Private Supabase Storage"]
    API --> Gemini["Gemini embeddings + grounded answers"]
    API --> Routes

    subgraph Backend
        Routes["API routes"] --> Services["Application services"]
        Services --> Repositories["SQLAlchemy repositories"]
        Services --> Providers["Storage / embedding / answer adapters"]
    end
```

The browser receives only the Supabase URL, anonymous key, and public API URL. Database credentials,
the Supabase secret key, and the Gemini API key remain in the backend environment.

## End-to-end workflow

```mermaid
flowchart TD
    Upload["Upload PDF, Markdown, or TXT"] --> Validate["Validate title, extension, MIME, and 5 MiB limit"]
    Validate --> PrivateStore["Store original in private Supabase bucket"]
    PrivateStore --> Process["Extract and normalize text"]
    Process --> Chunk["Deterministic chunks: ~500 tokens, ~75 overlap"]
    Chunk --> Embed["Generate 768-d Gemini embeddings"]
    Embed --> Persist["Store chunks and vectors in PostgreSQL/pgvector"]
    Question["Authenticated question"] --> QueryVector["Generate query embedding"]
    QueryVector --> Retrieve["Owner-scoped cosine search over completed documents"]
    Persist --> Retrieve
    Retrieve --> Enough{"Retrieved chunks available?"}
    Enough -->|"Yes"| Context["Top-k chunk content + source metadata"]
    Context --> Answer["Gemini grounded-answer instruction"]
    Answer --> Cite["Return answer + server-built citations"]
    Enough -->|"No"| Abstain["Return insufficient-knowledge message"]
```

## How the RAG pipeline works

### Document ingestion

Uploads are authenticated and restricted to `application/pdf`, `text/markdown`, and `text/plain`,
with a maximum size of 5 MiB. The backend sanitizes filenames, calculates a SHA-256 checksum,
generates an owner/document storage path, and writes the original file to the configured private
Supabase Storage bucket. Duplicate active content is rejected per owner.

Processing transitions documents through `pending -> processing -> completed` or `failed`. PDF
extraction preserves page numbers, Markdown retains headings and lists, and plain text is supported
directly. Failures are sanitized, partial chunk writes roll back, and failed documents can be safely
reprocessed.

### Cleaning and chunking

The ingestion pipeline normalizes whitespace and null characters while preserving paragraphs,
punctuation, headings, lists, and support error codes. Chunking is deterministic, targets roughly
500 tokens with roughly 75 tokens of overlap, handles oversized paragraphs, and never creates empty
chunks. Metadata carries the document ID, source filename, section title, and PDF page where available.

### Embeddings

The provider-independent embedding contract supports document batches and query embeddings. The
Gemini adapter requests `gemini-embedding-001` with output dimensionality 768 and validates every
response before persistence. Embeddings are stored in `document_chunks.embedding vector(768)` and
indexed with HNSW cosine operations. Existing vectors are not overwritten unless force mode is
explicitly requested.

Backfill is explicit and idempotent; it never runs during startup or migrations:

```powershell
cd backend
python -m app.embedding_backfill --dry-run
python -m app.embedding_backfill
```

### Retrieval

`POST /api/v1/copilot/search` embeds a non-empty query of at most 1,000 characters and accepts
`top_k` from 1 through 10. PostgreSQL ranks embedded chunks by cosine distance. The repository joins
their parent documents and filters by authenticated owner, completed status, and non-null embedding.
Archived, pending, processing, and failed documents are excluded. Embedding vectors are never
returned by the API.

### Grounded answers and citations

`POST /api/v1/copilot/answer` reuses the same owner-scoped retrieval service. Only retrieved chunk
content and source metadata are sent to the answer provider. The system instruction requires answers
from supplied context and prohibits invented policies, prices, dates, and procedures. With no useful
evidence, the service returns:

> The knowledge base does not contain enough information to answer this question.

Citations come from retrieved rows and include document title, original filename, chunk ID, section,
page number, and similarity score. The response never exposes prompts, access tokens, API keys, or
embedding vectors.

## Technology stack

| Area | Technology |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript |
| Client data and authentication | TanStack Query, Supabase JavaScript client |
| Styling | Application CSS in `frontend/app/globals.css` |
| Backend | Python 3.12, FastAPI, Uvicorn, Pydantic |
| Persistence | SQLAlchemy, Alembic, Supabase PostgreSQL |
| Vector search | pgvector, HNSW index, cosine distance |
| Storage and identity | Private Supabase Storage, Supabase Auth |
| AI provider | Google Gen AI SDK, Gemini embeddings and answer generation |
| Document parsing | pypdf plus Markdown/plain-text extractors |
| Testing | Pytest, Vitest, Testing Library |
| Deployment targets | Vercel frontend, Render or Railway backend, Supabase managed services |

## Project structure

```text
customer-support-rag-copilot/
|-- backend/
|   |-- alembic/                 # PostgreSQL and pgvector migrations
|   |-- app/
|   |   |-- api/v1/              # Auth, ticket, document, copilot, system routes
|   |   |-- core/                # Settings, safe errors, structured logging
|   |   |-- database/            # SQLAlchemy session management
|   |   |-- models/              # Profiles, tickets, documents, chunks
|   |   |-- repositories/        # Ticket, embedding, semantic-search queries
|   |   |-- services/            # Auth, ingestion, embeddings, retrieval, answers
|   |   `-- embedding_backfill.py
|   |-- tests/
|   |-- Dockerfile
|   `-- pyproject.toml
|-- frontend/
|   |-- app/                      # Next.js routes
|   |-- components/               # Auth, tickets, documents, retrieval, copilot UI
|   |-- hooks/                    # TanStack Query hooks
|   |-- lib/                      # API, Supabase, and validation clients
|   |-- tests/
|   `-- package.json
|-- docs/                         # Deployment and Supabase notes
|-- evaluation/datasets/          # Fictional support data
|-- knowledge-base/               # Example fictional knowledge documents
|-- .env.example
`-- README.md
```

## Local setup

### Prerequisites

- Python 3.12+
- Node.js 22+ and npm
- A Supabase project with PostgreSQL, Auth, and a private Storage bucket
- A Gemini API key

### Clone and configure Supabase

```bash
git clone https://github.com/MayankBaddam/customer-support-rag-copilot.git
cd customer-support-rag-copilot
```

Enable the `vector` extension, create a private bucket named `knowledge-documents`, enable the desired
Supabase Auth sign-in method, and add `http://localhost:3000` to the allowed Auth redirect URLs.
Use the pooled PostgreSQL URL for application traffic and the direct URL for Alembic migrations.
See [`docs/supabase.md`](docs/supabase.md) and [`docs/deployment.md`](docs/deployment.md).

### Backend environment

Copy `backend/.env.example` to `backend/.env` and replace placeholders locally:

```env
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3000
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@POOLER_HOST:6543/postgres
MIGRATION_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@DIRECT_HOST:5432/postgres
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=replace_me
SUPABASE_SECRET_KEY=replace_me
SUPABASE_STORAGE_BUCKET=knowledge-documents
GEMINI_API_KEY=replace_me
EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIMENSION=768
```

Do not place `SUPABASE_SECRET_KEY`, `GEMINI_API_KEY`, or database URLs in frontend variables.

### Run the backend

From `backend`:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

macOS or Linux:

```bash
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

Backend URLs:

- API documentation: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`
- Dependency readiness: `http://localhost:8000/ready`

### Frontend environment and startup

Copy `frontend/.env.example` to `frontend/.env.local` and replace placeholders:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=replace_me
```

Then run:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` and sign in with a Supabase Auth user.

### Tests and production build

```powershell
cd backend
python -m pytest -q
```

```bash
cd frontend
npm run lint
npm run typecheck
npm run test
npm run build
```

## API examples

All document and copilot routes require `Authorization: Bearer <ACCESS_TOKEN>`.

### Health

```http
GET /health
```

```json
{
  "status": "ok",
  "service": "customer-support-rag-backend"
}
```

### Upload, process, and embed a document

```bash
curl -X POST "http://localhost:8000/api/v1/documents" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F "title=Account Recovery" \
  -F "file=@knowledge-base/account-recovery.md;type=text/markdown"

curl -X POST "http://localhost:8000/api/v1/documents/<DOCUMENT_ID>/process" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"

curl -X POST "http://localhost:8000/api/v1/documents/<DOCUMENT_ID>/embed" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

### Semantic search

```http
POST /api/v1/copilot/search
Authorization: Bearer <ACCESS_TOKEN>
Content-Type: application/json

{
  "query": "How long does a password recovery link remain valid?",
  "top_k": 5
}
```

The response includes request ID, retrieval latency, embedding model, evidence status, and ranked
chunks with document metadata and similarity scores. It does not include vectors.

### Grounded answer

```http
POST /api/v1/copilot/answer
Authorization: Bearer <ACCESS_TOKEN>
Content-Type: application/json

{
  "query": "How long does a password recovery link remain valid?",
  "top_k": 5
}
```

```json
{
  "answer": "A grounded answer based on the retrieved knowledge documents.",
  "citations": [
    {
      "chunk_id": "00000000-0000-0000-0000-000000000000",
      "document_title": "Account Recovery",
      "original_filename": "account-recovery.md",
      "section_title": "Recovery links",
      "page_number": null,
      "similarity_score": 0.91
    }
  ],
  "retrieved_chunks": 1
}
```

### Endpoint overview

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Process health check |
| `GET` | `/ready` | Application/database readiness |
| `GET` | `/api/v1/auth/me` | Authenticated profile |
| `GET`, `POST` | `/api/v1/tickets` | List or create tickets |
| `GET`, `PATCH` | `/api/v1/tickets/{ticket_id}` | Read or update a ticket |
| `POST` | `/api/v1/tickets/{ticket_id}/messages` | Add a conversation message |
| `GET`, `POST` | `/api/v1/documents` | List or upload documents |
| `GET`, `DELETE` | `/api/v1/documents/{document_id}` | Read or delete an owned document |
| `GET` | `/api/v1/documents/{document_id}/chunks` | Paginated chunk inspection |
| `POST` | `/api/v1/documents/{document_id}/process` | Process a pending document |
| `POST` | `/api/v1/documents/{document_id}/reprocess` | Replace chunks safely |
| `POST` | `/api/v1/documents/{document_id}/embed` | Generate missing embeddings |
| `POST` | `/api/v1/copilot/search` | Owner-scoped semantic retrieval |
| `POST` | `/api/v1/copilot/answer` | Grounded answer with citations |

FastAPI exposes the generated OpenAPI interface at `/docs`.

## Security and ownership isolation

- Supabase access tokens are validated by the backend; missing or invalid tokens return 401.
- Every document lookup filters `documents.uploaded_by` by the authenticated profile ID.
- Chunk inspection, processing, reprocessing, embedding, and deletion first verify document ownership.
- Semantic search joins chunks to documents and applies the same owner ID and completed-status filter.
- A user receives 404 rather than another user's document metadata.
- The Storage bucket is private, object paths are generated by the backend, and the browser never
  receives the Supabase secret key or accesses private objects directly.
- CORS accepts only exact origins configured through `CORS_ORIGINS`; wildcard origins are rejected.
- Upload extension, MIME type, size, checksum, duplicate content, and sanitized filename are enforced.
- `top_k` is limited to 1–10 and queries are stripped, non-empty, and limited to 1,000 characters.
- Provider, database, validation, authentication, and unexpected errors use predictable safe JSON.
- Structured request logs include method, path, status, request ID, and latency without sensitive bodies.

## Deployment

The current frontend build is available as a
[live Vercel demo](https://customer-support-rag-copilot-btsyg2qbm-goblin2.vercel.app). The repository
is prepared for this deployment topology:

- **Vercel:** root directory `frontend`, build command `npm run build`, with only
  `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SUPABASE_URL`, and `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- **Render or Railway:** root directory `backend`, build command `pip install .`, start command
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, and health-check path `/health`.
- **Supabase:** pooled PostgreSQL connection for the API, direct connection for controlled Alembic
  migrations, Auth redirect URLs for the frontend, pgvector enabled, and a private document bucket.

Production values belong in each provider's encrypted environment settings. Do not commit `.env`,
`.env.local`, service credentials, access tokens, or document uploads. See
[`docs/deployment.md`](docs/deployment.md) for the full variable reference and smoke-test checklist.

## Limitations

- The current demo uses a Vercel-generated deployment URL, which may change between deployments.
- Copilot interactions are single-turn; there is no conversation memory or streaming response.
- Retrieval is dense cosine search only—there is no keyword hybrid search or reranker.
- Embedding work is invoked explicitly through the API or CLI; there is no queue or background worker.
- The authorization model isolates individual users but does not implement organization-level tenancy.
- PDF extraction targets text PDFs and does not include OCR for scanned documents.
- The included evaluation data is not yet a published retrieval or groundedness benchmark report.
- Free-tier provider quotas and cold starts can affect latency and availability.

## Future improvements

- Publish the demo at a stable custom domain and keep screenshots synchronized with UI releases.
- Add hybrid keyword/vector retrieval and cross-encoder reranking.
- Introduce structure-aware parent/child chunks and document version comparison.
- Add asynchronous ingestion and embedding jobs with progress reporting.
- Add multi-turn support with explicit, bounded conversation state.
- Add OCR and richer document-format support.
- Build reproducible retrieval, citation, abstention, and latency evaluation reports.
- Add organization-level roles, audit history, and administrative knowledge controls.
- Add OpenTelemetry traces and provider cost/usage dashboards.

## Author

Built by [Mayank Baddam](https://github.com/MayankBaddam).

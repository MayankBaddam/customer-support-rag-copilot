[README (4).md](https://github.com/user-attachments/files/31474305/README.4.md)
# Customer Support RAG Copilot

> A full-stack, evaluation-driven customer-support assistant that retrieves evidence from approved company documents and generates reviewable answers with source citations.

[![Frontend](https://img.shields.io/badge/Frontend-Next.js-black)](#technology-stack)
[![Backend](https://img.shields.io/badge/Backend-FastAPI-009688)](#technology-stack)
[![Database](https://img.shields.io/badge/Database-Supabase_PostgreSQL-3ECF8E)](#technology-stack)
[![Vector Search](https://img.shields.io/badge/Vector_Search-pgvector-blue)](#technology-stack)
[![Status](https://img.shields.io/badge/Status-In_Development-orange)](#project-roadmap)

<!-- Replace these placeholders after deployment. -->

- Live application: `Coming soon`
- API documentation: `Coming soon`
- Demo video: `Coming soon`
- Architecture document: [`docs/architecture.md`](docs/architecture.md)
- Evaluation report: [`evaluation/README.md`](evaluation/README.md)

## Table of contents

1. [Overview](#overview)
2. [Problem statement](#problem-statement)
3. [Project goals](#project-goals)
4. [Core features](#core-features)
5. [Technology stack](#technology-stack)
6. [System architecture](#system-architecture)
7. [Application workflows](#application-workflows)
8. [Repository structure](#repository-structure)
9. [Database design](#database-design)
10. [API design](#api-design)
11. [Project roadmap](#project-roadmap)
12. [Local development](#local-development)
13. [Deployment](#deployment)
14. [Evaluation strategy](#evaluation-strategy)
15. [Testing](#testing)
16. [Security](#security)
17. [Free-tier constraints](#free-tier-constraints)
18. [Future improvements](#future-improvements)

---

## Overview

Support agents often search across policy documents, troubleshooting guides, FAQs, and previous tickets before answering a customer. This process is slow, and an incorrect or outdated answer can damage customer trust.

The Customer Support RAG Copilot gives agents a single workspace in which they can:

- Review a customer ticket and its conversation.
- Ask questions about approved company documentation.
- Receive an answer grounded in retrieved evidence.
- Inspect the passages and documents used by the model.
- Generate and edit a customer-ready response.
- Give feedback when an answer is incorrect, incomplete, or outdated.

The copilot assists the support agent; it does not autonomously send messages or approve sensitive actions.

## Problem statement

Traditional LLM chatbots can produce fluent answers without reliable evidence. Customer support requires a stricter system because answers may involve refunds, account access, security, subscriptions, or contractual policies.

This project addresses four problems:

| Problem | Project response |
|---|---|
| Information is distributed across documents | Centralized searchable knowledge base |
| Keyword search misses paraphrased questions | Vector similarity search with pgvector |
| LLMs can hallucinate policies | Context-grounded prompts and abstention |
| Agents cannot verify generated answers | Document-level and passage-level citations |

## Project goals

### Primary goals

- Build a complete Next.js and FastAPI application.
- Implement document ingestion and vector retrieval.
- Generate answers supported by retrieved evidence.
- Expose sources instead of hiding the RAG process.
- Measure retrieval and answer quality using a repeatable dataset.
- Deploy the complete application using free cloud tiers.

### Non-goals for the MVP

- Automatically sending customer responses.
- Connecting to a real production helpdesk.
- Supporting multiple organizations or tenants.
- Processing confidential customer data.
- Creating a complex multi-agent system.
- Replacing human support agents.

## Core features

### Support workspace

- Ticket list with search, filters, status, category, and priority.
- Ticket conversation and customer-plan information.
- Copilot question input.
- Grounded answer with evidence status.
- Expandable source citations.
- Customer-response drafting and editing.
- Helpful/not-helpful feedback.

### Knowledge management

- Upload PDF, Markdown, and text documents.
- Store original files in Supabase Storage.
- Extract, clean, and chunk document text.
- Generate and store vector embeddings.
- Inspect document processing status and chunks.
- Archive or reprocess a document.

### RAG engineering

- Configurable chunk size and overlap.
- Semantic retrieval using pgvector.
- Metadata-aware filtering.
- Provider-independent embedding and chat interfaces.
- Structured model responses.
- Citation validation.
- Low-evidence abstention.

### Full-stack engineering

- Responsive Next.js interface.
- Typed API client and form validation.
- FastAPI REST API with OpenAPI documentation.
- PostgreSQL schema and migrations.
- Authentication and protected routes.
- Consistent errors, loading states, and empty states.
- Backend, frontend, integration, and RAG evaluation tests.
- CI/CD and cloud deployment.

## Technology stack

| Layer | Technology | Responsibility |
|---|---|---|
| Frontend | Next.js, React, TypeScript | Support-agent user interface |
| Styling | Tailwind CSS | Responsive visual system |
| Forms | React Hook Form and Zod | Form state and client validation |
| Server state | TanStack Query | API caching, loading, and retry states |
| Backend | FastAPI and Python | REST APIs and application logic |
| Validation | Pydantic | Typed request and response contracts |
| ORM | SQLAlchemy | Database access |
| Migrations | Alembic | Version-controlled schema changes |
| Database | Supabase PostgreSQL | Relational application data |
| Vector store | pgvector on Supabase | Embeddings and similarity search |
| File storage | Supabase Storage | Original knowledge documents |
| Authentication | Supabase Auth or backend JWT | User identity and protected access |
| LLM | Gemini through a provider adapter | Answer and response generation |
| Testing | Pytest, Vitest, Playwright | Unit, integration, and end-to-end tests |
| Frontend hosting | Vercel Hobby | Next.js deployment |
| Backend hosting | Render Free | FastAPI deployment |
| CI | GitHub Actions | Automated linting and tests |

## System architecture

### High-level architecture

```mermaid
flowchart TD
    U["Support Agent"] --> FE["Next.js Frontend<br/>Vercel"]
    FE --> API["FastAPI Backend<br/>Render"]
    API --> AUTH["Authentication"]
    API --> DB["Supabase PostgreSQL<br/>Application Data"]
    API --> VS["Supabase pgvector<br/>Document Chunks"]
    API --> FS["Supabase Storage<br/>Original Documents"]
    API --> AI["Embedding and LLM Provider"]
```

### Backend layers

```mermaid
flowchart TD
    R["API Routes"] --> S["Application Services"]
    S --> REP["Repositories"]
    REP --> DB["Supabase PostgreSQL"]
    S --> ING["Ingestion Pipeline"]
    S --> RET["Retrieval Pipeline"]
    S --> GEN["Generation Pipeline"]
    ING --> EXT["External AI and Storage Services"]
    RET --> EXT
    GEN --> EXT
```

### Architectural boundaries

- API routes validate HTTP input and produce HTTP responses.
- Services contain business and RAG logic.
- Repositories isolate SQLAlchemy database operations.
- Provider adapters isolate Gemini or another AI provider.
- The frontend never receives database service-role credentials or model API keys.
- Supabase Row Level Security protects browser-accessible resources.
- Backend authorization remains mandatory for backend-managed resources.

## Application workflows

### Ticket-assistance workflow

```mermaid
sequenceDiagram
    actor Agent
    participant UI as Next.js UI
    participant API as FastAPI
    participant Search as Retrieval Service
    participant DB as Supabase pgvector
    participant LLM as Language Model

    Agent->>UI: Open ticket and ask question
    UI->>API: POST /api/v1/copilot/ask
    API->>Search: Normalize and embed query
    Search->>DB: Retrieve relevant chunks
    DB-->>Search: Chunks and similarity scores
    Search-->>API: Ranked evidence
    API->>LLM: Question plus approved evidence
    LLM-->>API: Structured answer and chunk citations
    API->>API: Validate citations and evidence
    API-->>UI: Answer, citations, and evidence status
    UI-->>Agent: Display reviewable suggestion
```

### Document-ingestion workflow

```mermaid
flowchart TD
    A["Upload document"] --> B["Validate type and size"]
    B --> C["Store original in Supabase Storage"]
    C --> D["Extract text"]
    D --> E["Clean and normalize"]
    E --> F["Create overlapping chunks"]
    F --> G["Generate embeddings"]
    G --> H["Store chunks in pgvector"]
    H --> I["Mark document active"]
    B -->|Invalid| X["Reject with safe error"]
    D -->|Failure| Y["Mark ingestion failed"]
```

### Safe-answer workflow

```mermaid
flowchart TD
    Q["User question"] --> R["Retrieve top evidence"]
    R --> C{"Evidence sufficient?"}
    C -->|No| A["Abstain or request clarification"]
    C -->|Yes| G["Generate grounded answer"]
    G --> V{"Citations valid?"}
    V -->|No| H["Require human review"]
    V -->|Yes| O["Return answer with sources"]
```

### Feedback workflow

```mermaid
flowchart LR
    A["Generated answer"] --> B["Agent reviews"]
    B --> C{"Decision"}
    C -->|Use| D["Copy or edit response"]
    C -->|Reject| E["Choose failure reason"]
    D --> F["Store usage feedback"]
    E --> F
    F --> G["Evaluation dashboard"]
```

## Repository structure

```text
customer-support-rag-copilot/
├── frontend/
│   ├── app/
│   │   ├── (auth)/
│   │   ├── dashboard/
│   │   ├── tickets/
│   │   ├── knowledge-base/
│   │   └── evaluation/
│   ├── components/
│   │   ├── layout/
│   │   ├── tickets/
│   │   ├── copilot/
│   │   └── knowledge/
│   ├── hooks/
│   ├── lib/
│   ├── types/
│   ├── tests/
│   ├── package.json
│   └── Dockerfile
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   ├── core/
│   │   ├── database/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── ingestion/
│   │   ├── retrieval/
│   │   ├── generation/
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── knowledge-base/
│   ├── refund-policy.md
│   ├── subscription-plans.md
│   ├── account-recovery.md
│   ├── data-retention.md
│   └── integration-troubleshooting.md
├── evaluation/
│   ├── datasets/
│   ├── experiments/
│   ├── reports/
│   └── README.md
├── docs/
│   ├── architecture.md
│   ├── decisions.md
│   ├── security.md
│   └── deployment.md
├── .github/workflows/
│   └── ci.yml
├── .env.example
├── .gitignore
├── docker-compose.yml
├── LICENSE
└── README.md
```

## Database design

### Entity relationships

```mermaid
erDiagram
    USERS ||--o{ TICKETS : owns
    TICKETS ||--o{ CONVERSATIONS : contains
    CONVERSATIONS ||--o{ MESSAGES : contains
    USERS ||--o{ DOCUMENTS : uploads
    DOCUMENTS ||--o{ DOCUMENT_CHUNKS : produces
    TICKETS ||--o{ RAG_QUERIES : receives
    RAG_QUERIES ||--o{ RETRIEVAL_RESULTS : retrieves
    RAG_QUERIES ||--|| GENERATED_ANSWERS : generates
    GENERATED_ANSWERS ||--o| FEEDBACK : receives
```

### Main tables

| Table | Purpose |
|---|---|
| `profiles` | Application profile linked to the authenticated user |
| `tickets` | Synthetic customer-support tickets |
| `conversations` | Ticket conversation containers |
| `messages` | Customer and support messages |
| `documents` | Knowledge-document metadata and ingestion status |
| `document_chunks` | Searchable passages and vector embeddings |
| `rag_queries` | Submitted questions and request measurements |
| `retrieval_results` | Retrieved chunks, ranks, and scores |
| `generated_answers` | Generated answer, model, prompt version, and evidence status |
| `feedback` | Agent rating, reason, and edited response |

### pgvector setup

Enable the extension in the Supabase SQL editor or through a controlled migration:

```sql
create extension if not exists vector;
```

The embedding dimension must match the selected embedding model:

```sql
create table document_chunks (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references documents(id) on delete cascade,
    content text not null,
    chunk_index integer not null,
    page_number integer,
    section_title text,
    token_count integer not null,
    metadata jsonb not null default '{}'::jsonb,
    embedding vector(EMBEDDING_DIMENSION),
    created_at timestamptz not null default now()
);
```

Replace `EMBEDDING_DIMENSION` with the exact dimension returned by the chosen embedding model. Do not guess the value.

### Storage buckets

Create a private bucket:

```text
knowledge-documents
```

Recommended object path:

```text
knowledge-documents/{user_id}/{document_id}/{sanitized_filename}
```

Original files remain private. The frontend should request access through authenticated backend endpoints or short-lived signed URLs.

## API design

All endpoints use the `/api/v1` prefix.

### System

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/ready` | Database and dependency readiness |

### Authentication

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Create account if backend-managed auth is used |
| `POST` | `/api/v1/auth/login` | Authenticate user |
| `POST` | `/api/v1/auth/logout` | End session |
| `GET` | `/api/v1/auth/me` | Return current profile |

### Tickets

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/tickets` | Paginated and filtered ticket list |
| `POST` | `/api/v1/tickets` | Create ticket |
| `GET` | `/api/v1/tickets/{ticket_id}` | Ticket with conversation |
| `PATCH` | `/api/v1/tickets/{ticket_id}` | Update status or priority |

### Documents

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/documents` | List knowledge documents |
| `POST` | `/api/v1/documents` | Upload and register document |
| `GET` | `/api/v1/documents/{document_id}` | Document and ingestion status |
| `GET` | `/api/v1/documents/{document_id}/chunks` | Inspect chunks |
| `POST` | `/api/v1/documents/{document_id}/reprocess` | Re-run ingestion |
| `DELETE` | `/api/v1/documents/{document_id}` | Remove file, chunks, and metadata |

### Copilot

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/copilot/search` | Debug retrieval without generation |
| `POST` | `/api/v1/copilot/answer` | Generate an owner-scoped grounded answer with citations |
| `POST` | `/api/v1/copilot/summarize` | Summarize ticket conversation |
| `POST` | `/api/v1/copilot/draft-response` | Generate customer-ready draft |
| `POST` | `/api/v1/copilot/answers/{answer_id}/feedback` | Store agent feedback |

### Example grounded response

```json
{
  "query_id": "9eb8d826-8051-4bb0-aec4-63808f7e8d08",
  "answer": "Customers may request a refund within 30 days of the initial purchase.",
  "evidence_status": "sufficient",
  "needs_human_review": false,
  "citations": [
    {
      "document_id": "fa8b9c75-891f-4a64-a249-d664fb262b68",
      "chunk_id": "6d8a282e-5b6d-45d5-a207-d69c49e3ccbf",
      "title": "Refund Policy",
      "section": "Eligibility",
      "page": 2,
      "excerpt": "Refund requests must be submitted within 30 days..."
    }
  ]
}
```

### Error contract

```json
{
  "error": {
    "code": "DOCUMENT_PROCESSING_FAILED",
    "message": "The document could not be processed.",
    "request_id": "req_01J6XYZ"
  }
}
```

## Project roadmap

The MVP is divided into eight phases so each phase produces a demonstrable result.

### Phase 1 — Product definition and repository setup

**Objective:** establish a reproducible full-stack foundation.

Tasks:

- Define the fictional CloudDesk support domain.
- Create 10–15 coherent support documents.
- Create 20–30 synthetic tickets.
- Initialize Next.js, FastAPI, Docker, and GitHub Actions.
- Create the Supabase project and local environment templates.
- Add `/health` and `/api/v1/ready` endpoints.
- Document the initial architecture.

Deliverable:

> Frontend, backend, and database connect successfully; the repository can be installed from its documentation.

### Phase 2 — Authentication and ticket management

**Objective:** demonstrate regular full-stack application engineering before adding AI.

Tasks:

- Add authentication and protected routes.
- Create profile, ticket, conversation, and message tables.
- Configure Row Level Security where browser-side Supabase access is used.
- Implement ticket CRUD APIs.
- Build ticket list, filters, pagination, and ticket details.
- Add client and server validation.

Deliverable:

> A signed-in demo user can browse, search, filter, create, and update support tickets.

### Phase 3 — Document ingestion

**Objective:** turn uploaded support documents into searchable knowledge.

Tasks:

- Validate extension, MIME type, and file size.
- Store original files in the private Supabase Storage bucket.
- Extract PDF, Markdown, and text content.
- Clean repeated whitespace and broken formatting.
- Create approximately 500-token chunks with approximately 75-token overlap.
- Preserve title, page, section, version, and source metadata.
- Track `pending`, `processing`, `completed`, and `failed` statuses.

Deliverable:

> An uploaded document is stored, processed, and displayed with inspectable chunks.

### Phase 4 — Embeddings and semantic retrieval

**Objective:** retrieve relevant evidence without generating an answer.

Tasks:

- Implement an embedding-provider interface.
- Generate embeddings in batches.
- Store embeddings in `document_chunks`.
- Implement cosine-similarity search.
- Support active-document and category filters.
- Build a retrieval-debug page showing content, score, source, and latency.
- Create at least 30 question-to-source evaluation cases.

Deliverable:

> The expected source appears in the top five results for at least 80% of the initial test questions.

#### Embedding backfill operations

Run the backfill explicitly from the `backend` directory. It is never started by application startup,
migrations, or tests:

```powershell
python -m app.embedding_backfill
```

Useful options:

```powershell
python -m app.embedding_backfill --dry-run
python -m app.embedding_backfill --document-id <document-uuid>
python -m app.embedding_backfill --batch-size 8 --limit 100
python -m app.embedding_backfill --force
```

The default run selects only chunks belonging to completed documents whose embedding is null. It
commits one batch at a time, so a rerun safely skips already committed embeddings. `--dry-run` makes
no Gemini requests and writes nothing. `--force` is the only mode that replaces existing vectors;
use it deliberately because it consumes quota again. Timeout, network, and quota failures receive a
small number of bounded-backoff retries, and the command exits non-zero if any batch still fails.

To verify counts without returning vector values, query PostgreSQL directly with an authorized
administrative connection:

```sql
select document_id, count(*) as total_chunks, count(embedding) as embedded_chunks
from document_chunks
group by document_id
order by document_id;
```

Keep `GEMINI_API_KEY` only in backend environment configuration. Do not print chunk content, API keys,
or vectors in command output or logs. The optional authenticated
`POST /api/v1/documents/{document_id}/embed` endpoint applies the same completed-document,
idempotency, batching, retry, and force-mode rules and returns counts and status only.

#### Grounded answer API

Authenticated users can generate an answer from their own completed, embedded knowledge documents:

```http
POST /api/v1/copilot/answer
Content-Type: application/json
Authorization: Bearer <access-token>

{
  "query": "How long does a password recovery link remain valid?",
  "top_k": 5
}
```

The service embeds the query, retrieves owner-scoped chunks with cosine similarity, and sends only
the query plus retrieved chunk content and source metadata to the configured `ANSWER_MODEL`. Gemini
is instructed to answer exclusively from that context and to state that the knowledge base lacks
enough information when the evidence is insufficient. Citations are built by the backend from the
retrieved rows rather than generated by the model.

The response contains `answer`, `citations`, and `retrieved_chunks`. Each citation includes document
title, original filename, chunk ID, section title, page number, and similarity score. Embedding vectors,
prompts, access tokens, and backend secrets are never included. Configure generation only in the
backend with `GEMINI_API_KEY`, `ANSWER_MODEL`, timeout, and bounded retry settings.

### Phase 5 — Grounded answer generation

**Objective:** generate useful answers without hiding uncertainty.

Tasks:

- Retrieve the top evidence for each question.
- Build a context-limited prompt.
- Request a structured model response.
- Validate cited chunk identifiers.
- Detect weak evidence and abstain.
- Save query, retrieval, answer, latency, model, and prompt version.
- Add ticket summarization and response drafting.

Deliverable:

> The copilot produces reviewable answers with valid citations and refuses unsupported questions.

### Phase 6 — Complete support-agent interface

**Objective:** turn the RAG pipeline into a polished product workflow.

Tasks:

- Build dashboard statistics and recent-ticket views.
- Add the ticket conversation and copilot side panel.
- Add expandable citation cards.
- Add editable response drafts and copy actions.
- Add feedback reasons.
- Implement skeletons, empty states, error messages, and retries.
- Verify responsive and accessible behaviour.

Deliverable:

> A user can complete `ticket → question → evidence → draft → feedback` from one interface.

### Phase 7 — Evaluation, testing, and security

**Objective:** provide evidence that the system works reliably.

Tasks:

- Expand the evaluation dataset to 40–60 questions.
- Measure Hit Rate@K, Recall@K, MRR, citation correctness, abstention accuracy, and latency.
- Add parser, chunker, retrieval, citation, and API tests.
- Add one Playwright end-to-end test.
- Add rate limits, upload limits, log redaction, and safe error responses.
- Test prompt injection, missing evidence, invalid citations, and archived documents.

Deliverable:

> CI passes and the repository contains a reproducible evaluation report with actual results.

### Phase 8 — Deployment and portfolio packaging

**Objective:** publish a live, understandable portfolio application.

Tasks:

- Deploy PostgreSQL, Auth, Storage, and pgvector on Supabase.
- Deploy FastAPI on Render.
- Deploy Next.js on Vercel.
- Configure CORS, environment variables, and migrations.
- Seed non-sensitive demonstration content.
- Add screenshots, architecture diagrams, results, limitations, and live links.
- Record a two-to-three-minute demonstration video.

Deliverable:

> A recruiter can open the application, use a demo account, inspect citations, review evaluation results, and understand the architecture from this README.

### Suggested eight-day schedule

| Day | Phase | Outcome |
|---:|---|---|
| 1 | Phase 1 | Repository, applications, Supabase, and health checks |
| 2 | Phase 2 | Authentication and ticket workflow |
| 3 | Phase 3 | Upload, storage, parsing, and chunking |
| 4 | Phase 4 | Embeddings, pgvector, and retrieval lab |
| 5 | Phase 5 | Grounded answers, citations, and abstention |
| 6 | Phase 6 | Complete agent workspace and feedback |
| 7 | Phase 7 | Tests, evaluation, and security checks |
| 8 | Phase 8 | Vercel, Render, Supabase, README, and demo |

## Local development

### Prerequisites

- Git
- Node.js supported by the selected Next.js release
- Python 3.12 or the version declared in `backend/pyproject.toml`
- Docker Desktop, optional but recommended
- Supabase project
- AI provider API key

### Clone

```bash
git clone https://github.com/YOUR_USERNAME/customer-support-rag-copilot.git
cd customer-support-rag-copilot
```

### Environment variables

Create `backend/.env`:

```env
ENVIRONMENT=development
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:6543/postgres
MIGRATION_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/postgres
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=replace_me
SUPABASE_SECRET_KEY=replace_me
SEED_DEMO_USER_ID=replace_with_supabase_auth_user_uuid
SUPABASE_STORAGE_BUCKET=knowledge-documents
GEMINI_API_KEY=replace_me
EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIMENSION=768
CORS_ORIGINS=http://localhost:3000,https://frontend.example.com
```

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=replace_me
```

Security rules:

- Never place the Supabase service-role key in the frontend.
- Never prefix model or database secrets with `NEXT_PUBLIC_`.
- Commit `.env.example`; never commit `.env` or `.env.local`.
- Use the pooled Supabase connection for application runtime.
- Use the direct connection for Alembic migrations when required.

### Backend

```bash
cd backend
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

To explicitly seed the fictional CloudDesk demo data, create a Supabase Auth
user, set its UUID as `SEED_DEMO_USER_ID` in `backend/.env`, and run:

```powershell
python -m app.seed
```

macOS or Linux:

```bash
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

Backend URLs:

- API: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend URL: `http://localhost:3000`

### Tests

```bash
cd backend
pytest
```

```bash
cd frontend
npm run lint
npm run test
```

## Deployment

The complete environment-variable reference, Render/Railway and Vercel setup,
Supabase preparation, command verification, and production smoke checklist are in
[Deployment readiness](docs/deployment.md).

### Production topology

```mermaid
flowchart TD
    GH["GitHub main branch"] --> CI["GitHub Actions"]
    CI --> V["Vercel<br/>frontend/"]
    CI --> R["Render<br/>backend/"]
    V --> R
    R --> SDB["Supabase PostgreSQL + pgvector"]
    R --> SFS["Supabase Storage"]
    R --> LLM["AI Provider"]
```

### 1. Supabase

1. Create a Supabase project.
2. Enable the `vector` extension.
3. Create a private `knowledge-documents` bucket.
4. Copy the pooled and direct PostgreSQL connection strings.
5. Add the migration connection locally or to a controlled deployment job.
6. Run `alembic upgrade head`.
7. Configure authentication redirect URLs.
8. Apply and test Row Level Security policies.
9. Seed only fictional documents and tickets.

### 2. Render backend

1. Create a Render Web Service from this GitHub repository.
2. Set the root directory to `backend`.
3. Choose the free instance type.
4. Use the build command appropriate to `pyproject.toml`, for example:

```bash
pip install -e .
```

5. Use the start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

6. Configure `/health` as the health-check path.
7. Add backend environment variables in Render.
8. Verify the OpenAPI page and readiness endpoint.

Do not store documents on Render's local filesystem. Free instances can restart, so durable files belong in Supabase Storage.

### 3. Vercel frontend

1. Import the same GitHub repository into Vercel.
2. Set the root directory to `frontend`.
3. Select Next.js as the framework.
4. Add public Supabase variables and `NEXT_PUBLIC_API_URL`.
5. Deploy.
6. Add the final Vercel origin to the backend `CORS_ORIGINS` allowlist.

### 4. Production verification

- Open the frontend.
- Sign in with the demo account.
- Confirm the dashboard loads.
- Upload a small document.
- Confirm ingestion completes.
- Ask a question whose answer exists.
- Open the returned citation.
- Ask an unsupported question and confirm abstention.
- Submit feedback.
- Review Render and Supabase logs for unexpected errors.

## Evaluation strategy

### Dataset format

```json
{
  "id": "refund-001",
  "question": "Can I get a refund 45 days after purchase?",
  "expected_document": "refund-policy",
  "expected_section": "Eligibility",
  "expected_behavior": "answer",
  "required_claims": ["Refunds are limited to the documented eligibility period"],
  "forbidden_claims": ["A refund has been approved"],
  "difficulty": "medium"
}
```

### Evaluation categories

| Category | Minimum cases |
|---|---:|
| Direct factual questions | 15 |
| Paraphrased questions | 10 |
| Technical or error-code questions | 5 |
| Multi-section questions | 5 |
| Unanswerable questions | 5 |
| Prompt-injection attempts | 5 |
| Conflicting or archived information | 5 |

### Metrics

| Layer | Metrics |
|---|---|
| Retrieval | Hit Rate@K, Recall@K, MRR, latency |
| Generation | Correctness, relevance, groundedness |
| Citations | Citation correctness and completeness |
| Safety | Abstention accuracy and injection resistance |
| System | End-to-end latency, failures, token usage |

### Release gates

- Correct document appears in top five for at least 80% of the MVP dataset.
- Every returned citation references a retrieved chunk.
- Unsupported questions do not receive confident policy answers.
- Archived documents are excluded from production retrieval.
- No critical API, authentication, or cross-user access test fails.

Actual measurements should be recorded in `evaluation/reports/`; targets must not be presented as achieved results.

## Testing

### Backend tests

- File and MIME validation.
- Text cleaning and chunk boundaries.
- Embedding-provider failure handling.
- Vector retrieval and metadata filters.
- Citation validation.
- Ticket authorization.
- Document deletion and cascade behaviour.
- Consistent API errors.

### Frontend tests

- Login validation.
- Ticket filters.
- Loading and empty states.
- Copilot answer rendering.
- Citation expansion.
- Feedback submission.

### End-to-end tests

- Sign in and open a ticket.
- Ask the copilot and inspect a citation.
- Upload and process a knowledge document.
- Submit negative feedback with a reason.

External model calls should be mocked in normal CI. Run live-model evaluation manually or through an explicitly triggered workflow to protect free API quota.

## Security

### Required controls

- Use fictional data only in the public demonstration.
- Keep secrets in hosting-platform environment variables.
- Validate authentication in the backend.
- Apply ownership checks to tickets, documents, answers, and feedback.
- Use Row Level Security for resources accessed through Supabase clients.
- Keep the Supabase service-role key on the backend only.
- Restrict upload extension, MIME type, and size.
- Sanitize filenames and generate server-side object paths.
- Treat retrieved text as untrusted evidence, never as system instructions.
- Add request limits and model timeouts.
- Redact tokens, credentials, and sensitive content from logs.
- Validate that cited chunks were actually retrieved.

### Prompt-injection boundary

```text
System instructions: trusted application policy
User question: untrusted input
Retrieved document text: untrusted evidence
Tool output: validated structured data
Final answer: validated structured response
```

Retrieved text may inform the answer but cannot override application instructions or authorize actions.

## Free-tier constraints

This project is designed for portfolio traffic, not continuous production load.

| Constraint | Mitigation |
|---|---|
| Render backend may sleep | Show a startup notice and retry the first request |
| AI provider quota is limited | Add request caps, short context, caching, and clear quota errors |
| Supabase resources are limited | Use small fictional datasets and remove unused vectors/files |
| Long ingestion can exceed request limits | Restrict document size and process compact demo documents |
| GitHub CI should not spend model quota | Mock external AI calls in CI |

Never enable automatic paid usage solely for a public portfolio demo. Add explicit rate limits before sharing the live URL.

## Future improvements

- Hybrid dense and keyword retrieval.
- Cross-encoder reranking.
- Structure-aware and parent-child chunking.
- Streaming answers.
- Asynchronous ingestion queue.
- Document version comparison.
- Knowledge-gap detection from negative feedback.
- LangGraph routing and human-review checkpoints.
- Multilingual retrieval.
- Helpdesk integration through a controlled adapter.
- OpenTelemetry traces and detailed cost dashboards.

## Status

- [ ] Phase 1: Product definition and repository setup
- [ ] Phase 2: Authentication and ticket management
- [ ] Phase 3: Document ingestion
- [ ] Phase 4: Embeddings and semantic retrieval
- [ ] Phase 5: Grounded answer generation
- [ ] Phase 6: Support-agent interface
- [ ] Phase 7: Evaluation, testing, and security
- [ ] Phase 8: Deployment and portfolio packaging


## Author

**Mayank Baddam**


---

If you find this project useful, consider starring the repository. Feedback and constructive suggestions are welcome.

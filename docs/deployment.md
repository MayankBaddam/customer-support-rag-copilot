# Deployment readiness

This guide prepares the Customer Support RAG Copilot for deployment without performing a deployment.
Run all commands from the indicated application root and keep real credentials in local environment
files or the hosting provider's encrypted environment-variable settings.

## Verified production commands

Backend platforms must use `backend` as the working directory and run:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Render and Railway provide `PORT`, and the backend Docker image requires that environment variable
instead of embedding a port. When running the image locally, pass `PORT` explicitly. Do not add
`--reload` in production.

Vercel must use `frontend` as the root directory. The production build command is:

```bash
npm run build
```

The repository uses the standard Next.js production output and `npm run start` when running the
built frontend outside Vercel.

## Environment variables

Use [backend/.env.example](../backend/.env.example) and
[frontend/.env.example](../frontend/.env.example) as templates. They contain placeholders and safe
local defaults only. Never commit `backend/.env`, `frontend/.env.local`, credentials, or copied
hosting-provider values.

### Backend local development

Create `backend/.env` with these values:

| Variable | Required | Purpose |
|---|---|---|
| `ENVIRONMENT` | Yes | Use `development` locally and `production` on the hosted service. |
| `DATABASE_URL` | Yes | Pooled Supabase PostgreSQL URL used by the running API. |
| `MIGRATION_DATABASE_URL` | Yes for migrations | Direct Supabase PostgreSQL URL used only by Alembic. |
| `SUPABASE_URL` | Yes | Supabase project URL used by Auth and Storage. |
| `SUPABASE_ANON_KEY` | Yes | Public Supabase key used by the backend to validate user access tokens. |
| `SUPABASE_SECRET_KEY` | Yes | Backend-only Supabase secret key used for private Storage operations. |
| `SUPABASE_STORAGE_BUCKET` | Yes | Name of the private document bucket; normally `knowledge-documents`. |
| `GEMINI_API_KEY` | Yes | Backend-only Gemini credential used for embeddings and grounded answers. |
| `EMBEDDING_MODEL` | Yes | Must remain `gemini-embedding-001` for the current embedding data. |
| `EMBEDDING_DIMENSION` | Yes | Must remain `768` to match the pgvector column and index. |
| `CORS_ORIGINS` | Yes | Comma-separated exact frontend origins, such as local Next.js during development. |

The following backend settings have safe defaults but should be reviewed before production:

| Variable | Default | Purpose |
|---|---:|---|
| `MAX_DOCUMENT_SIZE_BYTES` | `5242880` | Upload limit; configuration cannot exceed 5 MiB. |
| `EMBEDDING_BATCH_SIZE` | `16` | Maximum texts sent in one embedding batch. |
| `EMBEDDING_API_TIMEOUT_SECONDS` | `30` | Embedding request timeout. |
| `EMBEDDING_MAX_RETRIES` | `2` | Bounded embedding retries. |
| `EMBEDDING_RETRY_BACKOFF_SECONDS` | `0.5` | Initial embedding retry delay. |
| `EMBEDDING_RETRY_MAX_BACKOFF_SECONDS` | `4` | Maximum embedding retry delay. |
| `ANSWER_MODEL` | `gemini-2.5-flash` | Gemini model used for grounded answer generation. |
| `ANSWER_API_TIMEOUT_SECONDS` | `30` | Answer-generation request timeout. |
| `ANSWER_MAX_RETRIES` | `2` | Bounded answer-generation retries. |
| `ANSWER_RETRY_BACKOFF_SECONDS` | `0.5` | Initial answer retry delay. |
| `ANSWER_RETRY_MAX_BACKOFF_SECONDS` | `4` | Maximum answer retry delay. |
| `SEED_DEMO_USER_ID` | Unset | Optional Supabase Auth user UUID used only by the explicit seed command. |

Settings load from `backend/.env` during local development. Start locally with port 8000 and include
`http://localhost:3000` in `CORS_ORIGINS`.

### Backend on Render or Railway

Set the same backend runtime variables in the service's encrypted environment settings. Use real
hosted values for `DATABASE_URL`, Supabase credentials, `GEMINI_API_KEY`, and `CORS_ORIGINS`.
Additionally:

- Set `ENVIRONMENT=production`.
- Set `CORS_ORIGINS` to the exact HTTPS Vercel domain and any intentional custom frontend domains.
- Do not use `*` and do not add paths to an origin.
- Keep `SUPABASE_SECRET_KEY`, database URLs, and `GEMINI_API_KEY` backend-only.
- Let the platform provide `PORT`; do not place `PORT` in a committed environment file.
- Provide `MIGRATION_DATABASE_URL` only to the controlled migration command or deployment job when
  the platform supports separating migration and runtime secrets.

### Frontend local development and Vercel

Create `frontend/.env.local` locally or configure these in Vercel for Preview and Production:

| Variable | Required | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Yes | Public HTTPS origin of the deployed FastAPI service, without `/api/v1`. |
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Public Supabase project URL used for browser authentication. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | Public Supabase anonymous/publishable key used for browser authentication. |

Only these browser-safe values use the `NEXT_PUBLIC_` prefix. Never add the Supabase secret key,
Gemini key, database URLs, access tokens, or backend `.env` contents to Vercel frontend variables.
Vercel embeds public variables at build time, so redeploy after changing them.

## Supabase preparation

### Database and migrations

1. Create the Supabase project and copy both PostgreSQL connection strings.
2. Use the pooled connection string for `DATABASE_URL` and the direct connection for
   `MIGRATION_DATABASE_URL`.
3. Confirm the `vector` extension is enabled.
4. From `backend`, run `python -m alembic upgrade head` using the project virtual environment.
5. Confirm the latest migration is recorded and that the existing support, document, chunk, and
   vector-index objects remain present.
6. Do not run migrations from application startup or invoke embedding generation from migrations.

### Private Storage

1. In Supabase Storage, create the bucket named by `SUPABASE_STORAGE_BUCKET`.
2. Keep the bucket private; do not enable public access or create a public document URL.
3. Use `SUPABASE_SECRET_KEY` only in the backend deployment.
4. Confirm uploads use backend-generated user/document paths and survive service restarts.
5. Confirm deletion removes both the private object and its database record.

### Authentication

1. Enable the intended Supabase Auth sign-in method.
2. Set the Supabase Auth site URL to the production Vercel origin.
3. Add the local frontend and intended Vercel Preview/Production callback origins to the allowed
   redirect URLs.
4. Create a test user through Supabase Auth; use fictional data only.
5. Confirm the browser uses `NEXT_PUBLIC_SUPABASE_ANON_KEY` and the backend validates the resulting
   bearer token with `SUPABASE_ANON_KEY`.
6. Confirm protected endpoints return 401 without a valid session and owner isolation remains active.

## Render backend

1. Create a Render Web Service from the repository.
2. Set **Root Directory** to `backend` and choose the Python runtime.
3. Set **Build Command** to `pip install .`.
4. Set **Start Command** to:

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

5. Add the backend production variables listed above.
6. Set the health-check path to `/health`.
7. Run `python -m alembic upgrade head` as a controlled pre-deploy step or from an authorized one-off
   shell before serving the new revision.
8. Verify `/health` returns HTTP 200 before connecting Vercel.

Do not store uploads on Render's filesystem. Supabase Storage is the durable document store.

## Railway backend alternative

1. Create a Railway service from the repository and set the root directory to `backend`.
2. Set the build command to `pip install .`.
3. Use the same `uvicorn app.main:app --host 0.0.0.0 --port $PORT` start command.
4. Add the backend production variables and let Railway supply `PORT`.
5. Run Alembic as a controlled deployment or one-off command before switching traffic.
6. Configure `/health` for health monitoring and verify it returns HTTP 200.

## Vercel frontend

1. Import the repository into Vercel.
2. Set **Root Directory** to `frontend` and use the detected Next.js framework preset.
3. Keep **Install Command** as `npm install` and **Build Command** as `npm run build`.
4. Add all three frontend variables for Preview and Production.
5. Set `NEXT_PUBLIC_API_URL` to the HTTPS Render or Railway backend origin.
6. Deploy the frontend, then add its exact HTTPS origin to backend `CORS_ORIGINS` and restart the
   backend service.
7. Add the same Vercel origin to the Supabase Auth site/redirect configuration.

## Production smoke-test checklist

Perform these checks after deployment using a fictional test account and a small non-sensitive TXT
document:

- [ ] **Health check:** `GET https://BACKEND_HOST/health` returns HTTP 200 with `status: "ok"` and no
  configuration or secret values.
- [ ] **Sign in:** the Vercel frontend establishes a Supabase session and protected API requests work.
- [ ] **Upload document:** upload the TXT file in Knowledge Base and confirm its object exists only in
  the private bucket.
- [ ] **Process document:** process it and confirm status becomes `completed` with a non-zero chunk count.
- [ ] **Generate embeddings:** call the authenticated `POST /api/v1/documents/{document_id}/embed`
  endpoint once and confirm a completed count without vectors in the response.
- [ ] **Semantic search:** use Retrieval Debug and confirm only the signed-in user's completed chunks
  are returned.
- [ ] **Grounded answer:** ask a question answered by the uploaded TXT file in Copilot.
- [ ] **Citations:** confirm title, original filename, section/page when applicable, chunk ID, and
  similarity score are shown and point to the retrieved evidence.
- [ ] **Delete document:** delete it in Knowledge Base and confirm both the Storage object and database
  document/chunk records are removed.

Also test an unsupported question and confirm the Copilot abstains, inspect backend logs for request
IDs and failures without sensitive values, and confirm another user cannot access the test document.

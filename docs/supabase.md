# Supabase database foundation

Phase 1C uses two PostgreSQL connection strings:

- `DATABASE_URL`: Supavisor pooled connection for application runtime, normally port `6543`.
- `MIGRATION_DATABASE_URL`: direct database connection for Alembic migrations, normally port `5432`.

In the Supabase dashboard, open **Connect**, choose **Postgres**, and copy the
connection strings. Put them only in a local `backend/.env` or an equivalent
secret store. Replace the placeholders in `.env.example` locally; never commit
the resulting values.

The service-role key is not used by this database foundation and must never be
placed in frontend variables or code.

## pgvector

The initial migration runs:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Run `alembic upgrade head` with a direct connection role permitted to install
extensions. If that role lacks permission, run the exact SQL above in the
Supabase SQL Editor as a project owner, then run future migrations normally.
This phase creates no application tables.
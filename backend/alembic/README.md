# Alembic migrations

Run migrations with `MIGRATION_DATABASE_URL`, which must be the direct Supabase
PostgreSQL connection. `DATABASE_URL` is reserved for the pooled application
runtime connection.

The initial revision only enables pgvector and creates no application tables.
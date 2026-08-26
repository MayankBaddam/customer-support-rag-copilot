# CloudDesk demo seed data

Seeding is explicit and never runs during application startup. Create a demo user
in Supabase Auth first, then copy that user's UUID into the ignored local
`backend/.env` file:

```env
SEED_DEMO_USER_ID=the-supabase-auth-user-uuid
```

Run from the repository root:

```powershell
Push-Location backend
python -m app.seed
Pop-Location
```

The command creates one agent profile, 20 fictional tickets, one conversation
per ticket, and three messages per conversation. It is idempotent by the fixed
seed ticket numbers (`TCK-1001` through `TCK-1020`); running it again creates no
duplicates.

The seed uses only fictional names and `example.com` addresses. Do not use this
seed command against a production database without explicit approval.

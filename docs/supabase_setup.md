# Supabase setup (one person does this, then shares the project)

1. Go to https://supabase.com, sign in, **New project** (free tier is enough).
   Pick a strong database password and save it in a password manager.
2. **SQL Editor -> New query**, paste all of `database/schema.sql`, click **Run**.
   You should see tables `profiles, sessions, attempts, issues, exercises`.
3. **Authentication -> Providers -> Email**: for development turn **off**
   "Confirm email" so test accounts work instantly.
4. **Project Settings -> API**: copy **Project URL** and the **anon public** key.
5. Locally: `cp .env.example .env` and fill `SUPABASE_URL` and `SUPABASE_ANON_KEY`.
   Never commit `.env`. Never use the `service_role` key in the app: it bypasses
   the row level security that keeps each student's history private.
6. Teammates: share URL + anon key privately (the anon key is safe to ship in
   a client, RLS protects the data), each puts it in their own `.env`.
7. Check it works: `python scripts/smoke_supabase.py`

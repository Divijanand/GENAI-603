-- CodeMentor AI: Supabase (Postgres) schema.
-- Every table is scoped by user_id and protected with row level security, so
-- each student has an independent history (no shared per-user .md file).

create table if not exists profiles (
    user_id     uuid primary key references auth.users(id) on delete cascade,
    display_name text,
    created_at  timestamptz not null default now()
);

-- One debugging session = one piece of code the student is working on.
create table if not exists sessions (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references profiles(user_id) on delete cascade,
    title       text,
    started_at  timestamptz not null default now(),
    closed_at   timestamptz
);

-- Every submission (first try and each resubmission) in a session.
create table if not exists attempts (
    id          uuid primary key default gen_random_uuid(),
    session_id  uuid not null references sessions(id) on delete cascade,
    user_id     uuid not null references profiles(user_id) on delete cascade,
    attempt_no  int  not null,
    code        text not null,
    created_at  timestamptz not null default now(),
    unique (session_id, attempt_no)
);

-- A distinct mistake within a session. `fingerprint` de-duplicates: the same
-- issue seen on a resubmission updates this row instead of creating a new one.
create table if not exists issues (
    id            uuid primary key default gen_random_uuid(),
    session_id    uuid not null references sessions(id) on delete cascade,
    user_id       uuid not null references profiles(user_id) on delete cascade,
    category      text not null,          -- fixed taxonomy, see taxonomy.py
    rule_key      text not null,          -- e.g. ruff code or AST check name
    fingerprint   text not null,
    message       text,
    first_attempt int  not null,
    last_attempt  int  not null,
    attempts_seen int  not null default 1,
    hint_level    int  not null default 0, -- 0 none, 1 nudge, 2 guided, 3 fix
    status        text not null default 'open' check (status in ('open', 'resolved')),
    resolved_at   timestamptz,
    created_at    timestamptz not null default now(),
    unique (session_id, fingerprint)
);

create table if not exists exercises (
    id            uuid primary key default gen_random_uuid(),
    user_id       uuid not null references profiles(user_id) on delete cascade,
    category      text not null,
    prompt        text not null,
    reference_solution text not null,
    tests         text not null,
    verified      boolean not null default false,
    created_at    timestamptz not null default now()
);

create index if not exists issues_user_category on issues (user_id, category);
create index if not exists attempts_session on attempts (session_id, attempt_no);

-- Row level security: a user only ever sees their own rows.
alter table profiles  enable row level security;
alter table sessions  enable row level security;
alter table attempts  enable row level security;
alter table issues    enable row level security;
alter table exercises enable row level security;

create policy "own profile"   on profiles  for all using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy "own sessions"  on sessions  for all using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy "own attempts"  on attempts  for all using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy "own issues"    on issues    for all using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy "own exercises" on exercises for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- Auto-create a profile row when a student signs up, so inserts into
-- sessions/attempts/issues (which reference profiles) never fail.
create or replace function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = public as $$
begin
    insert into public.profiles (user_id, display_name)
    values (new.id, split_part(new.email, '@', 1))
    on conflict do nothing;
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();

-- Migration for projects created before created_at existed (safe to re-run).
alter table issues add column if not exists created_at timestamptz not null default now();

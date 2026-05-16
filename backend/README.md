# TalentExe — Backend

Django 5 + Django REST Framework backend for TalentExe. Connects to Supabase (PostgreSQL) and validates Supabase JWTs for API authentication.

---

## Stack

| | |
|---|---|
| Framework | Django 5.0.6 + DRF 3.15 |
| Database | Supabase (PostgreSQL 15) via psycopg2 |
| Auth | Supabase JWT (validated in custom DRF auth class) |
| Admin | Django Admin (manages HR users) |
| Python | 3.11+ |

---

## Project Structure

```
backend/
├── manage.py
├── requirements.txt
├── .env                    ← gitignored, real secrets
├── .env.example            ← committed template
├── project/
│   ├── settings/
│   │   ├── base.py         ← shared settings
│   │   ├── dev.py          ← local dev (DEBUG=True)
│   │   └── prod.py         ← production
│   ├── urls.py
│   └── wsgi.py
└── apps/
    └── users/
        ├── models.py        ← UserProfile (mirrors public.profiles in Supabase)
        ├── admin.py         ← Django Admin with Supabase user creation hook
        ├── authentication.py← SupabaseJWTAuthentication (custom DRF class)
        ├── serializers.py
        ├── views.py         ← GET /api/v1/auth/me/
        ├── urls.py
        └── services.py      ← Supabase Admin API calls
```

---

## Local Setup

```bash
cd backend

# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy env template and fill in values (already done if you followed Phase 1)
cp .env.example .env

# 4. Run Django migrations (creates built-in auth/session tables only)
#    UserProfile uses managed=False — Supabase owns the profiles table DDL
python manage.py migrate

# 5. Create a superuser for Django Admin
python manage.py createsuperuser

# 6. Start the dev server
python manage.py runserver
# → http://localhost:8000
# → http://localhost:8000/admin/  (Django Admin)
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `DJANGO_SECRET_KEY` | Django secret key |
| `DJANGO_DEBUG` | `True` for local dev |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hosts |
| `DATABASE_URL` | Full postgres connection URL (URL-encode special chars in password) |
| `DB_HOST` | Supabase pooler host |
| `DB_PORT` | `5432` |
| `DB_NAME` | `postgres` |
| `DB_USER` | Supabase user (e.g. `postgres.<project-ref>`) |
| `DB_PASSWORD` | Supabase database password |
| `SUPABASE_URL` | `https://<project-ref>.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key from Supabase dashboard (bypasses RLS) |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000` for local dev |
| `ANTHROPIC_API_KEY` | Phase 2+ — leave blank for now |

---

## API Endpoints

### `GET /api/v1/auth/me/`

Returns the profile of the authenticated user. Requires a valid Supabase JWT in the `Authorization` header.

**Request**
```
GET /api/v1/auth/me/
Authorization: Bearer <supabase-access-token>
```

**Response 200**
```json
{
  "data": {
    "id": "uuid",
    "email": "hr@company.com",
    "full_name": "Jane Smith",
    "role": "hr",
    "is_active": true
  },
  "error": null,
  "meta": {}
}
```

**Response 401** — missing or invalid token  
**Response 403** — user not found in `public.profiles` or inactive

---

## Django Admin

Access at `http://localhost:8000/admin/` with your superuser credentials.

**What you can do:**
- **Create HR users** — fill in email + full name → backend calls the Supabase Admin API to create an `auth.users` record, then saves a `profiles` row with `role = 'hr'`
- **List / search / filter** users by role and active status
- **Toggle `is_active`** to enable/disable access
- **Delete users** from the profiles table

> Note: Deleting a user here does not delete them from Supabase Auth. Use the Supabase dashboard or the Admin API for full deletion.

---

## Authentication Architecture

All API requests must carry a Supabase JWT:

```
Supabase signInWithPassword()
  → returns access_token (JWT)
  → Frontend sends: Authorization: Bearer <access_token>
  → SupabaseJWTAuthentication decodes JWT, extracts sub (UUID)
  → Looks up UserProfile by that UUID
  → Returns (profile, token) tuple to DRF
```

The `UserProfile.id` is the same UUID as `auth.users.id` in Supabase — no join needed.

---

## Database Schema (run in Supabase SQL Editor)

```sql
create type user_role as enum ('hr', 'employee');

create table public.profiles (
    id          uuid primary key references auth.users(id) on delete cascade,
    email       text not null unique,
    full_name   text not null,
    role        user_role not null,
    is_active   boolean not null default true,
    created_by  uuid references public.profiles(id) on delete set null,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger profiles_updated_at
before update on public.profiles
for each row execute function public.set_updated_at();

alter table public.profiles enable row level security;

create policy "self_read"
on public.profiles for select
using (auth.uid() = id);
```

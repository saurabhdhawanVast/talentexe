# Phase 1 — Foundation, Admin Panel & Auth

## Objective

Stand up the full project skeleton (frontend, backend, database) and deliver two working things:

1. **Admin** manages HR users via the **Django Admin panel** (no custom frontend for admin).
2. **HR users can log in** to the Next.js frontend using the same auth system that employees will use in later phases.

No email notifications yet — that is Phase 2.

---

## Scope Boundaries

| In Scope (Phase 1) | Deferred (Phase 2+) |
|---|---|
| Project scaffolding (Next.js + Django + Supabase) | Email invite to HR after creation |
| Environment config (.env / .gitignore) | Employee onboarding / profile |
| Supabase project + schema setup | Resume ingestion / AI extraction |
| Django Admin panel — Add / manage HR users | Semantic search |
| HR login via Next.js frontend | Employee login (same code path, different role) |
| HR lands on a placeholder dashboard after login | Full HR dashboard features |
| Role-based routing (`/hr/*` protected, redirect `/employee/*` later) | |

---

## Stack & Tooling

| Layer | Technology | Version |
|---|---|---|
| Frontend | Next.js (App Router) | 14.x |
| Styling | Tailwind CSS + shadcn/ui | latest |
| Backend | Django + Django REST Framework | Django 5.x / DRF 3.15 |
| Admin Panel | Django Admin (built-in) | — |
| Database | Supabase (PostgreSQL 15) | cloud |
| Auth | Supabase Auth (JWT) | — |
| AI (future) | Anthropic Claude API | claude-sonnet-4-6 |
| Package mgr (FE) | pnpm | 9.x |
| Package mgr (BE) | pip + venv | — |

---

## Auth Architecture — Single Login for All Roles

HR and Employee share **exactly the same login page and auth mechanism**. Role determines where they land after login.

```
/login  →  Supabase signInWithPassword()
              ↓
        JWT contains user id
              ↓
        Backend /api/v1/auth/me/  →  returns { role: 'hr' | 'employee' }
              ↓
        middleware.ts redirects:
          role=hr       →  /hr/dashboard
          role=employee →  /employee/dashboard   (Phase 3)
          role=admin    →  blocked (admin uses Django Admin only)
```

This means the login page, Supabase client, and JWT handling code is written **once** and works for all non-admin roles.

---

## User Model Design

All users (HR + Employee, future) live in a **single table** keyed off `auth.users`. The `role` column is the only differentiator.

```
public.profiles
  id          uuid   PK → auth.users(id)
  email       text   unique
  full_name   text
  role        enum   'hr' | 'employee'          ← admin lives only in Django Admin
  is_active   bool   default true
  created_by  uuid   → profiles(id)             ← which admin added this user
  created_at  timestamptz
  updated_at  timestamptz
```

**Why admin is not in `profiles`:** The Django superuser account is managed entirely by Django's built-in auth and the Django Admin panel. It never touches Supabase Auth or the `profiles` table. Keeping them separate avoids leaking admin credentials through the public API and keeps the RLS rules simple.

---

## Directory Layout

```
TalentExe/
├── .gitignore                      ← root-level, covers both workspaces
├── .env.example                    ← committed template (all keys, no values)
├── frontend/
│   ├── .env.local.example          ← committed template
│   ├── .env.local                  ← gitignored
│   ├── package.json
│   └── src/
│       ├── app/
│       │   ├── (auth)/
│       │   │   └── login/
│       │   │       └── page.tsx        ← Shared login page (HR + Employee)
│       │   ├── hr/
│       │   │   └── dashboard/
│       │   │       └── page.tsx        ← HR placeholder dashboard
│       │   └── employee/               ← scaffold only, Phase 3
│       ├── components/
│       │   ├── ui/                     ← shadcn/ui primitives
│       │   └── auth/
│       │       └── LoginForm.tsx
│       ├── lib/
│       │   ├── supabase.ts             ← browser Supabase client
│       │   └── api.ts                  ← fetch wrapper (attaches JWT)
│       └── middleware.ts               ← role-based route protection
├── backend/
│   ├── .env.example                ← committed template
│   ├── .env                        ← gitignored
│   ├── requirements.txt
│   ├── manage.py
│   ├── project/
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── dev.py
│   │   │   └── prod.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   └── apps/
│       └── users/
│           ├── admin.py            ← registers HR/Employee model in Django Admin
│           ├── models.py           ← HrProfile / UserProfile (mirrors Supabase)
│           ├── serializers.py
│           ├── views.py            ← /api/v1/auth/me/
│           ├── urls.py
│           └── services.py        ← Supabase Admin API calls
└── docs/
    └── phase-1.md
```

---

## Environment Variables

### Root `.env.example`

```env
# ── Supabase ──────────────────────────────────────────────
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# ── Django Backend ────────────────────────────────────────
DJANGO_SECRET_KEY=
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=                       # postgres://user:pass@host:5432/db (Supabase connection string)
CORS_ALLOWED_ORIGINS=http://localhost:3000

# ── Frontend ──────────────────────────────────────────────
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# ── AI (Phase 2+) ─────────────────────────────────────────
ANTHROPIC_API_KEY=

# ── Email (Phase 2) ───────────────────────────────────────
RESEND_API_KEY=
EMAIL_FROM=noreply@talentexe.com
```

### Frontend `frontend/.env.local.example`

```env
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### Backend `backend/.env.example`

```env
DJANGO_SECRET_KEY=
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

---

## .gitignore (root)

```gitignore
# ── Environment ───────────────────────────────────────────
.env
.env.local
.env.*.local
*.env

# ── Python / Django ───────────────────────────────────────
__pycache__/
*.py[cod]
*.pyo
*.pyd
*.so
.venv/
venv/
env/
*.egg-info/
dist/
build/
.pytest_cache/
.mypy_cache/
.ruff_cache/
db.sqlite3

# ── Node / Next.js ────────────────────────────────────────
node_modules/
.next/
out/
.pnpm-store/
*.tsbuildinfo
next-env.d.ts

# ── OS / Editor ───────────────────────────────────────────
.DS_Store
Thumbs.db
.idea/
.vscode/
*.swp
*.swo
```

---

## Database Schema (Supabase / PostgreSQL)

```sql
-- ── Role enum ─────────────────────────────────────────────────────────
create type user_role as enum ('hr', 'employee');
-- Note: 'admin' is intentionally excluded — admin lives only in Django Admin

-- ── Profiles table ────────────────────────────────────────────────────
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

-- ── Auto-update updated_at ────────────────────────────────────────────
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

-- ── RLS Policies ──────────────────────────────────────────────────────
alter table public.profiles enable row level security;

-- Any authenticated user can read their own profile
create policy "self_read"
on public.profiles for select
using (auth.uid() = id);

-- Service role (used by Django backend) bypasses RLS — handled by using
-- SUPABASE_SERVICE_ROLE_KEY in the backend, not the anon key.
-- No additional policies needed for backend-initiated writes.
```

---

## Backend — Django Admin

The Django Admin panel is the **entire admin interface** for Phase 1. No custom admin frontend is built.

### What Admin Can Do in Phase 1 (Django Admin)

- Create HR users: fills in email, full name — backend calls Supabase Admin API to create the `auth.users` record and inserts a row in `public.profiles` with `role = 'hr'`
- List / search / filter HR users
- Toggle `is_active` on any user
- Delete users (soft or hard)

### Django Admin Registration (`apps/users/admin.py`)

```python
# apps/users/admin.py
from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('email', 'full_name', 'role', 'is_active', 'created_at')
    list_filter   = ('role', 'is_active')
    search_fields = ('email', 'full_name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    def save_model(self, request, obj, form, change):
        # On create: call Supabase Admin API to create auth user first
        if not change:
            from .services import create_supabase_user
            supabase_id = create_supabase_user(obj.email, obj.full_name, obj.role)
            obj.id = supabase_id
        super().save_model(request, obj, form, change)
```

### API Endpoint (for frontend use)

```
GET  /api/v1/auth/me/
Authorization: Bearer <supabase-jwt>

Response 200:
{
  "data": {
    "id": "<uuid>",
    "email": "hr@company.com",
    "full_name": "Jane Smith",
    "role": "hr",
    "is_active": true
  },
  "error": null,
  "meta": {}
}
```

This is the only API call the frontend makes immediately after login — it fetches the role and drives the redirect.

### Python Dependencies (`backend/requirements.txt`)

```
django==5.0.6
djangorestframework==3.15.2
django-environ==0.11.2
django-cors-headers==4.4.0
psycopg2-binary==2.9.9
supabase==2.5.0
PyJWT==2.8.0
cryptography==42.0.8
gunicorn==22.0.0
```

---

## Frontend — Key Deliverables

### Pages

| Route | Auth required | Description |
|---|---|---|
| `/login` | No | Shared login page for HR + Employee |
| `/hr/dashboard` | Yes (role=hr) | Placeholder HR dashboard |
| `/employee/dashboard` | Yes (role=employee) | Scaffold only — Phase 3 |

### Login Flow (step-by-step)

1. User enters email + password on `/login`.
2. `supabase.auth.signInWithPassword()` → returns session with JWT.
3. Session cookie set by `@supabase/ssr`.
4. Frontend calls `GET /api/v1/auth/me/` with the JWT.
5. Backend validates JWT, queries `public.profiles`, returns `{ role }`.
6. `middleware.ts` reads role from cookie/session and routes:
   - `hr` → `/hr/dashboard`
   - `employee` → `/employee/dashboard`
   - unknown / error → back to `/login`

### middleware.ts Logic

```typescript
// Protect /hr/* → must be role=hr
// Protect /employee/* → must be role=employee
// /login → redirect to dashboard if already authenticated
// /admin/* → always redirect to /login (admin never uses Next.js)
```

---

## Agent Responsibilities

| Agent | Phase 1 Tasks |
|---|---|
| `django-supabase-backend-dev` | Django scaffold, settings, `users` app, Django Admin registration, custom Supabase JWT auth class, `GET /api/v1/auth/me/` endpoint, `create_supabase_user` service function |
| `nextjs-frontend-dev` | Next.js scaffold, Tailwind + shadcn/ui, login page, `middleware.ts` with role routing, HR dashboard placeholder, Supabase client setup, API fetch wrapper |

---

## Phase 1 Checklist

### Setup
- [ ] Initialize git repo at root (`git init`)
- [ ] Create root `.gitignore`
- [ ] Create `.env.example` (root, frontend, backend)

### Database (Supabase)
- [ ] Create Supabase project, note URL + keys
- [ ] Run Phase 1 SQL schema (profiles table + RLS + trigger)
- [ ] Create admin Django superuser (`python manage.py createsuperuser`)

### Backend
- [ ] Django project scaffold (`settings/base.py`, `dev.py`, `prod.py`)
- [ ] `apps/users/` app with `UserProfile` model
- [ ] Custom DRF authentication class (validates Supabase JWT)
- [ ] Django Admin registration with `save_model` hook to Supabase
- [ ] `GET /api/v1/auth/me/` endpoint
- [ ] CORS configured for `localhost:3000`
- [ ] `requirements.txt` committed

### Frontend
- [ ] Next.js 14 App Router scaffold
- [ ] Tailwind CSS + shadcn/ui configured
- [ ] Supabase browser client (`@supabase/ssr`)
- [ ] `/login` page — email + password form
- [ ] `middleware.ts` — role-based protection and redirect
- [ ] `GET /api/v1/auth/me/` call after login to resolve role
- [ ] `/hr/dashboard` placeholder page (just a welcome message)
- [ ] `/employee/dashboard` route scaffold (empty, protected)
- [ ] Logout button on dashboard

---

## Phase 2 Preview

- Admin adds HR → backend sends invite email via Resend
- HR clicks link → sets their password → lands on dashboard
- HR dashboard becomes functional (view/edit employee profiles)

---

## Running Locally

```bash
# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in real values
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver    # http://localhost:8000
# Admin panel: http://localhost:8000/admin/

# 2. Frontend (new terminal)
cd frontend
pnpm install
cp .env.local.example .env.local   # fill in real values
pnpm dev                           # http://localhost:3000
```

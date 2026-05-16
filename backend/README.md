# TalentExe — Backend

Django 5 + Django REST Framework backend for TalentExe. Connects to Supabase (PostgreSQL + pgvector) and validates Supabase JWTs for API authentication.

---

## Stack

| | |
|---|---|
| Framework | Django 5.0.6 + DRF 3.15 |
| Database | Supabase (PostgreSQL 15 + pgvector) via psycopg2 |
| Auth | Supabase JWT (validated in custom DRF auth class) |
| LLM | Ollama `llama3.2:3b` — extraction + match scoring |
| Embeddings | Ollama `nomic-embed-text` 768-dim — semantic search |
| Vector search | pgvector cosine similarity (`<=>` operator) |
| PDF generation | WeasyPrint |
| Email | Brevo SMTP (or Gmail SMTP) |
| Python | 3.11+ |

---

## Project Structure

```
backend/
├── manage.py
├── requirements.txt
├── .env                        ← gitignored, real secrets
├── .env.example                ← committed template
├── project/
│   ├── settings/
│   │   ├── base.py             ← shared settings
│   │   ├── dev.py              ← local dev (DEBUG=True)
│   │   └── prod.py             ← production
│   ├── urls.py
│   └── wsgi.py
└── apps/
    ├── users/                  ← user management, JWT auth, welcome emails
    │   ├── models.py           ← UserProfile (mirrors public.profiles in Supabase)
    │   ├── admin.py            ← Django Admin with Supabase user creation hook
    │   ├── authentication.py   ← SupabaseJWTAuthentication (custom DRF class)
    │   ├── serializers.py
    │   ├── views.py
    │   ├── urls.py
    │   ├── services.py         ← Supabase Admin API calls
    │   └── management/
    │       └── commands/
    │           └── seed_employees.py  ← seed demo employee data
    ├── profiles/               ← employee profile, resume upload, normalized tables
    │   ├── models.py           ← EmployeeProfile, Skill, Experience, Project, …
    │   ├── serializers.py
    │   ├── views.py
    │   ├── urls.py
    │   └── pdf.py              ← WeasyPrint PDF generation
    ├── reviews/                ← HR review queue (approve / reject)
    │   ├── models.py
    │   ├── serializers.py
    │   ├── views.py
    │   └── urls.py
    ├── auth_ext/               ← password change / reset
    │   ├── views.py
    │   └── urls.py
    ├── dashboard/              ← HR dashboard stat counts
    │   ├── views.py
    │   └── urls.py
    └── ai_integration/         ← AI pipeline: extraction, embeddings, NLP search
        ├── views.py
        ├── urls.py
        ├── pipeline.py         ← resume / LinkedIn extraction orchestration
        ├── extractor.py        ← Ollama LLM entity extraction
        ├── embedder.py         ← Ollama nomic-embed-text vector generation
        ├── searcher.py         ← pgvector cosine search + hard filters
        ├── explainer.py        ← Ollama LLM match scoring + explanation
        ├── profile_text_builder.py  ← serialize profile → text for embedding
        ├── text_extractor.py   ← PDF/DOCX → raw text
        └── linkedin_scraper.py ← LinkedIn URL → raw text
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

# 3. Copy env template and fill in values
cp .env.example .env

# 4. Run Django migrations
python manage.py migrate

# 5. Create a superuser for Django Admin
python manage.py createsuperuser

# 6. (Optional) Seed demo employee data
python manage.py seed_employees

# 7. Start the dev server
python manage.py runserver
# → http://localhost:8000
# → http://localhost:8000/admin/
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `DJANGO_SECRET_KEY` | Django secret key |
| `DJANGO_DEBUG` | `True` for local dev |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hosts |
| `DATABASE_URL` | Full postgres connection URL |
| `DB_HOST` | Supabase pooler host |
| `DB_PORT` | `5432` |
| `DB_NAME` | `postgres` |
| `DB_USER` | Supabase user (e.g. `postgres.<project-ref>`) |
| `DB_PASSWORD` | Supabase database password |
| `SUPABASE_URL` | `https://<project-ref>.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key (bypasses RLS) |
| `SUPABASE_ANON_KEY` | Supabase anon key |
| `SUPABASE_STORAGE_BUCKET_RESUMES` | Storage bucket name for resumes (default: `resumes`) |
| `SUPABASE_STORAGE_BUCKET_AVATARS` | Storage bucket name for avatars (default: `avatars`) |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000` for local dev |
| `FRONTEND_URL` | Frontend base URL (used in email links) |
| `BREVO_SMTP_HOST` | SMTP host (e.g. `smtp-relay.brevo.com`) |
| `BREVO_SMTP_PORT` | SMTP port (e.g. `587`) |
| `BREVO_SMTP_USER` | SMTP username |
| `BREVO_SMTP_PASSWORD` | SMTP password / API key |
| `EMAIL_FROM` | From address for outbound emails |
| `EMAIL_FROM_NAME` | Display name for outbound emails |
| `OLLAMA_BASE_URL` | Ollama server URL (default: `http://localhost:11434`) |
| `OLLAMA_LLM_MODEL` | LLM model for extraction + scoring (default: `llama3.2:3b`) |
| `OLLAMA_EMBED_MODEL` | Embedding model for search (default: `nomic-embed-text`) |
| `SEARCH_MAX_RESULTS` | Max candidates returned by NLP search (default: `20`) |
| `ANTHROPIC_API_KEY` | Optional — only needed if using Claude API directly |

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/auth/me/` | Authenticated | Current user profile + role |
| `POST` | `/api/v1/auth/change-password/` | Authenticated | Change password |
| `POST` | `/api/v1/auth/forgot-password/` | Public | Send password reset email |
| `GET` | `/api/v1/users/` | HR | List employees |
| `POST` | `/api/v1/users/` | HR | Create employee (sends welcome email) |
| `GET` | `/api/v1/profiles/{id}/` | HR or self | Full employee profile |
| `PATCH` | `/api/v1/profiles/{id}/` | HR or self | Update profile fields |
| `POST` | `/api/v1/profiles/{id}/resume/` | HR or self | Upload resume (PDF/DOCX) |
| `POST` | `/api/v1/profiles/{id}/submit-review/` | Employee | Submit profile for HR review |
| `GET` | `/api/v1/profiles/{id}/download/` | HR | Download profile as PDF |
| `POST` | `/api/v1/profiles/{id}/generate-embedding/` | HR | Generate / refresh vector embedding |
| `GET` | `/api/v1/reviews/` | HR | List pending reviews |
| `POST` | `/api/v1/reviews/{id}/approve/` | HR | Approve profile → auto-generates embedding |
| `POST` | `/api/v1/reviews/{id}/reject/` | HR | Reject with comment |
| `GET` | `/api/v1/dashboard/stats/` | HR | Dashboard stat counts |
| `POST` | `/api/v1/ai/extract/{resume_upload_id}/` | HR or self | Trigger AI extraction for a resume |
| `GET` | `/api/v1/ai/extractions/{profile_id}/` | HR or self | Get latest extraction status + JSON |
| `POST` | `/api/v1/ai/extract-linkedin/` | Employee | Extract profile from LinkedIn URL |
| `POST` | `/api/v1/search/` | HR | Semantic NLP search — ranked results with scores |

---

## Authentication Architecture

All API requests must carry a Supabase JWT:

```
supabase.auth.signInWithPassword()
  → returns access_token (JWT)
  → Frontend sends: Authorization: Bearer <access_token>
  → SupabaseJWTAuthentication decodes JWT, extracts sub (UUID)
  → Looks up UserProfile by that UUID
  → Returns (profile, token) tuple to DRF
```

`UserProfile.id` is the same UUID as `auth.users.id` in Supabase — no join needed.

---

## Django Admin

Access at `http://localhost:8000/admin/` with your superuser credentials.

- **Create HR users** — backend calls the Supabase Admin API to create an `auth.users` record, then saves a `profiles` row with `role = 'hr'`
- **List / search / filter** users by role and active status
- **Toggle `is_active`** to enable/disable access

> Note: Deleting a user here does not delete them from Supabase Auth. Use the Supabase dashboard for full deletion.

---

## Supabase — One-time SQL Setup

Run in the Supabase SQL editor:

```sql
-- Enable pgvector
create extension if not exists vector;

-- Set embedding column to 768 dims (nomic-embed-text)
ALTER TABLE employee_embeddings ALTER COLUMN embedding TYPE vector(768);
```

Also create two Storage buckets:
- `resumes` — private
- `avatars` — public

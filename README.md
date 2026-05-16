# TalentExe — Skills Intelligence Platform

A full-stack AI-powered skills intelligence platform that helps HR teams discover, search, and manage developer talent inside their organisation. Built for a hackathon.

---

## What It Does

| Role | Capabilities |
|------|-------------|
| **HR** | Add & manage employees, review submitted profiles, search talent using natural language, download PDF profiles |
| **Employee** | Build a skills profile, upload resume or import via LinkedIn, submit for HR review, track approval status |

The two core AI problems this platform solves:

1. **Smart Profile Ingestion** — upload a resume (PDF/DOCX) or paste a LinkedIn URL; Ollama (`llama3.2:3b`) extracts structured skills, experience, certifications, and projects automatically. Extracted data goes into a review queue before being accepted.
2. **Semantic NLP Search** — HR asks questions in plain English ("Find a senior React developer with WebSocket experience in Pune") and gets ranked, explained results with match scores — powered by `nomic-embed-text` vector embeddings + pgvector cosine similarity.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (App Router) + TypeScript |
| Styling | Tailwind CSS + shadcn/ui |
| Backend | Django 5 + Django REST Framework |
| Database | Supabase (PostgreSQL 15 + pgvector) |
| Auth | Supabase Auth (JWT) |
| LLM — extraction + scoring | Ollama `llama3.2:3b` (runs locally) |
| Embeddings — semantic search | Ollama `nomic-embed-text` 768-dim (runs locally) |
| Vector search | pgvector cosine similarity (`<=>` operator) |
| File Storage | Supabase Storage |
| Email | Brevo SMTP (or Gmail SMTP) |
| PDF Generation | WeasyPrint |
| Frontend pkg mgr | pnpm |

---

## Project Structure

```
TalentExe/
├── frontend/                   # Next.js App Router frontend
│   └── src/
│       ├── app/
│       │   ├── hr/             # HR portal (dashboard, employees, search, reviews)
│       │   ├── employee/       # Employee portal (profile, status)
│       │   └── (auth)/         # Login, forgot/reset password
│       ├── components/
│       │   ├── search/         # NlpSearchBox, SearchResults
│       │   ├── profile/        # Skills, Experience, Projects editors
│       │   ├── employees/      # EmployeeTable, BulkUpload
│       │   └── ui/             # shadcn primitives
│       └── lib/                # Supabase client, API fetch wrapper
├── backend/                    # Django backend
│   ├── apps/
│   │   ├── users/              # User management, JWT auth, welcome emails
│   │   ├── profiles/           # Employee profile, resume upload, normalized tables
│   │   ├── reviews/            # HR review queue (approve / reject)
│   │   ├── auth_ext/           # Password change / reset
│   │   ├── dashboard/          # HR dashboard stats
│   │   └── ai_integration/     # AI pipeline: extraction, embeddings, NLP search
│   └── project/                # Django settings (base / dev / prod)
└── docs/                       # Phase design documents + NLP guide
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+ and pnpm
- A [Supabase](https://supabase.com) project with pgvector enabled
- [Ollama](https://ollama.com) installed and running locally
- A [Brevo](https://brevo.com) account (or Gmail) for email

---

### 1. Clone the repo

```bash
git clone <repo-url>
cd TalentExe
```

---

### 2. Ollama Setup (AI — required for extraction + search)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh   # Linux
# or download from https://ollama.com for Mac/Windows

# Start the Ollama server
ollama serve &

# Pull the two required models
ollama pull llama3.2:3b        # LLM — resume extraction + match scoring
ollama pull nomic-embed-text   # Embedding model — vector search (768 dims)
```

---

### 3. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Fill in .env with your Supabase credentials (see Environment Variables below)

# Run migrations
python manage.py migrate

# Create Django superuser (admin panel access)
python manage.py createsuperuser

# Start the backend
python manage.py runserver      # http://localhost:8000
```

---

### 4. Supabase — One-time SQL setup

Run the following in the Supabase SQL editor:

```sql
-- Enable pgvector extension
create extension if not exists vector;

-- Alter embedding column to 768 dims (nomic-embed-text)
ALTER TABLE employee_embeddings ALTER COLUMN embedding TYPE vector(768);
```

Also create two Storage buckets:
- `resumes` — private
- `avatars` — public

---

### 5. Frontend Setup

```bash
cd frontend

# Install dependencies
pnpm install

# Configure environment
cp .env.local.example .env.local
# Fill in .env.local with your Supabase keys

# Start the frontend
pnpm dev                        # http://localhost:3000
```

---

## Environment Variables

### `backend/.env`

```env
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Supabase
DATABASE_URL=postgres://user:pass@host:5432/db
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_ANON_KEY=your-anon-key

# CORS + Frontend
CORS_ALLOWED_ORIGINS=http://localhost:3000
FRONTEND_URL=http://localhost:3000

# Supabase Storage
SUPABASE_STORAGE_BUCKET_RESUMES=resumes
SUPABASE_STORAGE_BUCKET_AVATARS=avatars

# Email (Brevo SMTP or Gmail)
BREVO_SMTP_HOST=smtp-relay.brevo.com
BREVO_SMTP_PORT=587
BREVO_SMTP_USER=your-brevo-email
BREVO_SMTP_PASSWORD=your-smtp-key
EMAIL_FROM=noreply@yourdomain.com
EMAIL_FROM_NAME=TalentExe

# Ollama — LLM for extraction + scoring (runs locally, no API key)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=llama3.2:3b

# Ollama — dedicated embedding model for NLP search (768 dims)
OLLAMA_EMBED_MODEL=nomic-embed-text

# Search tuning
SEARCH_MAX_RESULTS=20

# Anthropic (optional — leave blank if not using Claude API directly)
ANTHROPIC_API_KEY=
```

### `frontend/.env.local`

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_MAX_RESUME_SIZE_MB=10
```

---

## Auth Flow

All users (HR + Employee) share the same login page. Role determines where they land.

```
/login  →  Supabase signInWithPassword()
                ↓
           JWT issued
                ↓
         GET /api/v1/auth/me/  →  { role, must_change_password }
                ↓
    role=hr       →  /hr/dashboard
    role=employee →  /employee/profile
    must_change_password=true  →  /set-password
```

---

## Key API Endpoints

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

## NLP Search

HR types any plain-English query (3+ words) into the Smart Search box:

```
"Find a senior React developer with fintech experience"
"Backend engineer in Pune with 5 years Java and payment gateway"
"Data scientist who knows Python and machine learning"
```

**Pipeline:**
1. `llama3.2:3b` parses the query → structured intent (skills, location, min years)
2. `nomic-embed-text` embeds the query → 768-dim vector
3. pgvector cosine search against all approved profile embeddings
4. Hard filters applied (location, min years, department)
5. `llama3.2:3b` scores each result 0–100 and writes a plain-English explanation
6. Results ranked by match score, filtered to score ≥ 60

> **Note:** Only employees with `profile_status = 'approved'` appear in search results. Embeddings are auto-generated when HR approves a profile.

---

## Features by Role

### HR Portal (`/hr/*`)
- **Dashboard** — stat cards: total employees, pending reviews, incomplete profiles, top skills
- **Employee List** — searchable table with pagination; add, edit, bulk upload via JSON/Excel
- **Smart Search** — NLP queries with AI-ranked results, match score badges, and plain-English explanations
- **Review Queue** — approve or reject submitted profiles with comments
- **Profile Preview** — full profile view with skills, experience, projects, certifications
- **PDF Download** — generate and download a formatted PDF of any employee profile

### Employee Portal (`/employee/*`)
- **Profile Editor** — manage skills (proficiency + years), experience, projects, certifications, education, languages, links
- **Resume Upload** — PDF/DOCX up to 10 MB; Ollama extracts structured data automatically
- **LinkedIn Import** — paste a LinkedIn profile URL to auto-fill profile via AI extraction
- **Submit for Review** — send profile to HR for approval
- **Profile Status** — view approval status, HR comments, and submission timeline

---

## Docs

| Document | Description |
|----------|-------------|
| [docs/problemStatement.md](docs/problemStatement.md) | Problem overview and hackathon goals |
| [docs/NLP.md](docs/NLP.md) | NLP search design — embeddings, pipeline, scoring, accuracy |
| [docs/phase-1.md](docs/phase-1.md) | Foundation, auth, Django Admin setup |
| [docs/phase-2.md](docs/phase-2.md) | User management, HR dashboard, employee portal |
| [docs/phase-2.1.md](docs/phase-2.1.md) | Normalized schema — skills, experience, projects, certifications |
| [docs/phase-3.md](docs/phase-3.md) | AI ingestion pipeline and semantic search implementation |

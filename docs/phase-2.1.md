# Phase 2.1 — Normalized Schema & Tabbed Profile UI

## Objective

Replace the JSONB-based `employee_profiles` columns with fully normalized relational tables.
This is required to support semantic search, AI ranking, and skill normalization in Phase 3.
No AI logic is wired up in this phase — tables are created ready for Phase 3.

---

## What Changes

| Before (Phase 2) | After (Phase 2.1) |
|---|---|
| `employee_profiles.skills` — JSONB array | `employee_skills` table → `skills_master` FK |
| `employee_profiles.projects` — JSONB array | `projects` + `project_skills` tables |
| `employee_profiles.certifications` — JSONB array | `certifications` table |
| `employee_profiles.education` — JSONB array | `education` table |
| Single flat profile page | Tabbed profile page (Overview / Skills / Experience / Projects / Certifications / Education) |
| `employee_experiences` — missing | `employee_experiences` table added |

`employee_profiles` is kept but stripped to: `summary`, `linkedin_url`, `github_url`, `portfolio_url`, `languages` (JSONB).

---

## Database Schema

Run in Supabase SQL editor **after** Phase 2 schema.

```sql
-- ══════════════════════════════════════════════════════════════════
-- Phase 2.1 — Normalized Skills / Experience / Projects / Certs / Education
-- ══════════════════════════════════════════════════════════════════

-- 1. skills_master — canonical skill catalog for normalization + AI search
CREATE TABLE public.skills_master (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name        varchar(255) NOT NULL UNIQUE,
  category    varchar(100),
  aliases     text[],
  description text,
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- Seed common tech skills
INSERT INTO public.skills_master (name, category, aliases) VALUES
  ('React',       'Frontend',  ARRAY['ReactJS', 'React.js']),
  ('Next.js',     'Frontend',  ARRAY['NextJS']),
  ('TypeScript',  'Language',  ARRAY['TS']),
  ('JavaScript',  'Language',  ARRAY['JS', 'ES6']),
  ('Node.js',     'Backend',   ARRAY['NodeJS', 'Node']),
  ('Python',      'Language',  ARRAY['py']),
  ('Django',      'Backend',   ARRAY[]::text[]),
  ('FastAPI',     'Backend',   ARRAY[]::text[]),
  ('PostgreSQL',  'Database',  ARRAY['Postgres', 'psql']),
  ('MySQL',       'Database',  ARRAY[]::text[]),
  ('MongoDB',     'Database',  ARRAY['Mongo']),
  ('Redis',       'Database',  ARRAY[]::text[]),
  ('AWS',         'Cloud',     ARRAY['Amazon Web Services']),
  ('Docker',      'DevOps',    ARRAY[]::text[]),
  ('Kubernetes',  'DevOps',    ARRAY['K8s']),
  ('Java',        'Language',  ARRAY[]::text[]),
  ('Spring Boot', 'Backend',   ARRAY['Spring']),
  ('Go',          'Language',  ARRAY['Golang']),
  ('GraphQL',     'API',       ARRAY[]::text[]),
  ('REST',        'API',       ARRAY['REST API']),
  ('Socket.IO',   'Realtime',  ARRAY['WebSockets']),
  ('Supabase',    'BaaS',      ARRAY[]::text[]),
  ('Git',         'Tools',     ARRAY[]::text[]),
  ('CI/CD',       'DevOps',    ARRAY[]::text[])
ON CONFLICT (name) DO NOTHING;

-- 2. employee_skills — normalized many-to-many: profile ↔ skill
CREATE TABLE public.employee_skills (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id          uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  skill_id            uuid NOT NULL REFERENCES public.skills_master(id),
  proficiency_level   varchar(20) NOT NULL DEFAULT 'Intermediate'
                        CHECK (proficiency_level IN ('Beginner','Intermediate','Expert')),
  years_of_experience numeric(4,1),
  last_used_at        date,
  is_primary          boolean NOT NULL DEFAULT false,
  source              varchar(30) NOT NULL DEFAULT 'manual'
                        CHECK (source IN ('manual','ai_extracted','inferred')),
  confidence_score    numeric(3,2),
  verified_by_hr      boolean NOT NULL DEFAULT false,
  created_at          timestamptz NOT NULL DEFAULT now(),
  UNIQUE (profile_id, skill_id)
);

-- 3. employee_experiences — work history
CREATE TABLE public.employee_experiences (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id      uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  company_name    varchar(255) NOT NULL,
  designation     varchar(255) NOT NULL,
  employment_type varchar(50),
  start_date      date NOT NULL,
  end_date        date,
  is_current      boolean NOT NULL DEFAULT false,
  location        varchar(255),
  description     text,
  created_at      timestamptz NOT NULL DEFAULT now()
);

-- 4. projects — professional projects
CREATE TABLE public.projects (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id  uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  name        varchar(255) NOT NULL,
  client_name varchar(255),
  description text,
  role        varchar(255),
  team_size   integer,
  start_date  date,
  end_date    date,
  is_current  boolean NOT NULL DEFAULT false,
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- 5. project_skills — skills used in each project (for semantic search)
CREATE TABLE public.project_skills (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  skill_id   uuid NOT NULL REFERENCES public.skills_master(id),
  UNIQUE (project_id, skill_id)
);

-- 6. certifications
CREATE TABLE public.certifications (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id     uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  name           varchar(255) NOT NULL,
  issuer         varchar(255),
  issue_date     date,
  expiry_date    date,
  credential_url text,
  created_at     timestamptz NOT NULL DEFAULT now()
);

-- 7. education
CREATE TABLE public.education (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id  uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  degree      varchar(255) NOT NULL,
  institution varchar(255) NOT NULL,
  start_year  integer,
  end_year    integer,
  grade       varchar(50),
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- ── Migrate employee_profiles — drop JSONB columns ────────────────────────────
-- WARNING: This drops existing Phase 2 JSONB data. Export before running if needed.
ALTER TABLE public.employee_profiles
  DROP COLUMN IF EXISTS skills,
  DROP COLUMN IF EXISTS certifications,
  DROP COLUMN IF EXISTS projects,
  DROP COLUMN IF EXISTS education;
-- Kept: summary, languages (JSONB), linkedin_url, github_url, portfolio_url

-- ── Update resume_uploads — add extraction_status for Phase 3 AI pipeline ────
ALTER TABLE public.resume_uploads
  ADD COLUMN IF NOT EXISTS extraction_status varchar(20) NOT NULL DEFAULT 'pending'
    CHECK (extraction_status IN ('pending','processing','completed','failed'));

-- ══════════════════════════════════════════════════════════════════
-- AI Placeholder Tables (tables only — no logic in Phase 2.1)
-- ══════════════════════════════════════════════════════════════════

-- 8. ai_profile_extractions — stores raw AI extraction output for audit + retry
CREATE TABLE public.ai_profile_extractions (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id            uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  resume_upload_id      uuid REFERENCES public.resume_uploads(id) ON DELETE SET NULL,
  raw_text              text,
  extracted_json        jsonb,
  model_name            varchar(100),
  extraction_confidence numeric(3,2),
  status                varchar(20) NOT NULL DEFAULT 'pending'
                          CHECK (status IN ('pending','processing','completed','failed')),
  created_at            timestamptz NOT NULL DEFAULT now()
);

-- 9. inferred_skills — AI-inferred skill relationships (e.g. Next.js → React)
CREATE TABLE public.inferred_skills (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id        uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  source_skill_id   uuid NOT NULL REFERENCES public.skills_master(id),
  inferred_skill_id uuid NOT NULL REFERENCES public.skills_master(id),
  confidence_score  numeric(3,2) NOT NULL,
  inference_reason  text,
  created_at        timestamptz NOT NULL DEFAULT now()
);

-- 10. employee_embeddings — pgvector embeddings for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE public.employee_embeddings (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id     uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  embedding_type varchar(50) NOT NULL DEFAULT 'profile',
  embedding      vector(1536),
  searchable_text text,
  updated_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (profile_id, embedding_type)
);

-- ── RLS ───────────────────────────────────────────────────────────────────────
ALTER TABLE public.skills_master          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.employee_skills        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.employee_experiences   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects               ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.project_skills         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.certifications         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.education              ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_profile_extractions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inferred_skills        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.employee_embeddings    ENABLE ROW LEVEL SECURITY;

-- skills_master is readable by all authenticated users
CREATE POLICY "skills_master_read"
  ON public.skills_master FOR SELECT USING (true);

-- Employees can read their own normalized data
CREATE POLICY "employee_own_skills"
  ON public.employee_skills FOR SELECT USING (profile_id = auth.uid());

CREATE POLICY "employee_own_experiences"
  ON public.employee_experiences FOR SELECT USING (profile_id = auth.uid());

CREATE POLICY "employee_own_projects"
  ON public.projects FOR SELECT USING (profile_id = auth.uid());

CREATE POLICY "employee_own_certifications"
  ON public.certifications FOR SELECT USING (profile_id = auth.uid());

CREATE POLICY "employee_own_education"
  ON public.education FOR SELECT USING (profile_id = auth.uid());

-- Backend service role (Django) bypasses RLS for all writes.
```

---

## Relationship Diagram

```
profiles
 ├── employee_profiles          (summary, languages, links — Phase 2 remnant)
 ├── employee_experiences       (work history — NEW)
 ├── employee_skills            (many-to-many with skills_master — NEW)
 │      └── skills_master       (canonical skill catalog — NEW)
 ├── projects                   (NEW)
 │      └── project_skills      (many-to-many with skills_master — NEW)
 ├── certifications             (NEW)
 ├── education                  (NEW)
 ├── resume_uploads             (Phase 2 + extraction_status column added)
 │      └── ai_profile_extractions  (AI placeholder — NEW)
 ├── profile_reviews            (Phase 2 — unchanged)
 ├── inferred_skills            (AI placeholder — NEW)
 └── employee_embeddings        (AI placeholder — NEW)
```

---

## New API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/skills/` | List all skills in master catalog |
| `POST` | `/api/v1/skills/` | Create skill in catalog (get-or-create by name) |
| `GET` | `/api/v1/profiles/{id}/skills/` | List employee skills |
| `POST` | `/api/v1/profiles/{id}/skills/` | Add skill to employee profile |
| `PATCH` | `/api/v1/profiles/{id}/skills/{sk}/` | Update skill (proficiency, years) |
| `DELETE` | `/api/v1/profiles/{id}/skills/{sk}/` | Remove skill |
| `GET` | `/api/v1/profiles/{id}/experiences/` | List work experiences |
| `POST` | `/api/v1/profiles/{id}/experiences/` | Add experience |
| `PATCH` | `/api/v1/profiles/{id}/experiences/{ek}/` | Update experience |
| `DELETE` | `/api/v1/profiles/{id}/experiences/{ek}/` | Delete experience |
| `GET` | `/api/v1/profiles/{id}/projects/` | List projects |
| `POST` | `/api/v1/profiles/{id}/projects/` | Add project |
| `PATCH` | `/api/v1/profiles/{id}/projects/{pk}/` | Update project |
| `DELETE` | `/api/v1/profiles/{id}/projects/{pk}/` | Delete project |
| `GET` | `/api/v1/profiles/{id}/certifications/` | List certifications |
| `POST` | `/api/v1/profiles/{id}/certifications/` | Add certification |
| `PATCH` | `/api/v1/profiles/{id}/certifications/{ck}/` | Update certification |
| `DELETE` | `/api/v1/profiles/{id}/certifications/{ck}/` | Delete certification |
| `GET` | `/api/v1/profiles/{id}/education/` | List education entries |
| `POST` | `/api/v1/profiles/{id}/education/` | Add education |
| `PATCH` | `/api/v1/profiles/{id}/education/{ek}/` | Update education |
| `DELETE` | `/api/v1/profiles/{id}/education/{ek}/` | Delete education |

Existing endpoints unchanged:
- `GET/PATCH /api/v1/profiles/{id}/` — user fields + employee basic fields (summary, languages, links)
- `POST/GET /api/v1/profiles/{id}/resume/` — unchanged
- `POST /api/v1/profiles/{id}/submit-review/` — unchanged
- `GET /api/v1/profiles/{id}/download/` — PDF (updated to read normalized tables)

---

## Frontend Changes

`/employee/profile` converts from a single-column card stack to a **tabbed layout**:

```
[Overview]  [Skills]  [Experience]  [Projects]  [Certifications]  [Education]
```

- **Overview** — Basic Info (designation, dept, location, exp years), Contact (email, phone), Summary, Links
- **Skills** — SkillsEditor reading/writing `/api/v1/profiles/{id}/skills/`
- **Experience** — ExperienceEditor reading/writing `/api/v1/profiles/{id}/experiences/`
- **Projects** — ProjectsEditor reading/writing `/api/v1/profiles/{id}/projects/`
- **Certifications** — CertificationsEditor reading/writing `/api/v1/profiles/{id}/certifications/`
- **Education** — EducationEditor reading/writing `/api/v1/profiles/{id}/education/`

Each tab independently fetches and saves its own data. The top header card (avatar, name, status badge) and the Import + Submit for Review cards remain outside the tabs.

---

## Phase 2.1 Checklist

### Database
- [ ] Run Phase 2.1 SQL migration in Supabase
- [ ] Verify `skills_master` seeded with common skills
- [ ] Verify JSONB columns dropped from `employee_profiles`
- [ ] Verify AI placeholder tables created (`ai_profile_extractions`, `inferred_skills`, `employee_embeddings`)

### Backend
- [ ] Add new models: `SkillMaster`, `EmployeeSkill`, `EmployeeExperience`, `Project`, `ProjectSkill`, `Certification`, `Education`
- [ ] Add AI placeholder models: `AIProfileExtraction`, `InferredSkill`, `EmployeeEmbedding`
- [ ] Update `EmployeeProfile` model — remove JSONB fields
- [ ] Update `ResumeUpload` model — add `extraction_status`
- [ ] Add serializers for all new models
- [ ] Add section views (skills, experiences, projects, certifications, education)
- [ ] Add `SkillsMasterView` for catalog lookup
- [ ] Update `ProfileDetailView` — GET no longer returns skills/projects/certs/education in `employee` key
- [ ] Update PDF generation to query normalized tables
- [ ] Update dashboard top_skills stat to query `employee_skills` → `skills_master`
- [ ] Register new URL patterns

### Frontend
- [ ] Update `types/index.ts` for new API shapes
- [ ] Convert `employee/profile/page.tsx` to tabbed layout
- [ ] Skills tab — reads/writes `/api/v1/profiles/{id}/skills/`
- [ ] Experience tab — reads/writes `/api/v1/profiles/{id}/experiences/`
- [ ] Projects tab — reads/writes `/api/v1/profiles/{id}/projects/`
- [ ] Certifications tab — reads/writes `/api/v1/profiles/{id}/certifications/`
- [ ] Education tab — reads/writes `/api/v1/profiles/{id}/education/`
- [ ] HR employee detail page updated to same tab layout

---

## Phase 3 Preview

With this schema in place, Phase 3 can:
- Generate `searchable_text` per employee and store in `employee_embeddings`
- Run cosine similarity search against `embedding` (pgvector)
- Use `inferred_skills` to boost semantically related skill matches
- Use `ai_profile_extractions` to parse uploaded resumes and auto-populate normalized tables

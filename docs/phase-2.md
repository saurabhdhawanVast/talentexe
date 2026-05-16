# Phase 2 — User Management, HR Dashboard & Employee Onboarding

## Objective

Build the full working application on top of the Phase 1 skeleton:

1. **Admin** adds HR and Employee users via a custom Next.js admin UI (or Django Admin). System sends credentials by email via **Brevo SMTP**.
2. **First-login password change** flow for all new users.
3. **Forgot password** self-service flow.
4. **Shared navbar** with profile avatar and account options.
5. **HR portal** — Dashboard, Employee List, Smart Search (UI only), Review Queue, Reports stub.
6. **Employee portal** — Profile management (manual + resume upload), Profile Status tracking.

---

## Scope Boundaries

| In Scope (Phase 2) | Deferred (Phase 3+) |
|---|---|
| Brevo SMTP email — credentials, approval, comments | AI/NLP processing of search queries |
| First-login forced password change | Resume AI data extraction / entity parsing |
| Forgot password flow | Semantic / vector search |
| Shared navbar (logo + profile menu) | Analytics charts / graphs |
| HR Dashboard with stat cards | Bench tracking automation |
| Employee List (table, filters, pagination) | LinkedIn OAuth import |
| Add Employee form + bulk upload (JSON/Excel) | |
| Smart Search — text input box only, no AI backend | |
| LinkedIn — URL text field only, no API/OAuth | |
| Resume upload — file stored as-is, no AI parsing | |
| Review Queue — approve / reject + comments | |
| Reports & Analytics page — "Coming Soon" | |
| Employee profile page (manual fields + file upload) | |
| Employee profile status + HR comments view | |
| HR views & downloads employee profile as PDF | |

---

## Stack Additions (Phase 2)

| Concern | Technology |
|---|---|
| Email | Brevo (formerly Sendinblue) — SMTP via `django.core.mail` |
| File storage | Supabase Storage — `resumes` bucket (private), `avatars` bucket (public) |
| PDF generation | `weasyprint` (backend renders HTML template → PDF) |
| Excel/CSV parsing | `openpyxl` + `pandas` (bulk upload only) |
| Frontend forms | `react-hook-form` + `zod` |
| Toast notifications | `sonner` (shadcn/ui compatible) |

> **No AI dependencies in Phase 2.** Resume files are stored as raw files. LinkedIn is a plain URL field. The NLP search box collects typed text only — no processing until Phase 3.

---

## Environment Variables

### New variables — `backend/.env.example` (already updated)

```env
# Frontend URL (used in email links)
FRONTEND_URL=http://localhost:3000

# Supabase Storage bucket names
SUPABASE_STORAGE_BUCKET_RESUMES=resumes
SUPABASE_STORAGE_BUCKET_AVATARS=avatars

# Brevo (Email via SMTP)
# Get these from: Brevo dashboard → SMTP & API → SMTP tab
BREVO_SMTP_HOST=smtp-relay.brevo.com
BREVO_SMTP_PORT=587
BREVO_SMTP_USER=          # your Brevo account email
BREVO_SMTP_PASSWORD=      # SMTP key shown in Brevo dashboard (not your account password)
EMAIL_FROM=               # verified sender address configured in Brevo
EMAIL_FROM_NAME=TalentExe
```

### New variables — `frontend/.env.local.example` (already updated)

```env
NEXT_PUBLIC_MAX_RESUME_SIZE_MB=10
```

> Copy `.env.example` → `.env` (backend) and `.env.local.example` → `.env.local` (frontend), then fill in the real values.

### Django `settings/base.py` email config block

```python
EMAIL_BACKEND      = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST         = env('BREVO_SMTP_HOST', default='smtp-relay.brevo.com')
EMAIL_PORT         = env.int('BREVO_SMTP_PORT', default=587)
EMAIL_HOST_USER    = env('BREVO_SMTP_USER')
EMAIL_HOST_PASSWORD= env('BREVO_SMTP_PASSWORD')
EMAIL_USE_TLS      = True
DEFAULT_FROM_EMAIL = f"{env('EMAIL_FROM_NAME', default='TalentExe')} <{env('EMAIL_FROM')}>"
```

---

## Database Schema Additions

Run these migrations in Supabase SQL editor after Phase 1 schema.

```sql
-- ── Extended profile fields on public.profiles ──────────────────────────
alter table public.profiles
  add column if not exists phone          text,
  add column if not exists designation    text,
  add column if not exists department     text,
  add column if not exists experience_years numeric(4,1),
  add column if not exists location       text,
  add column if not exists avatar_url     text,
  add column if not exists must_change_password boolean not null default true,
  add column if not exists profile_status text not null default 'incomplete'
    check (profile_status in ('incomplete','submitted','approved','rejected'));

-- ── Employee detail table ────────────────────────────────────────────────
create table public.employee_profiles (
  id              uuid primary key default gen_random_uuid(),
  profile_id      uuid not null references public.profiles(id) on delete cascade,
  skills          jsonb not null default '[]',   -- [{name, proficiency, years}]
  certifications  jsonb not null default '[]',   -- [{name, issuer, issued_at, expires_at}]
  projects        jsonb not null default '[]',   -- [{name, description, tech_stack[], duration}]
  education       jsonb not null default '[]',   -- [{degree, institution, year}]
  languages       jsonb not null default '[]',   -- [{name, proficiency}]
  summary         text,
  linkedin_url    text,
  github_url      text,
  portfolio_url   text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  constraint unique_profile unique (profile_id)
);

create trigger employee_profiles_updated_at
before update on public.employee_profiles
for each row execute function public.set_updated_at();

-- ── Resume uploads ───────────────────────────────────────────────────────
create table public.resume_uploads (
  id              uuid primary key default gen_random_uuid(),
  profile_id      uuid not null references public.profiles(id) on delete cascade,
  storage_path    text not null,        -- path inside Supabase Storage bucket
  original_name   text not null,
  mime_type       text not null,
  size_bytes      bigint not null,
  uploaded_at     timestamptz not null default now(),
  is_current      boolean not null default true
);

-- ── Review queue ─────────────────────────────────────────────────────────
create table public.profile_reviews (
  id              uuid primary key default gen_random_uuid(),
  profile_id      uuid not null references public.profiles(id) on delete cascade,
  reviewed_by     uuid references public.profiles(id) on delete set null,
  status          text not null default 'pending'
    check (status in ('pending','approved','rejected')),
  hr_comment      text,
  submitted_at    timestamptz not null default now(),
  reviewed_at     timestamptz
);

-- ── RLS additions ────────────────────────────────────────────────────────
alter table public.employee_profiles  enable row level security;
alter table public.resume_uploads     enable row level security;
alter table public.profile_reviews    enable row level security;

-- Employees can read their own extended profile
create policy "employee_own_profile"
on public.employee_profiles for select
using (profile_id = auth.uid());

-- Employees can read their own resume uploads
create policy "employee_own_resumes"
on public.resume_uploads for select
using (profile_id = auth.uid());

-- Employees can read their own reviews
create policy "employee_own_reviews"
on public.profile_reviews for select
using (profile_id = auth.uid());

-- Service role (Django backend) handles all writes via service role key — no
-- additional insert/update policies needed; backend bypasses RLS.
```

---

## Auth Flows

### 1. Admin Creates HR or Employee

```
Admin fills "Add User" form
  → POST /api/v1/users/   { email, full_name, role, phone?, designation?, department? }
      ↓
  backend: supabase.auth.admin.create_user(email, password=<random 12-char>)
  backend: INSERT INTO public.profiles (must_change_password=true)
  backend: send_welcome_email(email, full_name, temp_password)
      ↓
  User receives email:
    Subject: "Welcome to TalentExe — Your login credentials"
    Body: email + temp_password + link to /login
```

### 2. First-Login Forced Password Change

```
User logs in with temp credentials
  → backend /api/v1/auth/me/ returns { must_change_password: true }
  → middleware.ts redirects to /set-password
  → user enters New Password + Confirm Password
  → POST /api/v1/auth/change-password/  { new_password }
      ↓
  backend: supabase.auth.admin.update_user_by_id(password=new_password)
  backend: UPDATE profiles SET must_change_password = false
  → redirect to role dashboard
```

### 3. Forgot Password

```
/forgot-password  →  user enters email
  → POST /api/v1/auth/forgot-password/  { email }
      ↓
  backend: generate reset token, store in profiles (or use Supabase reset)
  backend: send_password_reset_email(email, reset_link)
  → user clicks link → /reset-password?token=<token>
  → user enters New Password + Confirm Password
  → POST /api/v1/auth/reset-password/  { token, new_password }
  → redirect to /login
```

---

## API Endpoints (Phase 2)

### Users

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/users/` | Admin (service) | Create HR or Employee, send welcome email |
| `GET` | `/api/v1/users/` | HR | List all users (with filters + pagination) |
| `GET` | `/api/v1/users/{id}/` | HR | Get single user details |
| `PATCH` | `/api/v1/users/{id}/` | HR | Update user fields (name, designation, etc.) |
| `DELETE` | `/api/v1/users/{id}/` | HR | Delete user |
| `POST` | `/api/v1/users/{id}/disable/` | HR | Toggle `is_active` false |
| `POST` | `/api/v1/users/{id}/resend-invite/` | HR | Re-send welcome email with new temp password |
| `POST` | `/api/v1/users/bulk-upload/` | HR | Import users from JSON or Excel file |

### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/auth/me/` | Authenticated | Returns profile + `must_change_password` |
| `POST` | `/api/v1/auth/change-password/` | Authenticated | Change password, clears `must_change_password` |
| `POST` | `/api/v1/auth/forgot-password/` | Public | Send reset email |
| `POST` | `/api/v1/auth/reset-password/` | Public (token) | Set new password via reset token |

### Employee Profiles

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/profiles/{id}/` | HR or self | Full employee profile |
| `PATCH` | `/api/v1/profiles/{id}/` | HR or self | Update skills, certs, projects, education |
| `POST` | `/api/v1/profiles/{id}/resume/` | HR or self | Upload resume file to Supabase Storage |
| `GET` | `/api/v1/profiles/{id}/resume/` | HR or self | Get signed download URL for current resume |
| `POST` | `/api/v1/profiles/{id}/submit-review/` | Employee (self) | Mark profile as submitted, create review queue entry |
| `GET` | `/api/v1/profiles/{id}/download/` | HR | Generate + return PDF of employee profile |

### Review Queue

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/reviews/` | HR | List all pending reviews |
| `POST` | `/api/v1/reviews/{id}/approve/` | HR | Approve profile, send approval email |
| `POST` | `/api/v1/reviews/{id}/reject/` | HR | Reject with comment, send rejection email |

### Dashboard Stats

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/dashboard/stats/` | HR | Returns all card counts and top skills |

---

## Frontend — Page & Route Map

```
/login                          ← Phase 1 (extended: reads must_change_password)
/set-password                   ← NEW — first-login forced change
/forgot-password                ← NEW — request reset link
/reset-password                 ← NEW — enter new password via token

/hr/
  dashboard/                    ← HR Dashboard (stat cards)
  employees/                    ← Employee List (table + filters + pagination)
  employees/new/                ← Add Employee form
  employees/[id]/               ← Employee Detail (full profile, edit, upload resume)
  search/                       ← Smart Search (NLP box + results)
  search/[id]/preview/          ← Read-only profile + Download PDF
  reviews/                      ← Review Queue
  reports/                      ← Coming Soon

/employee/
  dashboard/                    ← redirect to /employee/profile
  profile/                      ← Profile edit (resume upload + manual fields)
  profile/status/               ← Profile Status + HR comments

/set-password                   ← shared (used after first login)
```

---

## Shared Navbar

Applies to all authenticated pages (`/hr/*` and `/employee/*`).

```
┌────────────────────────────────────────────────────────────────┐
│  Talent.exe                                     [Avatar ▼]     │
└────────────────────────────────────────────────────────────────┘
                                                       │
                                               ┌───────▼───────┐
                                               │ Change Password│
                                               │ Set Profile Pic│
                                               │ ─────────────  │
                                               │ Logout         │
                                               └───────────────┘
```

- **Left:** `Talent.exe` logo/wordmark linking to role dashboard.
- **Right:** Circle avatar — shows profile picture if set, else initials on a colored background.
- Avatar dropdown: `Change Password`, `Set Profile Picture`, `Logout`.
- `Change Password` → modal with Current Password, New Password, Confirm Password.
- `Set Profile Picture` → file input (jpg/png, max 2 MB) → uploaded to Supabase Storage `avatars` bucket.

---

## HR Portal — Detailed Screens

### 1. Dashboard (`/hr/dashboard`)

Stat cards in a responsive grid:

| Card | Data source |
|---|---|
| Total Employees | `COUNT(*) FROM profiles WHERE role='employee'` |
| Pending Reviews | `COUNT(*) FROM profile_reviews WHERE status='pending'` |
| Incomplete Profiles | employees with `profile_status='incomplete'` |
| Approved Profiles | employees with `profile_status='approved'` |
| Top Skills | top 5 skills by frequency across all `employee_profiles.skills` |
| Bench Employees | employees with `profile_status='approved'` and no active project allocation |

Layout:

```
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Total Emp   │ │ Pending Rev │ │ Incomplete  │
│     42      │ │      7      │ │     12      │
└─────────────┘ └─────────────┘ └─────────────┘
┌─────────────┐ ┌─────────────────────────────┐
│ Approved    │ │ Top Skills                  │
│     23      │ │ React ████ 18               │
│             │ │ Java  ████ 14               │
│             │ │ ...                         │
└─────────────┘ └─────────────────────────────┘
```

### 2. Employee List (`/hr/employees`)

**Filters bar:**

```
[Search by name / email]  [Designation ▼]  [Department ▼]  [Experience ▼]  [Skills ▼]  [Location ▼]  [Status ▼]
```

**Table:**

| Name | Designation | Dept | Experience | Skills (top 3) | Status | Actions |
|---|---|---|---|---|---|---|
| Jane Smith | Sr. Dev | Engineering | 5 yrs | React, Node, AWS | Approved | View Edit Delete Disable Resend |

- Clicking a **row** or **View** opens `/hr/employees/[id]`.
- **Delete** shows a confirmation dialog before calling the API.
- **Disable** toggles `is_active = false`, greys out the row.
- **Resend Invite** calls `/api/v1/users/{id}/resend-invite/` and shows a toast.

**Pagination:**

```
< Previous   1  2  3  4   Next >          Showing 1–20 of 42 employees
```

**Add Employee button** → opens `/hr/employees/new` or a slide-over panel.

**Add Employee form fields:**

| Field | Required | Notes |
|---|---|---|
| Full Name | Yes | |
| Email | Yes | must be unique |
| Phone | No | |
| Designation | Yes | |
| Department | Yes | |
| Experience (years) | No | numeric |
| Location | No | |

On submit → `POST /api/v1/users/` → welcome email sent → user appears in list.

**Bulk Upload button** (beside Add Employee):
- Accepts `.json` or `.xlsx` / `.xls`.
- JSON schema: `[{ full_name, email, phone?, designation, department, experience_years?, location? }]`.
- Excel: same columns as headers in row 1.
- Backend validates each row, skips duplicates, returns a summary `{ created: N, skipped: M, errors: [...] }`.
- UI shows the summary in a modal after upload.

### 3. Employee Detail (`/hr/employees/[id]`)

Full-page employee profile. HR can view and edit all fields.

**Sections:**

1. **Header** — avatar, name, designation, department, location, status badge, `Edit` toggle.
2. **Contact** — email, phone.
3. **Summary** — free-text professional summary.
4. **Skills** — tag list. Each skill shows proficiency badge (Beginner / Intermediate / Expert) and years. HR can add, edit, or remove skills.
5. **Experience** — work history entries: company, role, start/end date, description.
6. **Projects** — project name, description, tech stack tags, duration.
7. **Education** — degree, institution, year.
8. **Certifications** — name, issuer, issue date, expiry date.
9. **Languages** — language + proficiency level.
10. **Links** — LinkedIn URL (plain text field — just stores the URL, no API call), GitHub URL, Portfolio URL.
11. **Resume** — current uploaded file name + date. `Upload Resume` button (replaces current). Download link for current resume. File is stored as-is in Supabase Storage — no AI parsing in Phase 2.

**Upload Resume validation:**
- Accepted: `.pdf`, `.doc`, `.docx`
- Max size: 10 MB
- Client-side check before upload; server also validates MIME type and size.
- File stored in Supabase Storage `resumes` bucket under path `{profile_id}/{uuid}_{original_filename}`.

**Save** → `PATCH /api/v1/profiles/{id}/` with changed fields.

### 4. Smart Search (`/hr/search`)

> **Phase 2 scope:** UI only. The search box collects the query text. No AI or NLP backend is called. Results shown are a static/empty state until Phase 3 wires in the AI pipeline.

```
┌─────────────────────────────────────────────────────────────────┐
│  🔍  e.g. "Find backend developers with Java experience"        │
│                                               [Search]          │
└─────────────────────────────────────────────────────────────────┘

Optional filters: [Skills ▼]  [Location ▼]  [Experience ▼]  [Department ▼]
```

- Large text input with rotating placeholder examples showing sample queries.
- `Search` button disabled until input has ≥ 3 characters.
- On submit: button shows a loading state then displays an empty results area with a message like "AI search coming soon — results will appear here in Phase 3."
- No API call is made for the NLP query in Phase 2.

**Profile Preview (`/hr/search/[id]/preview`):**
- Read-only version of the Employee Detail page (no edit controls) — navigated to directly via URL or from future search results.
- Top-right: `Download Profile` button → calls `GET /api/v1/profiles/{id}/download/` → backend generates a clean PDF resume and streams it to the browser.

### 5. Review Queue (`/hr/reviews`)

List of employees who have submitted their profiles for review.

**Table:**

| Employee | Designation | Submitted | Status | HR Comment | Actions |
|---|---|---|---|---|---|
| John Doe | Backend Dev | 2026-05-12 | Pending | — | Approve Reject View |

- **View** → opens the Employee Detail in read-only mode.
- **Approve** → `POST /api/v1/reviews/{id}/approve/` → `profile_status` set to `approved` → approval email sent to employee → row moves out of queue.
- **Reject** → opens a modal with a **Comment** textarea → `POST /api/v1/reviews/{id}/reject/` with `{ comment }` → rejection email sent to employee with the comment.

**Email on approval:**
```
Subject: Your TalentExe profile has been approved!
Body: "Hi <name>, your profile has been approved and is now searchable. ..."
```

**Email on rejection:**
```
Subject: TalentExe profile update required
Body: "Hi <name>, your profile needs some updates before it can be approved.
HR comment: <comment>
Please log in to update your profile."
```

### 6. Reports & Analytics (`/hr/reports`)

Full-page "Coming Soon" placeholder:

```
┌──────────────────────────────────────────────┐
│                                              │
│   📊  Reports & Analytics                   │
│                                              │
│   This feature is coming soon.              │
│   Stay tuned for workforce insights,        │
│   skill gap analysis, and more.             │
│                                              │
└──────────────────────────────────────────────┘
```

---

## Employee Portal — Detailed Screens

### First-Login: Set Password (`/set-password`)

Shown immediately after logging in with the temp password when `must_change_password = true`.

```
┌──────────────────────────────────────┐
│  Set Your New Password               │
│                                      │
│  New Password       [____________]   │
│  Confirm Password   [____________]   │
│                                      │
│              [Set Password]          │
└──────────────────────────────────────┘
```

- Validation: min 8 chars, must match.
- On success → redirect to `/employee/profile`.

### Forgot Password (`/forgot-password`)

```
┌──────────────────────────────────────┐
│  Forgot Password                     │
│                                      │
│  Email  [_________________________]  │
│                                      │
│         [Send Reset Link]            │
│                                      │
│  ← Back to Login                     │
└──────────────────────────────────────┘
```

### Reset Password (`/reset-password?token=...`)

```
┌──────────────────────────────────────┐
│  Reset Your Password                 │
│                                      │
│  New Password       [____________]   │
│  Confirm Password   [____________]   │
│                                      │
│              [Reset Password]        │
└──────────────────────────────────────┘
```

### Sidebar (Employee)

```
Talent.exe
──────────
📋  Profile
🔍  Profile Status
──────────
⬚   Logout
```

### Profile (`/employee/profile`)

Two modes: **View** and **Edit** (toggled by an `Edit Profile` button).

**Sections** (same structure as HR Employee Detail):
1. Header (avatar, name, designation)
2. Summary
3. Skills (with proficiency and years)
4. Experience
5. Projects
6. Education
7. Certifications
8. Languages
9. Links — LinkedIn URL (plain text field, no API), GitHub URL, Portfolio URL
10. Resume upload

**Resume Upload panel:**
- Drag-and-drop zone or `Browse` button.
- Accepted: `.pdf`, `.doc`, `.docx` — Max 10 MB.
- File is uploaded directly to Supabase Storage. No AI extraction happens — the raw file is stored and made available to HR for download.
- Shows current uploaded file name + upload date + a `Download` link.

**Submit for Review button:**
- Enabled only when profile has at least: name, designation, 1 skill, and resume uploaded.
- `POST /api/v1/profiles/{id}/submit-review/` → `profile_status` set to `submitted` → button changes to "Awaiting Review".
- If employee edits again after submission → status resets to `submitted` and a new review entry is created.

### Profile Status (`/employee/profile/status`)

```
┌───────────────────────────────────────────────────────────┐
│  Profile Status                                           │
│                                                           │
│  Status:  ● Approved                                      │
│                                                           │
│  Reviewed by:  Jane HR  on  12 May 2026                  │
│                                                           │
│  HR Comments:                                             │
│  "Great profile! Please add your LinkedIn URL."           │
│                                                           │
│  Timeline                                                 │
│  ──────────────────────────────────────────              │
│  12 May 2026  Approved by HR                             │
│  10 May 2026  Submitted for review                       │
│   8 May 2026  Profile created                            │
└───────────────────────────────────────────────────────────┘
```

Status badge colors:
- `incomplete` → grey
- `submitted` → amber (Awaiting Review)
- `approved` → green
- `rejected` → red

---

## Backend — New Apps & Files

```
backend/apps/
├── users/
│   ├── models.py          ← add phone, designation, department, etc. to UserProfile
│   ├── serializers.py     ← UserListSerializer, UserDetailSerializer, BulkUploadSerializer
│   ├── views.py           ← UserViewSet, DisableView, ResendInviteView, BulkUploadView
│   ├── services.py        ← create_supabase_user(), send_welcome_email(), generate_temp_password()
│   └── urls.py
├── auth_ext/              ← NEW — password change/reset endpoints
│   ├── __init__.py
│   ├── views.py           ← ChangePasswordView, ForgotPasswordView, ResetPasswordView
│   ├── serializers.py
│   └── urls.py
├── profiles/              ← NEW — employee extended profile
│   ├── __init__.py
│   ├── models.py          ← EmployeeProfile, ResumeUpload
│   ├── serializers.py     ← EmployeeProfileSerializer, ResumeUploadSerializer
│   ├── views.py           ← ProfileViewSet, ResumeUploadView, SubmitReviewView, DownloadProfileView
│   ├── pdf.py             ← PDF generation logic (weasyprint)
│   └── urls.py
├── reviews/               ← NEW — HR review queue
│   ├── __init__.py
│   ├── models.py          ← ProfileReview
│   ├── serializers.py
│   ├── views.py           ← ReviewListView, ApproveView, RejectView
│   └── urls.py
└── dashboard/             ← NEW — HR dashboard stats
    ├── __init__.py
    ├── views.py           ← DashboardStatsView
    └── urls.py
```

### Email service (`apps/users/services.py` additions)

```python
import random, string
from django.core.mail import send_mail
from django.conf import settings

def generate_temp_password(length=12) -> str:
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(random.choices(chars, k=length))

def send_welcome_email(to_email: str, full_name: str, temp_password: str, role: str):
    subject = "Welcome to TalentExe — Your login credentials"
    body = f"""Hi {full_name},

Your TalentExe account has been created. Use the credentials below to log in:

  Email:    {to_email}
  Password: {temp_password}

You will be asked to set a new password on your first login.

Login at: {settings.FRONTEND_URL}/login

Best,
TalentExe Team
"""
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to_email])

def send_approval_email(to_email: str, full_name: str):
    subject = "Your TalentExe profile has been approved!"
    body = f"""Hi {full_name},

Great news — your profile has been approved and is now searchable by the HR team.

Login at: {settings.FRONTEND_URL}/login

Best,
TalentExe Team
"""
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to_email])

def send_rejection_email(to_email: str, full_name: str, comment: str):
    subject = "TalentExe profile update required"
    body = f"""Hi {full_name},

Your profile needs some updates before it can be approved.

HR comment:
"{comment}"

Please log in to update your profile: {settings.FRONTEND_URL}/login

Best,
TalentExe Team
"""
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to_email])
```

### PDF Generation (`apps/profiles/pdf.py`)

Uses `weasyprint` to render an HTML template to PDF.

```python
from weasyprint import HTML
from django.template.loader import render_to_string

def generate_profile_pdf(profile_data: dict) -> bytes:
    html_str = render_to_string('profiles/resume_pdf.html', {'profile': profile_data})
    return HTML(string=html_str).write_pdf()
```

Template file: `backend/templates/profiles/resume_pdf.html`

---

## Frontend — Component Map

```
src/
├── app/
│   ├── (auth)/
│   │   ├── login/page.tsx                ← Phase 1 (extend: must_change_password check)
│   │   ├── set-password/page.tsx         ← NEW
│   │   ├── forgot-password/page.tsx      ← NEW
│   │   └── reset-password/page.tsx       ← NEW
│   ├── hr/
│   │   ├── layout.tsx                    ← HR shell with sidebar + shared navbar
│   │   ├── dashboard/page.tsx            ← Stat cards
│   │   ├── employees/
│   │   │   ├── page.tsx                  ← Employee list table
│   │   │   ├── new/page.tsx              ← Add Employee form
│   │   │   └── [id]/page.tsx             ← Employee detail + edit
│   │   ├── search/
│   │   │   ├── page.tsx                  ← NLP search UI
│   │   │   └── [id]/preview/page.tsx     ← Read-only profile + download
│   │   ├── reviews/page.tsx              ← Review queue
│   │   └── reports/page.tsx              ← Coming soon
│   └── employee/
│       ├── layout.tsx                    ← Employee shell with sidebar + navbar
│       ├── profile/page.tsx              ← Profile edit
│       └── profile/status/page.tsx       ← Status + comments
├── components/
│   ├── layout/
│   │   ├── Navbar.tsx                    ← Shared top bar
│   │   ├── HrSidebar.tsx
│   │   └── EmployeeSidebar.tsx
│   ├── profile/
│   │   ├── AvatarUpload.tsx
│   │   ├── ResumeUpload.tsx              ← drag-and-drop, validation
│   │   ├── SkillsEditor.tsx              ← add/edit/remove skill tags + proficiency
│   │   ├── CertificationsEditor.tsx
│   │   ├── ProjectsEditor.tsx
│   │   ├── EducationEditor.tsx
│   │   └── ProfileStatusBadge.tsx
│   ├── employees/
│   │   ├── EmployeeTable.tsx             ← table + pagination + filters
│   │   ├── AddEmployeeForm.tsx
│   │   ├── BulkUploadModal.tsx
│   │   └── EmployeeActions.tsx           ← View/Edit/Delete/Disable/Resend row actions
│   ├── reviews/
│   │   ├── ReviewTable.tsx
│   │   └── RejectModal.tsx               ← reject with comment
│   ├── dashboard/
│   │   └── StatCard.tsx
│   └── search/
│       └── NlpSearchBox.tsx
└── lib/
    └── api.ts                            ← extend with new endpoint helpers
```

---

## File Upload — Validation Rules

| Field | Rule |
|---|---|
| Accepted formats | `.pdf`, `.doc`, `.docx` |
| Max file size | 10 MB (client + server) |
| Client check | Before upload: check `file.size` and `file.name` extension |
| Server check | Django view checks `Content-Type` and `size` before writing to Supabase Storage |
| Error messages | "Only PDF, DOC, and DOCX files are supported." / "File exceeds 10 MB limit." |

---

## Python Dependencies (additions to `requirements.txt`)

```
weasyprint==62.3
openpyxl==3.1.2
pandas==2.2.2
Pillow==10.3.0
```

---

## Phase 2 Checklist

### Email & Auth Flows
- [ ] Add Brevo SMTP config to Django settings
- [ ] `generate_temp_password()` and `send_welcome_email()` in services.py
- [ ] `POST /api/v1/users/` calls Supabase + sends welcome email
- [ ] `GET /api/v1/auth/me/` returns `must_change_password` field
- [ ] `POST /api/v1/auth/change-password/` updates password + clears flag
- [ ] `POST /api/v1/auth/forgot-password/` sends reset email
- [ ] `POST /api/v1/auth/reset-password/` validates token + sets new password
- [ ] `/set-password` page (frontend)
- [ ] `/forgot-password` page (frontend)
- [ ] `/reset-password` page (frontend)
- [ ] `middleware.ts` redirects to `/set-password` if `must_change_password = true`

### Database
- [ ] Run schema additions SQL (alter profiles + 4 new tables)
- [ ] Create Supabase Storage bucket `resumes` (public: false)
- [ ] Create Supabase Storage bucket `avatars` (public: true)

### Shared Navbar
- [ ] `Navbar.tsx` with Talent.exe wordmark + avatar dropdown
- [ ] `AvatarUpload.tsx` — upload picture to `avatars` bucket
- [ ] Change Password modal in navbar

### HR Dashboard
- [ ] `GET /api/v1/dashboard/stats/` endpoint
- [ ] `StatCard.tsx` component
- [ ] Dashboard page with all 6 cards

### Employee List
- [ ] `GET /api/v1/users/` with filters + pagination
- [ ] `EmployeeTable.tsx` with all columns and row actions
- [ ] Filter bar (name, designation, department, experience, skills, location, status)
- [ ] `AddEmployeeForm.tsx` + `POST /api/v1/users/`
- [ ] `BulkUploadModal.tsx` + `POST /api/v1/users/bulk-upload/`
- [ ] Disable / Resend Invite actions wired up

### Employee Detail (HR view)
- [ ] `GET /api/v1/profiles/{id}/` full profile endpoint
- [ ] Employee detail page with all 11 sections
- [ ] Inline editing for all fields
- [ ] `ResumeUpload.tsx` — upload to Supabase Storage, replace current
- [ ] `PATCH /api/v1/profiles/{id}/` save changes

### Smart Search
- [ ] `NlpSearchBox.tsx` with placeholder text
- [ ] Search results table (same columns as employee list + Match Score placeholder)
- [ ] Read-only profile preview page
- [ ] `GET /api/v1/profiles/{id}/download/` PDF endpoint
- [ ] `weasyprint` PDF template for employee profile

### Review Queue
- [ ] `GET /api/v1/reviews/` list pending reviews
- [ ] `ReviewTable.tsx` with Approve / Reject / View actions
- [ ] `POST /api/v1/reviews/{id}/approve/` + approval email
- [ ] `RejectModal.tsx` with comment textarea
- [ ] `POST /api/v1/reviews/{id}/reject/` + rejection email

### Reports
- [ ] `/hr/reports` "Coming Soon" page

### Employee Portal
- [ ] HR sidebar: Dashboard, Employee List, Smart Search, Review Queue, Reports, Logout
- [ ] Employee sidebar: Profile, Profile Status, Logout
- [ ] `/employee/profile` — all sections editable + resume upload
- [ ] `POST /api/v1/profiles/{id}/submit-review/` + status update
- [ ] `/employee/profile/status` — status badge + timeline + HR comments
- [ ] Re-submission resets status to `submitted` and creates new review entry

---

## Running Locally (additions)

```bash
# Backend — install new dependencies
pip install -r requirements.txt

# Create Django migrations for new models
python manage.py makemigrations profiles reviews dashboard
python manage.py migrate

# Verify email config (send a test email)
python manage.py shell -c "
from django.core.mail import send_mail
send_mail('Test', 'Hello from TalentExe', None, ['your@email.com'])
"
```

---

## Phase 3 Preview

- AI/NLP query processing wired into Smart Search (Claude claude-sonnet-4-6 + pgvector embeddings).
- Resume text extraction on upload — automatic skill, experience, and certification parsing.
- LinkedIn profile data import via LinkedIn export or API.
- Match scores populated in search results with AI-generated explanations.
- Analytics charts and skill gap reports.

# TalentExe — Frontend

Next.js 14 App Router frontend for TalentExe. Handles authentication via Supabase, role-based routing, the HR portal, and the Employee portal.

---

## Stack

| | |
|---|---|
| Framework | Next.js 14 (App Router) |
| Language | TypeScript |
| Styling | Tailwind CSS |
| Components | shadcn/ui |
| Auth | Supabase (`@supabase/ssr`) |
| Package manager | pnpm |

---

## Project Structure

```
frontend/src/
├── app/
│   ├── layout.tsx                              ← root layout
│   ├── page.tsx                                ← redirects to /login
│   ├── (auth)/
│   │   ├── login/page.tsx                      ← shared login (HR + Employee)
│   │   ├── forgot-password/page.tsx
│   │   ├── reset-password/page.tsx
│   │   └── set-password/page.tsx               ← forced password change on first login
│   ├── hr/
│   │   ├── layout.tsx                          ← HR shell with sidebar
│   │   ├── dashboard/page.tsx                  ← stat cards
│   │   ├── employees/
│   │   │   ├── page.tsx                        ← employee list with search + pagination
│   │   │   ├── new/page.tsx                    ← create employee form
│   │   │   └── [id]/page.tsx                   ← edit employee
│   │   ├── search/
│   │   │   ├── page.tsx                        ← NLP smart search
│   │   │   └── [id]/preview/page.tsx           ← full profile preview
│   │   ├── reviews/page.tsx                    ← HR review queue
│   │   └── reports/page.tsx
│   └── employee/
│       ├── layout.tsx                          ← Employee shell with sidebar
│       ├── dashboard/page.tsx                  ← redirect scaffold
│       └── profile/
│           ├── page.tsx                        ← full profile editor
│           └── status/page.tsx                 ← approval status + HR comments
├── components/
│   ├── ui/                                     ← shadcn primitives (Button, Input, Card, …)
│   ├── auth/
│   │   └── LoginForm.tsx
│   ├── layout/
│   │   ├── Navbar.tsx
│   │   ├── HrSidebar.tsx
│   │   ├── EmployeeSidebar.tsx
│   │   ├── AvatarUploadModal.tsx
│   │   └── ChangePasswordModal.tsx
│   ├── dashboard/
│   │   └── StatCard.tsx
│   ├── employees/
│   │   ├── EmployeeTable.tsx
│   │   ├── EmployeeActions.tsx
│   │   └── BulkUploadModal.tsx
│   ├── profile/
│   │   ├── SkillsEditor.tsx
│   │   ├── ExperienceEditor.tsx
│   │   ├── ProjectsEditor.tsx
│   │   ├── CertificationsEditor.tsx
│   │   ├── EducationEditor.tsx
│   │   ├── LanguagesEditor.tsx
│   │   ├── ResumeUpload.tsx
│   │   └── ProfileStatusBadge.tsx
│   ├── search/
│   │   ├── NlpSearchBox.tsx                    ← natural-language query input
│   │   └── SearchResults.tsx                   ← ranked results with match scores
│   └── reviews/
│       └── RejectModal.tsx
├── lib/
│   ├── supabase.ts                             ← browser Supabase client
│   ├── supabase-server.ts                      ← server/middleware Supabase client
│   ├── api.ts                                  ← fetch wrapper (attaches JWT)
│   └── utils.ts                                ← cn() class name helper
├── types/
│   └── index.ts                                ← shared TypeScript types
└── middleware.ts                               ← role-based route protection
```

---

## Local Setup

```bash
cd frontend

# 1. Install dependencies
pnpm install

# 2. Copy env template
cp .env.local.example .env.local

# 3. Fill in your keys in .env.local

# 4. Start dev server
pnpm dev
# → http://localhost:3000
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Your Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon/public key (safe to expose) |
| `NEXT_PUBLIC_API_BASE_URL` | Django backend URL (`http://localhost:8000` locally) |
| `NEXT_PUBLIC_MAX_RESUME_SIZE_MB` | Maximum resume upload size in MB (default: `10`) |

---

## Pages & Routes

| Route | Auth required | Role | Description |
|---|---|---|---|
| `/` | No | — | Redirects to `/login` |
| `/login` | No | — | Shared login for HR + Employee |
| `/forgot-password` | No | — | Send reset email |
| `/reset-password` | No | — | Confirm reset via link |
| `/set-password` | Yes | Any | Forced password change on first login |
| `/hr/dashboard` | Yes | `hr` | Stat cards: employees, reviews, skills |
| `/hr/employees` | Yes | `hr` | Employee list with search + pagination |
| `/hr/employees/new` | Yes | `hr` | Create a new employee |
| `/hr/employees/[id]` | Yes | `hr` | Edit employee details |
| `/hr/search` | Yes | `hr` | NLP smart search — ranked results |
| `/hr/search/[id]/preview` | Yes | `hr` | Full employee profile preview + PDF download |
| `/hr/reviews` | Yes | `hr` | Review queue — approve or reject submitted profiles |
| `/employee/profile` | Yes | `employee` | Full profile editor (skills, experience, projects, …) |
| `/employee/profile/status` | Yes | `employee` | Approval status + HR comments |

---

## Auth & Routing Flow

```
User enters email + password on /login
  → supabase.auth.signInWithPassword()
  → Supabase returns session with access_token (JWT)
  → Frontend calls GET /api/v1/auth/me/ with JWT
  → Backend returns { role: 'hr' | 'employee', must_change_password }
  → must_change_password=true  →  /set-password
  → role=hr       →  /hr/dashboard
  → role=employee →  /employee/profile
```

`middleware.ts` enforces role-based access on every request:
- Unauthenticated access to `/hr/*` or `/employee/*` → redirect to `/login`
- HR user hitting `/employee/*` → redirect to `/hr/dashboard`
- Employee hitting `/hr/*` → redirect to `/employee/profile`

---

## Key Files

### `src/middleware.ts`
Runs on every request (except static assets). Reads the Supabase session from cookies and enforces role-based route protection.

### `src/lib/api.ts`
Thin fetch wrapper that attaches `Authorization: Bearer <token>` to every request to the Django backend.

### `src/components/search/NlpSearchBox.tsx`
Natural-language query input that calls `POST /api/v1/search/` and passes results to `SearchResults`.

### `src/components/search/SearchResults.tsx`
Renders ranked candidate cards with match score badges and AI-generated plain-English explanations.

### `src/lib/supabase.ts`
Browser-side Supabase client (used in client components and event handlers).

### `src/lib/supabase-server.ts`
Server-side Supabase client (used in Server Components and middleware to read session cookies).

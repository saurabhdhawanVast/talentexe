# TalentExe — Frontend

Next.js 14 App Router frontend for TalentExe. Handles authentication via Supabase, role-based routing, and the HR dashboard.

---

## Stack

| | |
|---|---|
| Framework | Next.js 14 (App Router) |
| Language | TypeScript |
| Styling | Tailwind CSS |
| Components | shadcn/ui-compatible primitives |
| Auth | Supabase (`@supabase/ssr`) |
| Package manager | pnpm |

---

## Project Structure

```
frontend/src/
├── app/
│   ├── layout.tsx                  ← root layout
│   ├── page.tsx                    ← redirects to /login
│   ├── (auth)/login/page.tsx       ← shared login page (HR + Employee)
│   ├── hr/dashboard/
│   │   ├── page.tsx               ← HR placeholder dashboard (server component)
│   │   └── LogoutButton.tsx       ← client component
│   └── employee/dashboard/
│       └── page.tsx               ← Phase 3 scaffold
├── components/
│   ├── ui/                         ← Button, Input, Label, Card
│   └── auth/
│       └── LoginForm.tsx           ← login form (client component)
├── lib/
│   ├── supabase.ts                 ← browser Supabase client
│   ├── supabase-server.ts          ← server/middleware Supabase client
│   ├── api.ts                      ← fetch wrapper (attaches JWT)
│   └── utils.ts                    ← cn() class name helper
└── middleware.ts                   ← role-based route protection
```

---

## Local Setup

```bash
cd frontend

# 1. Install dependencies
pnpm install

# 2. Copy env template
cp .env.local.example .env.local

# 3. Fill in your Supabase keys in .env.local
#    NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
#    NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-key-from-supabase-dashboard>
#    NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

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

---

## Pages & Routes

| Route | Auth required | Description |
|---|---|---|
| `/` | No | Redirects to `/login` |
| `/login` | No | Shared login for HR + Employee |
| `/hr/dashboard` | Yes (`role=hr`) | HR placeholder dashboard |
| `/employee/dashboard` | Yes (`role=employee`) | Phase 3 scaffold |
| `/admin/*` | — | Always redirected to `/login` (admin uses Django Admin) |

---

## Auth & Routing Flow

```
User enters email + password on /login
  → supabase.auth.signInWithPassword()
  → Supabase returns session with access_token (JWT)
  → Frontend calls GET /api/v1/auth/me/ with JWT
  → Backend returns { role: 'hr' | 'employee' }
  → router.push() to the correct dashboard
```

`middleware.ts` enforces this on every request:
- Unauthenticated access to `/hr/*` or `/employee/*` → redirect to `/login`
- Authenticated user hitting `/login` → look up role → redirect to dashboard
- `/admin/*` → always redirect to `/login`

---

## Key Files

### `src/middleware.ts`
Runs on every request (except static assets). Reads the Supabase session from cookies, enforces role-based route protection.

### `src/components/auth/LoginForm.tsx`
Client component. Handles the full login flow: Supabase sign-in → role fetch → redirect.

### `src/lib/api.ts`
Thin fetch wrapper that attaches `Authorization: Bearer <token>` to every request to the Django backend.

### `src/lib/supabase.ts`
Browser-side Supabase client (used in client components and event handlers).

### `src/lib/supabase-server.ts`
Server-side Supabase client (used in Server Components and middleware to read session cookies).

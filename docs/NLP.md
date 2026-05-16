# NLP Smart Search — Design & Implementation Guide

> **Scope:** Hard Problem #2 from the [Problem Statement](./problemStatement.md). This document covers everything needed to design, build, and reason about the HR Semantic Natural Language Search feature.

> **Critical constraint:** NLP Smart Search **only returns employees whose profiles have been approved by HR** (`profile_status = 'approved'`). Pending, rejected, or incomplete profiles are never surfaced in search results.

---

## What Is It?

HR users on the platform have a **Smart Search** section where they can type plain-English queries to find employees — no filters, no dropdowns, just natural language.

Instead of keyword matching, the system **understands intent**, applies **vector similarity** against employee profiles, and returns **ranked, explained results** with a match score.

> **Who appears in search results?** Only employees whose profiles have been **approved by HR**. The approval flow (from the ingestion pipeline) is a prerequisite — unapproved profiles are invisible to search. This ensures search quality and prevents incomplete or unverified data from surfacing to HR.

**Example queries HR can type:**
- *"Who can lead a React project that also needs WebSocket experience?"*
- *"Find me a backend dev in Pune with at least 3 years of Java and any payment gateway integration."*
- *"Senior frontend folks who haven't been on a new project in the last quarter."*

Each result shows:
- Employee name, designation, location, experience
- **Match score** (e.g., 94%)
- **Plain-English explanation** (e.g., *"Rahul — 94% match. Expert Java developer (6 yrs) with Razorpay and PayU integration. Located in Pune, currently unallocated."*)
- Top skill badges

---

## How It Works — The Pipeline

```
HR types a query
       ↓
Step 1 — Query Parsing (Claude)
       Extract structured intent from the plain-English query
       { skills, location, min_years, role_hint, availability }
       ↓
Step 2 — Query Embedding (Ollama nomic-embed-text)
       Convert the full query text into a 768-dim vector
       ↓
Step 3 — Vector Similarity Search (pgvector)
       Find top 50 employee profiles by cosine similarity
       against pre-computed embeddings in employee_embeddings
       ↓
Step 4 — Hard Filters
       Apply deterministic filters: location, min_years, department
       Narrow to top 20 candidates
       ↓
Step 5 — Match Explanation + Score (Claude)
       Bulk call: Claude scores each of the top 20 profiles (0–100)
       and generates a 1–2 sentence plain-English explanation per result
       ↓
Step 6 — Response to Frontend
       Ranked list with match_score, explanation, top_skills, profile link
```

---

## Architecture

### Where Each Piece Lives

```
backend/apps/ai_integration/
├── searcher.py           ← orchestrates the full search pipeline
├── embedder.py           ← generates query embedding via Ollama
├── explainer.py          ← Claude bulk explanation + match scoring
└── profile_text_builder.py ← builds text representation of each employee profile

frontend/src/
├── components/hr/NlpSearchBox.tsx     ← search input, loading state, query chips
├── components/hr/SearchResults.tsx    ← result cards (score badge, explanation, skills)
└── app/(dashboard)/hr/search/page.tsx ← Smart Search page (HR only)
```

### Technology Stack for Search

| Concern | Technology | Why |
|---|---|---|
| Query intent parsing | Claude claude-sonnet-4-6 | Understands ambiguous HR language |
| Query + profile embedding | Ollama `nomic-embed-text` (768 dims) | Free, runs locally, no API cost |
| Vector similarity | pgvector cosine (`<=>` operator) | Already enabled in Supabase |
| Match explanation + score | Claude claude-sonnet-4-6 | Human-readable, contextual reasoning |
| Hard filters | Raw SQL + Python | Deterministic, fast, reliable |

---

## Step-by-Step Implementation

### Step 1 — Query Parsing (`searcher.py`)

Claude converts the raw query string into a structured JSON intent object so hard filters can be applied accurately.

```python
QUERY_PARSE_PROMPT = """
Parse this HR search query into structured filters. Return JSON only.

{
  "skills_required": ["string"],
  "skills_nice_to_have": ["string"],
  "location": "string or null",
  "min_years_experience": number or null,
  "role_hint": "frontend|backend|fullstack|devops|mobile|data or null",
  "department": "string or null",
  "availability_hint": "bench|unallocated or null"
}

Query: {query}
"""
```

**Example input → output:**

| Query | Parsed Intent |
|---|---|
| "Backend dev in Pune, 3+ years Java, payment gateway" | `{ skills_required: ["Java", "payment gateway"], location: "Pune", min_years_experience: 3, role_hint: "backend" }` |
| "Senior frontend folks not on any project" | `{ skills_required: [], role_hint: "frontend", availability_hint: "unallocated" }` |

The parsed intent is also **returned to the frontend** as filter chips so HR can see what Claude understood from the query.

---

### Step 2 — Embedding Generation (`embedder.py`)

Both **query embeddings** (at search time) and **profile embeddings** (at profile approval time) use the same model via Ollama.

```python
def generate_embedding(text: str) -> list[float]:
    response = requests.post(
        f"{settings.OLLAMA_BASE_URL}/api/embeddings",
        json={"model": settings.OLLAMA_EMBED_MODEL, "prompt": text}
    )
    return response.json()["embedding"]  # 768-dimensional vector
```

**Profile embeddings are pre-computed** when a profile is approved by HR. They are stored in `employee_embeddings.embedding (vector(768))`.

What goes into a profile's `searchable_text` (built by `profile_text_builder.py`):

```
Full Name, Designation, Department
Location: <city>
Experience: <N> years
Summary: <bio>
Skills: React (Expert, 5 yrs), Node.js (Intermediate, 3 yrs), ...
Projects: E-Commerce App: Built with React/Node/Mongo | ...
Experience: Senior Dev at Infosys | SDE at Wipro | ...
Certifications: AWS SAA, PMP
```

The richer the profile text, the better the semantic match quality.

---

### Step 3 — Vector Similarity Search (`searcher.py`)

```sql
SELECT
  ee.profile_id,
  p.full_name,
  p.designation,
  p.department,
  p.location,
  p.experience_years,
  1 - (ee.embedding <=> %(query_embedding)s::vector) AS similarity
FROM employee_embeddings ee
JOIN profiles p ON p.id = ee.profile_id
WHERE
  p.role = 'employee'
  AND p.is_active = true
  AND p.profile_status = 'approved'
ORDER BY similarity DESC
LIMIT 50
```

Only **approved** profiles are searched — profiles pending HR review are excluded.

---

### Step 4 — Hard Filters (`searcher.py`)

After the vector search retrieves the top 50 by similarity, deterministic filters are applied in Python:

```python
def _apply_hard_filters(results: list, parsed: dict) -> list:
    if parsed.get("location"):
        results = [r for r in results if parsed["location"].lower() in (r["location"] or "").lower()]
    if parsed.get("min_years_experience"):
        results = [r for r in results if (r["experience_years"] or 0) >= parsed["min_years_experience"]]
    if parsed.get("department"):
        results = [r for r in results if parsed["department"].lower() in (r["department"] or "").lower()]
    return results[:20]  # cap at 20 results
```

---

### Step 5 — Match Explanation + Scoring (`explainer.py`)

A **single bulk Claude call** scores and explains all top results at once (max 20 per call) to minimize API latency.

```python
EXPLANATION_PROMPT = """
You are an HR assistant. For each profile below, given the search query, generate:
1. A match score (0–100) reflecting how well the profile fits the query
2. A 1–2 sentence plain-English explanation citing specific skills, years, and project types

Return JSON array:
[{ "profile_id": "uuid", "match_score": 0-100, "explanation": "string" }]

Query: {query}
Profiles: {profiles_json}
"""
```

**Score guidance (applied by Claude):**
- **90–100** — matches all required skills + location + experience
- **70–89** — matches most required skills, minor gaps
- **50–69** — partial match, some relevant experience
- **< 50** — weak match (still returned but visually de-emphasized)

---

## API Contract

### `POST /api/v1/search/`

**Auth:** HR role only

**Request:**
```json
{
  "query": "Find me a backend dev in Pune with 3+ years Java and payment gateway experience",
  "filters": {
    "location": null,
    "min_years": null,
    "department": null
  }
}
```

**Response:**
```json
{
  "data": {
    "query_parsed": {
      "skills_required": ["Java", "payment gateway"],
      "location": "Pune",
      "min_years_experience": 3,
      "role_hint": "backend"
    },
    "results": [
      {
        "profile_id": "<uuid>",
        "full_name": "Rahul Sharma",
        "designation": "Senior Backend Developer",
        "department": "Engineering",
        "location": "Pune",
        "experience_years": 6,
        "profile_status": "approved",
        "match_score": 94,
        "explanation": "Expert Java developer (6 yrs) with Razorpay and PayU integration on 2 production projects. Located in Pune, currently unallocated.",
        "top_skills": ["Java", "Spring Boot", "Razorpay", "PostgreSQL"],
        "similarity": 0.94
      }
    ],
    "total": 12
  },
  "error": null,
  "meta": {}
}
```

### `GET /api/v1/search/{profile_id}/explain/`

**Auth:** HR role only

Re-generates the match explanation for a single profile on demand. Useful when HR wants a fresher explanation after changing the query.

---

## Frontend — HR Smart Search UI

### Search Box (`NlpSearchBox.tsx`)

- Full-width text input with placeholder: *"Try: 'Senior React developer in Mumbai with fintech experience'"*
- **Search** button (disabled if query < 3 words)
- On submit → `POST /api/v1/search/` → show loading skeleton
- After response → display `query_parsed` as **filter chips** below the input:
  ```
  [Skills: Java, payment gateway]  [Location: Pune]  [Min Experience: 3 yrs]  [Role: backend]
  ```
  These chips let HR confirm Claude understood the query correctly.

### Result Cards (`SearchResults.tsx`)

```
┌─────────────────────────────────────────────────────────────────────┐
│  ● Rahul Sharma                                          94% match  │
│  Senior Backend Developer · Engineering · Pune · 6 yrs             │
│  ─────────────────────────────────────────────────────────────────  │
│  Expert Java developer (6 yrs) with Razorpay and PayU              │
│  integration on 2 production projects. Currently unallocated.      │
│                                                                     │
│  [Java]  [Spring Boot]  [Razorpay]  [PostgreSQL]    [View Profile] │
└─────────────────────────────────────────────────────────────────────┘
```

**Match score badge colors:**
- Green (≥ 80%) — strong match
- Amber (60–79%) — partial match
- Red (< 60%) — weak match (shown last, visually muted)

**View Profile** → `/hr/employees/[id]` (existing profile preview page)

### Empty & Error States

| Scenario | UI message |
|---|---|
| No results after filters | *"No approved profiles match your search — try different skills or location."* |
| Query too short (< 3 words) | Search button disabled + hint: *"Try adding skills, location, or experience level."* |
| API error / timeout | *"Search temporarily unavailable — please try again."* |
| No approved employees in system | *"No approved profiles yet. Ask employees to complete their profiles."* |

---

## Sequence Diagram

```
HR              Frontend            Backend              Claude         Ollama        Supabase
  |                |                  |                   |              |              |
  |-- type query ->|                  |                   |              |              |
  |                |-- POST /search ->|                   |              |              |
  |                |                 |-- parse query --->|              |              |
  |                |                 |<- structured JSON  |              |              |
  |                |                 |-- embed query ------------------>|              |
  |                |                 |<- vector[768]      |              |              |
  |                |                 |-- cosine search -------------------------------->|
  |                |                 |<- top 50 profiles  |              |              |
  |                |                 |-- apply hard filters (Python)    |              |
  |                |                 |-- bulk explain --->|              |              |
  |                |                 |<- scores + text    |              |              |
  |                |<- ranked results|                   |              |              |
  |-- see results  |                 |                   |              |              |
```

---

## Profile Embedding — When It Happens

Embeddings are the foundation of search quality. They must be kept fresh:

| Trigger | Action |
|---|---|
| HR approves a profile for the first time | Auto-generate embedding via `generate_embedding()` |
| Employee updates their profile after approval | `employee_embeddings.updated_at` is stale — HR or employee can trigger refresh |
| HR clicks "Refresh Embedding" button on employee profile page | `POST /api/v1/profiles/{id}/generate-embedding/` |

---

## Error Handling

| Scenario | Handling |
|---|---|
| Claude returns invalid JSON from query parse | Retry once; on failure use empty structured intent (pure vector search) |
| Ollama embedding service down | Return `503` — *"Search temporarily unavailable"* |
| No approved employee profiles exist | Return `{ results: [], total: 0 }` with friendly message |
| Employee edited profile after embedding was built | Flag embedding as stale; surface refresh prompt to HR |

---

## Environment Variables

Add to `backend/.env`:

```env
# Ollama — embeddings (runs locally, no API key)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=nomic-embed-text

# Search tuning
SEARCH_MAX_RESULTS=20
```

---

## Local Setup (Search Feature Only)

```bash
# 1. Install and start Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
ollama pull nomic-embed-text

# 2. Verify embedding works (should print: dims: 768)
curl http://localhost:11434/api/embeddings \
  -d '{"model":"nomic-embed-text","prompt":"test"}' | \
  python -c "import sys,json; d=json.load(sys.stdin); print('dims:', len(d['embedding']))"

# 3. Verify Anthropic key
python -c "import anthropic; c = anthropic.Anthropic(); print('Claude: ok')"

# 4. One-time schema update (run in Supabase SQL editor)
ALTER TABLE employee_embeddings ALTER COLUMN embedding TYPE vector(768);

# 5. Start backend
cd backend && python manage.py runserver

# 6. Start frontend
cd frontend && pnpm dev
```

---

## Implementation Checklist

### Backend
- [ ] `embedder.py` — Ollama `nomic-embed-text` wrapper, `generate_embedding(text)` function
- [ ] `profile_text_builder.py` — assemble `searchable_text` from all normalized profile tables
- [ ] `searcher.py` — `parse_query()`, `_vector_search()`, `_apply_hard_filters()`, `search()` orchestrator
- [ ] `explainer.py` — `bulk_explain()` calling Claude with all top results in one prompt
- [ ] `views.py` → `SearchView` (POST), `ExplainMatchView` (GET)
- [ ] `serializers.py` → `SearchQuerySerializer`, `SearchResultSerializer`
- [ ] `urls.py` → register `/api/v1/search/` and `/api/v1/search/{profile_id}/explain/`
- [ ] Auto-embed on profile approval — hook into existing `approve` view
- [ ] `POST /api/v1/profiles/{id}/generate-embedding/` — manual refresh endpoint

### Frontend
- [ ] `NlpSearchBox.tsx` — POST to `/api/v1/search/`, loading skeleton, query chips
- [ ] `SearchResults.tsx` — result cards with match score badge, explanation, skill chips
- [ ] Empty state, error state, short-query validation
- [ ] `View Profile` link on each card → `/hr/employees/[id]`

### Database
- [ ] Run `ALTER TABLE employee_embeddings ALTER COLUMN embedding TYPE vector(768);`
- [ ] Confirm `pgvector` extension enabled (done in Phase 2.1)

---

## Related Documents

- [Problem Statement](./problemStatement.md) — original problem definition
- [Phase 3 Plan](./phase-3.md) — full Phase 3 scope including ingestion pipeline
- [Phase 2.1](./phase-2.1.md) — normalized schema that search queries against

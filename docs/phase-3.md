# Phase 3 — AI Ingestion Pipeline & Semantic Search

## Objective

Wire the two hard problems from the problem statement on top of the Phase 2.1 normalized schema:

1. **Smart Profile Ingestion** — resume upload triggers Claude-powered entity extraction; extracted data goes into the review queue before being accepted into normalized tables.
2. **Semantic Natural Language Search** — HR types a plain-English query; the system returns ranked, scored, explained results using pgvector similarity search + Claude.

---

## Scope Boundaries

| In Scope (Phase 3) | Deferred / Out of Scope |
|---|---|
| PDF / DOCX text extraction | LinkedIn OAuth / API import |
| Claude claude-sonnet-4-6 entity extraction (skills, experience, projects, certs, education) | Analytics charts |
| Skill inference (e.g. Next.js → React expertise) | Real-time re-embedding on every profile edit |
| AI extraction review queue (HR + employee accept/edit/reject) | Background task queue (Celery) — polling pattern used instead |
| Embedding generation per employee profile | Multi-modal (image) resume parsing |
| pgvector cosine similarity search | Fine-tuned or self-hosted embedding models |
| NL query → structured intent → filtered vector search | Cross-org search |
| Match score (0–100%) per result | |
| Plain-English match explanation per result | |

---

## How Phase 3 Connects to the Existing Stack

```
Phase 2.1 already built:
  employee_embeddings   ← Phase 3 populates this
  ai_profile_extractions ← Phase 3 writes raw + extracted JSON here
  inferred_skills       ← Phase 3 fills this
  resume_uploads.extraction_status ← Phase 3 drives this state machine

Phase 2 already built:
  NlpSearchBox.tsx      ← Phase 3 wires to real API
  resume file stored in Supabase Storage ← Phase 3 reads this file
  profile_reviews table ← Phase 3 creates entries after AI extraction
```

---

## Stack Additions (Phase 3)

| Concern | Technology | Notes |
|---|---|---|
| LLM — extraction + explanation | Anthropic Claude claude-sonnet-4-6 | `ANTHROPIC_API_KEY` already in `.env` |
| Embeddings | Ollama `nomic-embed-text` | 768 dims — free, runs locally, no API key needed; schema updated to `vector(768)` |
| Vector search | pgvector (already enabled in Supabase) | cosine similarity via `<=>` operator |
| PDF text extraction | `pdfminer.six` | pure-Python, no native deps |
| DOCX text extraction | `python-docx` | handles `.doc` / `.docx` |
| Async trigger pattern | Polling (no Celery) | endpoint returns `task_id`, client polls status |

> **Why Ollama for embeddings?** Claude does not produce vector embeddings natively. Ollama runs fully locally with no API key or cost. `nomic-embed-text` outputs 768-dim vectors — the Phase 2.1 schema uses `vector(1536)` so one line of SQL needs updating: `ALTER TABLE employee_embeddings ALTER COLUMN embedding TYPE vector(768);`

---

## Environment Variables (additions)

### `backend/.env.example` additions

```env
# Ollama — embeddings (runs locally, no API key needed)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=nomic-embed-text

# Extraction confidence threshold (0.0–1.0, default 0.7)
AI_EXTRACTION_CONFIDENCE_THRESHOLD=0.7

# Skill inference confidence threshold (0.0–1.0, default 0.6)
AI_INFERENCE_CONFIDENCE_THRESHOLD=0.6

# Max results returned by semantic search
SEARCH_MAX_RESULTS=20
```

---

## New Backend App: `ai_integration`

All AI logic lives in one dedicated Django app. This keeps AI code isolated from CRUD apps.

```
backend/apps/ai_integration/
├── __init__.py
├── apps.py
├── urls.py
├── views.py                  ← trigger extraction, get status, approve/reject, search
├── serializers.py
├── text_extractor.py         ← PDF/DOCX → plain text
├── extractor.py              ← Claude entity extraction prompt + parsing
├── skill_inferrer.py         ← infer related skills from extracted skill list
├── embedder.py               ← OpenAI text-embedding-3-small wrapper
├── profile_text_builder.py   ← builds searchable_text string per employee
├── searcher.py               ← pgvector cosine similarity + filter logic
└── explainer.py              ← Claude generates match explanation per result
```

---

## Hard Problem #1 — Smart Profile Ingestion

### Flow

```
Employee / HR uploads resume (already working from Phase 2)
  └── resume stored in Supabase Storage, resume_uploads row created
        ↓
  POST /api/v1/ai/extract/{resume_upload_id}/
        ↓
  1. Download file bytes from Supabase Storage
  2. Extract plain text (pdfminer.six or python-docx)
  3. Send to Claude claude-sonnet-4-6 with structured extraction prompt
  4. Parse Claude JSON response → validate schema
  5. Write raw_text + extracted_json → ai_profile_extractions
  6. Update resume_uploads.extraction_status = 'completed'
  7. Run skill inference on extracted skills
  8. Write inferred_skills rows
  9. Create profile_reviews entry (status='pending') for HR to verify
  10. Return { extraction_id, status: 'completed' }
```

### Claude Extraction Prompt (`extractor.py`)

```python
EXTRACTION_SYSTEM_PROMPT = """
You are an expert HR data extraction assistant. Extract structured information from the resume text.
Return ONLY valid JSON matching the schema below. Do not add commentary.

Schema:
{
  "summary": "string or null",
  "skills": [
    { "name": "string", "proficiency": "Beginner|Intermediate|Expert", "years": number_or_null }
  ],
  "experiences": [
    {
      "company_name": "string",
      "designation": "string",
      "employment_type": "Full-time|Part-time|Contract|Freelance|Internship or null",
      "start_date": "YYYY-MM or null",
      "end_date": "YYYY-MM or null",
      "is_current": boolean,
      "location": "string or null",
      "description": "string or null"
    }
  ],
  "projects": [
    {
      "name": "string",
      "description": "string or null",
      "role": "string or null",
      "tech_stack": ["string"],
      "start_date": "YYYY-MM or null",
      "end_date": "YYYY-MM or null",
      "is_current": boolean
    }
  ],
  "certifications": [
    { "name": "string", "issuer": "string or null", "issue_date": "YYYY-MM or null", "expiry_date": "YYYY-MM or null" }
  ],
  "education": [
    { "degree": "string", "institution": "string", "start_year": number_or_null, "end_year": number_or_null }
  ],
  "location": "string or null",
  "total_years_experience": number_or_null
}
"""
```

### Skill Inference (`skill_inferrer.py`)

After extraction, run a second Claude call to infer implied skills:

```python
INFERENCE_SYSTEM_PROMPT = """
Given the list of skills, infer which additional skills the person implicitly has.
Use only well-established technical relationships (e.g. 4+ years Next.js implies solid React expertise).

Return JSON:
{
  "inferences": [
    {
      "source_skill": "string",
      "inferred_skill": "string",
      "confidence": 0.0-1.0,
      "reason": "brief explanation"
    }
  ]
}
"""
```

Known inference rules to seed the prompt context:
- `Next.js` (≥2 yrs) → `React`
- `NestJS` → `Node.js`, `TypeScript`
- `Spring Boot` → `Java`
- `Django` / `FastAPI` → `Python`
- `React Native` → `React`
- `Kubernetes` → `Docker`
- `AWS` (broad) → implies basic `Linux`, `CI/CD`

### Extraction State Machine

```
resume_uploads.extraction_status:
  pending  →  processing  →  completed
                          →  failed

ai_profile_extractions.status:
  pending  →  processing  →  completed
                          →  failed
```

### Extraction Review (HR + Employee)

After extraction completes a `profile_reviews` row is created with `status = 'pending'`. The AI-extracted data is shown in a new **AI Extraction Review Panel** in the frontend before being committed to the normalized tables.

```
┌────────────────────────────────────────────────────────────────────┐
│  AI-Extracted Data — Please Review                                 │
│  Confidence: 92%                         [Accept All]  [Reject]   │
│ ─────────────────────────────────────────────────────────────────  │
│  Skills                    Experience                              │
│  ✓ React (Expert, 5 yrs)   ✓ Senior Dev @ Infosys (2020-2023)     │
│  ✓ Node.js (Intermediate)  ✓ SDE @ Wipro (2018-2020)              │
│  ⚠ Redux (inferred)                                                │
│                            Projects                                │
│  Certifications            ✓ E-Commerce App (React, Node, Mongo)  │
│  ✓ AWS SAA (2022)                                                  │
└────────────────────────────────────────────────────────────────────┘
```

- **Accept All** → `POST /api/v1/ai/extractions/{id}/accept/` → writes data to all normalized tables, marks extraction `completed`
- **Reject** → `POST /api/v1/ai/extractions/{id}/reject/` → marks extraction `failed`, profile stays as-is
- Employee can edit individual fields before accepting

---

## Hard Problem #2 — Semantic Natural Language Search

### Flow

```
HR types: "Find me a backend dev in Pune with at least 3 years Java and any payment gateway"
  ↓
POST /api/v1/search/
  ↓
  1. Claude parses query → structured intent JSON
       { skills: ["Java","payment gateway"], location: "Pune", min_years: 3, role_hint: "backend" }
  2. Generate query embedding (OpenAI text-embedding-3-small)
  3. pgvector cosine similarity search against employee_embeddings
       SELECT profile_id, 1 - (embedding <=> query_vec) AS similarity
       FROM employee_embeddings
       WHERE profile_id IN (approved employees only)
       ORDER BY similarity DESC LIMIT 50
  4. Apply hard filters: location ILIKE '%Pune%', experience_years >= 3
  5. Re-rank top 20 using Claude (combines semantic score + hard filter match + recency)
  6. For each result: Claude generates plain-English explanation
  7. Return ranked results with match_score (0–100) + explanation
```

### Claude Query Parser (`searcher.py`)

```python
QUERY_PARSE_PROMPT = """
Parse this HR search query into structured filters. Return JSON only.

{
  "skills_required": ["string"],
  "skills_nice_to_have": ["string"],
  "location": "string or null",
  "min_years_experience": number_or_null,
  "role_hint": "frontend|backend|fullstack|devops|mobile|data or null",
  "department": "string or null",
  "availability_hint": "bench|unallocated or null"
}
"""
```

### Embedding Generation (`embedder.py`)

Called when:
- Employee profile is approved by HR (first time)
- Employee edits their profile after approval (re-embed)
- HR manually triggers refresh

**What goes into `searchable_text`:**

```python
def build_searchable_text(profile: dict) -> str:
    parts = [
        f"{profile['full_name']}, {profile.get('designation','')}, {profile.get('department','')}",
        f"Location: {profile.get('location','')}",
        f"Experience: {profile.get('experience_years','')} years",
        f"Summary: {profile.get('summary','')}",
        "Skills: " + ", ".join(
            f"{s['name']} ({s['proficiency_level']}, {s.get('years_of_experience','')} yrs)"
            for s in profile['skills']
        ),
        "Projects: " + " | ".join(
            f"{p['name']}: {p.get('description','')} [{', '.join(p['tech_stack'])}]"
            for p in profile['projects']
        ),
        "Experience: " + " | ".join(
            f"{e['designation']} at {e['company_name']}"
            for e in profile['experiences']
        ),
        "Certifications: " + ", ".join(c['name'] for c in profile['certifications']),
    ]
    return "\n".join(filter(None, parts))
```

### Match Explanation (`explainer.py`)

```python
EXPLANATION_PROMPT = """
You are an HR assistant. Given this search query and this employee's profile summary,
generate a short 1–2 sentence explanation of why this person is a good match.
Be specific — mention skills, years, and project types. Be concise and factual.

Return JSON: { "explanation": "string", "match_score": 0-100 }
"""
```

Example output:
> *"Rahul — 94% match. Expert React developer (5 yrs) who has led 2 real-time apps using Socket.IO; currently unallocated and based in Pune."*

### pgvector SQL (`searcher.py`)

```python
SEARCH_SQL = """
SELECT
  ep.profile_id,
  p.full_name,
  p.designation,
  p.department,
  p.location,
  p.experience_years,
  p.profile_status,
  1 - (ee.embedding <=> %(query_embedding)s::vector) AS similarity
FROM employee_embeddings ee
JOIN profiles p ON p.id = ee.profile_id
WHERE
  p.role = 'employee'
  AND p.is_active = true
  AND p.profile_status = 'approved'
ORDER BY similarity DESC
LIMIT %(limit)s
"""
```

---

## New API Endpoints (Phase 3)

### AI Extraction

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/ai/extract/{resume_upload_id}/` | HR or self | Trigger extraction for a resume upload |
| `GET` | `/api/v1/ai/extractions/{profile_id}/` | HR or self | Get latest extraction status + extracted JSON |
| `POST` | `/api/v1/ai/extractions/{extraction_id}/accept/` | HR or self | Accept extraction → write to normalized tables |
| `POST` | `/api/v1/ai/extractions/{extraction_id}/reject/` | HR or self | Reject extraction |
| `POST` | `/api/v1/profiles/{id}/generate-embedding/` | HR | Generate / refresh embedding for a profile |

### Semantic Search

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/search/` | HR | NL query → ranked results with scores + explanations |
| `GET` | `/api/v1/search/{profile_id}/explain/` | HR | Re-generate explanation for one result (on demand) |

### Request / Response Shapes

**`POST /api/v1/search/`**

```json
// Request
{
  "query": "Find me a backend dev in Pune with 3+ years Java and payment gateway experience",
  "filters": {
    "location": null,
    "min_years": null,
    "department": null
  }
}

// Response
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

---

## Frontend Changes (Phase 3)

### 1. `NlpSearchBox.tsx` — wire to real API

- On submit: `POST /api/v1/search/` with the query text
- Show loading skeleton during search (typically 2–4 s)
- Display `query_parsed` as filter chips below the search box so HR can see what Claude understood

### 2. New: `SearchResults.tsx`

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

Fields shown per card:
- Full name, designation, department, location, experience
- **Match score badge** (color: green ≥80%, amber 60-79%, red <60%)
- Plain-English **explanation**
- Top skills as badge chips
- **View Profile** → existing `/hr/search/{id}/preview` page

### 3. New: `ExtractionReviewPanel.tsx`

Added to both `/hr/employees/[id]` and `/employee/profile` pages. Shown when `extraction_status = 'completed'` and the extraction has not yet been accepted or rejected.

Sections:
- **Summary** — extracted summary (editable)
- **Skills** — checkboxes, inferred skills marked with an "AI inferred" chip
- **Experience** — list with edit button per entry
- **Projects** — list with tech stack chips
- **Certifications** — list
- **Education** — list
- **[Accept All]** / **[Edit & Accept]** / **[Discard]** actions at the bottom

### 4. Resume Upload Auto-Trigger

In [ResumeUpload.tsx](../frontend/src/components/profile/ResumeUpload.tsx): after upload completes and returns a `resume_upload_id`, automatically call `POST /api/v1/ai/extract/{resume_upload_id}/` and show a progress indicator:

```
Processing...  🤖 AI is extracting your profile data
```

Poll `GET /api/v1/ai/extractions/{profile_id}/` every 3 seconds until `status = 'completed'` or `'failed'`. On completion, show the `ExtractionReviewPanel`.

---

## Backend File Layout (additions)

```
backend/apps/ai_integration/
├── __init__.py
├── apps.py
├── urls.py
├── views.py
│     ExtractionTriggerView       POST /ai/extract/{resume_upload_id}/
│     ExtractionStatusView        GET  /ai/extractions/{profile_id}/
│     ExtractionAcceptView        POST /ai/extractions/{id}/accept/
│     ExtractionRejectView        POST /ai/extractions/{id}/reject/
│     GenerateEmbeddingView       POST /profiles/{id}/generate-embedding/
│     SearchView                  POST /search/
│     ExplainMatchView            GET  /search/{profile_id}/explain/
├── serializers.py
│     ExtractionStatusSerializer
│     SearchQuerySerializer
│     SearchResultSerializer
├── text_extractor.py
│     extract_text(file_bytes: bytes, mime_type: str) -> str
├── extractor.py
│     extract_profile(text: str, profile_id: str) -> dict
│     _call_claude(prompt: str) -> dict
├── skill_inferrer.py
│     infer_skills(skills: list[dict]) -> list[dict]
├── embedder.py
│     generate_embedding(text: str) -> list[float]
├── profile_text_builder.py
│     build_searchable_text(profile_data: dict) -> str
├── searcher.py
│     parse_query(query: str) -> dict
│     search(query: str, filters: dict) -> list[dict]
│     _vector_search(embedding: list, limit: int) -> list
│     _apply_hard_filters(results: list, parsed: dict) -> list
└── explainer.py
      explain_match(query: str, profile_summary: str) -> dict
      bulk_explain(query: str, profiles: list) -> list[dict]
```

---

## Python Dependencies (additions to `requirements.txt`)

```
anthropic==0.30.0
requests==2.32.3          # Ollama HTTP API calls (likely already installed)
pdfminer.six==20231228
python-docx==1.1.2
pgvector==0.3.2
```

---

## Agent Responsibilities

| Agent | Phase 3 Tasks |
|---|---|
| `ai-integration-agent` | `text_extractor.py`, `extractor.py`, `skill_inferrer.py`, `embedder.py`, `profile_text_builder.py`, `searcher.py`, `explainer.py` — all AI/ML logic |
| `django-supabase-backend-dev` | `ai_integration` app scaffold, all 7 new API views, serializers, URL registration, Supabase Storage file download in trigger view, pgvector raw SQL execution in searcher |
| `nextjs-frontend-dev` | Wire `NlpSearchBox.tsx` to real API, `SearchResults.tsx`, `ExtractionReviewPanel.tsx`, polling logic in `ResumeUpload.tsx`, query_parsed chip display |

---

## Phase 3 Checklist

### Environment & Dependencies
- [ ] Install Ollama: `curl -fsSL https://ollama.com/install.sh | sh` (Linux) or download from ollama.com
- [ ] Pull embedding model: `ollama pull nomic-embed-text`
- [ ] Add `OLLAMA_BASE_URL`, `OLLAMA_EMBED_MODEL` to `backend/.env`
- [ ] Add `AI_EXTRACTION_CONFIDENCE_THRESHOLD`, `AI_INFERENCE_CONFIDENCE_THRESHOLD`, `SEARCH_MAX_RESULTS` to `.env`
- [ ] Install new Python packages: `anthropic pdfminer.six python-docx pgvector`
- [ ] Update schema dimension: run `ALTER TABLE employee_embeddings ALTER COLUMN embedding TYPE vector(768);` in Supabase SQL editor
- [ ] Verify `pgvector` extension is enabled in Supabase (already done in Phase 2.1 SQL)

### Backend — `ai_integration` App
- [ ] Create `apps/ai_integration/` directory and register in `INSTALLED_APPS`
- [ ] `text_extractor.py` — PDF and DOCX text extraction
- [ ] `extractor.py` — Claude extraction prompt, API call, JSON parsing, schema validation
- [ ] `skill_inferrer.py` — inference prompt + confidence filter + write to `inferred_skills`
- [ ] `embedder.py` — OpenAI `text-embedding-3-small` wrapper
- [ ] `profile_text_builder.py` — builds `searchable_text` from all normalized tables
- [ ] `searcher.py` — Claude query parser + pgvector SQL + hard filters
- [ ] `explainer.py` — Claude explanation + score generation (bulk, max 20 profiles per call)
- [ ] `views.py` — all 7 endpoint views
- [ ] `serializers.py` — request/response shapes
- [ ] `urls.py` — wire into `project/urls.py`

### Backend — Embedding Trigger
- [ ] Auto-generate embedding when a profile's `profile_status` changes to `'approved'`
  - Hook into `POST /api/v1/reviews/{id}/approve/` view (already exists) — call `generate_embedding` after approval
- [ ] `POST /api/v1/profiles/{id}/generate-embedding/` — manual refresh endpoint

### Backend — Extraction Flow
- [ ] `POST /api/v1/ai/extract/{resume_upload_id}/` — download from Supabase Storage, extract text, call Claude, write `ai_profile_extractions`, update `resume_uploads.extraction_status`
- [ ] `POST /api/v1/ai/extractions/{id}/accept/` — write skills/experiences/projects/certs/education to normalized tables, create `profile_reviews` entry (status='pending')
- [ ] `POST /api/v1/ai/extractions/{id}/reject/` — mark `ai_profile_extractions.status = 'failed'`

### Frontend — Search
- [ ] `NlpSearchBox.tsx` — call `POST /api/v1/search/`, handle loading + error states
- [ ] `SearchResults.tsx` — result cards with match score badge, explanation, skill chips, View Profile link
- [ ] Show `query_parsed` as filter chips below search box
- [ ] Empty state: "No profiles match your search — try different skills or location"
- [ ] Error state: "Search unavailable — try again"

### Frontend — Extraction Review
- [ ] `ExtractionReviewPanel.tsx` — sections per extracted category, inferred skill chips, Accept/Discard actions
- [ ] `ResumeUpload.tsx` — auto-trigger extraction after upload, poll for status, show panel on completion
- [ ] Show extraction panel on `/employee/profile` and `/hr/employees/[id]`

---

## Error Handling & Edge Cases

| Scenario | Handling |
|---|---|
| Claude returns invalid JSON | Retry once with a stricter prompt; on second failure mark `extraction_status = 'failed'`, show "Extraction failed — please fill in your profile manually" |
| Resume has no extractable text (scanned image PDF) | `text_extractor.py` returns empty string → skip Claude call, mark failed, notify user |
| No approved employee profiles in database | Search returns `{ results: [], total: 0 }` with message "No approved profiles yet" |
| Employee edits profile after embedding generated | Mark `employee_embeddings.updated_at` stale; HR can trigger refresh manually via Generate Embedding button |
| OpenAI embedding API down | Cache last good embedding; return `503` on search with message "Search temporarily unavailable" |
| Query too vague (< 3 words) | Frontend validation: disable Search button and show hint "Try adding skills, location, or experience level" |

---

## Running Locally (Phase 3 additions)

```bash
# Backend — install new dependencies
cd backend
pip install -r requirements.txt

# Start Ollama (run once, stays running in background)
ollama serve &
ollama pull nomic-embed-text

# Verify Ollama embedding works
curl http://localhost:11434/api/embeddings \
  -d '{"model":"nomic-embed-text","prompt":"test"}' | python -c "
import sys, json; d=json.load(sys.stdin); print('dims:', len(d['embedding']))
"
# should print: dims: 768

# Verify Anthropic key works
python -c "import anthropic; c = anthropic.Anthropic(); print('ok')"

# Test extraction on a sample resume
python manage.py shell -c "
from apps.ai_integration.text_extractor import extract_text
with open('/tmp/sample.pdf', 'rb') as f:
    print(extract_text(f.read(), 'application/pdf')[:500])
"

# Frontend — no new packages needed; polling uses existing fetch wrapper
cd frontend
pnpm dev
```

---

## Sequence Diagram — Full Ingestion Flow

```
Employee        Frontend            Backend              Claude         OpenAI        Supabase
   |                |                  |                   |              |              |
   |-- upload PDF ->|                  |                   |              |              |
   |                |-- POST /resume ->|                   |              |              |
   |                |                 |-- store file ------------------>--|              |
   |                |<- {upload_id} --|                   |              |              |
   |                |                  |                   |              |              |
   |                |-- POST /extract->|                   |              |              |
   |                |                 |-- download file ----------------->|              |
   |                |                 |-- extract text    |              |              |
   |                |                 |-- call Claude --->|              |              |
   |                |                 |<- extracted JSON -|              |              |
   |                |                 |-- call Claude (inference) ------->|              |
   |                |                 |<- inferred skills |              |              |
   |                |                 |-- write ai_profile_extractions -->|              |
   |                |<- {status:ok} --|                   |              |              |
   |                |                  |                   |              |              |
   |-- review panel |                  |                   |              |              |
   |-- [Accept] --->|                  |                   |              |              |
   |                |-- POST /accept ->|                   |              |              |
   |                |                 |-- write normalized tables ------->|              |
   |                |                 |-- embed profile ----------------->|              |
   |                |                 |<- vector[1536]    |              |              |
   |                |                 |-- store embedding --------------->|              |
   |                |<- {ok} ---------|                   |              |              |
```

## Sequence Diagram — Semantic Search Flow

```
HR              Frontend            Backend              Claude         OpenAI        Supabase
  |                |                  |                   |              |              |
  |-- type query ->|                  |                   |              |              |
  |                |-- POST /search ->|                   |              |              |
  |                |                 |-- parse query --->|              |              |
  |                |                 |<- structured intent              |              |
  |                |                 |-- embed query ------------------>|              |
  |                |                 |<- vector[1536]    |              |              |
  |                |                 |-- cosine search ----------------->|              |
  |                |                 |<- top 50 profiles |              |              |
  |                |                 |-- apply hard filters              |              |
  |                |                 |-- bulk explain -->|              |              |
  |                |                 |<- scores + text   |              |              |
  |                |<- ranked results|                   |              |              |
  |-- see results -|                 |                   |              |              |
```

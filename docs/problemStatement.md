# Skills Intelligence Platform — Problem Overview

## The Problem

Developer skills data in most software companies lives in scattered spreadsheets, stale profiles, or someone's memory. When HR needs to staff a project, finding the right person means pinging managers manually — slow, error-prone, and unscalable.

---

## What We're Building

A **skills intelligence platform** with two user roles:

| Role | Responsibilities |
|------|-----------------|
| **HR Team** | Manages the skills database, uploads employee data, searches using natural language, reviews and approves AI-extracted profiles |
| **Employees** | Upload resumes or LinkedIn exports for auto-extraction, review and refine their profiles, add proficiency levels, projects, and certifications |

---

## The Two Hard Problems

### Hard Problem #1 · Smart Profile Ingestion

When an employee uploads a resume (PDF) or pastes a LinkedIn profile, the system should:

- Auto-extract structured skill data — technologies, proficiency levels, years of experience, and projects
- Send extracted profiles to a **review queue** for HR or employee correction before acceptance
- **Bonus:** Infer related skills not explicitly mentioned (e.g., 4 years of Next.js → implicit React expertise)

### Hard Problem #2 · Semantic Natural Language Search

HR should be able to ask real questions in plain English and get **ranked, explained results** — not keyword matches.

**Example queries:**
- *"Who can lead a React project that also needs WebSocket experience?"*
- *"Find me a backend dev in Pune with at least 3 years of Java and any payment gateway integration."*
- *"Senior frontend folks who haven't been on a new project in the last quarter."*

**Each result must include:**
- A **match score** (e.g., 94%)
- A **plain-English explanation** (e.g., *"Rahul — 94% match. Expert in React (5 yrs), led 2 real-time apps using Socket.IO, currently unallocated."*)

---

## Key Principles

- **AI-powered extraction** — not manual data entry
- **Semantic understanding** — not dumb keyword matching
- **Transparent reasoning** — every result is explainable
- **Human-in-the-loop** — HR and employees can review and correct AI output

---

## Tech Challenges at a Glance

```
Resume/LinkedIn Input
        ↓
   AI Extraction  ←── Hard Problem #1
        ↓
  Review & Approval
        ↓
  Skills Database
        ↓
  NL Search Query ←── Hard Problem #2
        ↓
  Ranked Results with Scores + Explanations
```

---

> **The rest is CRUD. Win the hackathon by nailing ingestion and search.**

---

## Further Reading

| Document | What It Covers |
|---|---|
| [NLP.md](./NLP.md) | Full design & implementation guide for the HR Smart Search (Hard Problem #2) — pipeline, API contract, UI, embedding strategy, and approved-only search constraint |
| [phase-3.md](./phase-3.md) | Complete Phase 3 plan covering both Hard Problem #1 (ingestion) and Hard Problem #2 (search) |
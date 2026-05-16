from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
import pptx.oxml.ns as nsmap
from lxml import etree

# Color palette
DARK_BG     = RGBColor(0x0F, 0x17, 0x2A)   # deep navy
ACCENT      = RGBColor(0x4F, 0x8E, 0xFF)   # electric blue
ACCENT2     = RGBColor(0x00, 0xD4, 0xAA)   # teal
ACCENT3     = RGBColor(0xFF, 0x6B, 0x6B)   # coral
WHITE       = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GREY  = RGBColor(0xB0, 0xBE, 0xD4)
CARD_BG     = RGBColor(0x1A, 0x27, 0x42)   # slightly lighter navy

prs = Presentation()
prs.slide_width  = Inches(13.33)
prs.slide_height = Inches(7.5)

BLANK = prs.slide_layouts[6]  # completely blank


# ─── helpers ────────────────────────────────────────────────────────────────

def bg(slide, color=DARK_BG):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color

def rect(slide, l, t, w, h, fill_color, alpha=None):
    shape = slide.shapes.add_shape(1, Inches(l), Inches(t), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    shape.line.fill.background()
    return shape

def accent_bar(slide, color=ACCENT):
    rect(slide, 0, 0, 13.33, 0.06, color)

def txbox(slide, text, l, t, w, h, size=18, bold=False, color=WHITE,
          align=PP_ALIGN.LEFT, italic=False, wrap=True):
    tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tb.word_wrap = wrap
    tf = tb.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return tb

def tag_box(slide, text, l, t, w=1.8, h=0.38, color=ACCENT):
    shape = rect(slide, l, t, w, h, color)
    tf = shape.text_frame
    tf.word_wrap = False
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = text
    run.font.size = Pt(11)
    run.font.bold = True
    run.font.color.rgb = WHITE

def card(slide, l, t, w, h, title, body_lines, title_color=ACCENT):
    rect(slide, l, t, w, h, CARD_BG)
    # top accent strip
    rect(slide, l, t, w, 0.04, title_color)
    # title
    txbox(slide, title, l+0.15, t+0.12, w-0.3, 0.4, size=14, bold=True, color=title_color)
    # body
    body_text = "\n".join(body_lines)
    txbox(slide, body_text, l+0.15, t+0.55, w-0.3, h-0.7, size=11, color=LIGHT_GREY)

def arrow_right(slide, l, t, length=0.55, color=ACCENT):
    """Draw a horizontal right-pointing arrow."""
    cx = Inches(l)
    cy = Inches(t)
    cw = Inches(length)
    ch = Inches(0.25)
    shape = slide.shapes.add_shape(
        13,  # right arrow
        cx, cy, cw, ch
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 1 — Platform Overview Flow (Part 1): Users & Core Concept
# ════════════════════════════════════════════════════════════════════════════
s1 = prs.slides.add_slide(BLANK)
bg(s1)
accent_bar(s1)

# Title area
rect(s1, 0, 0.06, 13.33, 1.35, CARD_BG)
txbox(s1, "TalentExe — Platform Flow  (1/2)", 0.4, 0.15, 10, 0.55,
      size=30, bold=True, color=WHITE, align=PP_ALIGN.LEFT)
txbox(s1, "Skills Intelligence Platform · Who does what and how the system is structured",
      0.4, 0.72, 10, 0.55, size=15, color=LIGHT_GREY)

# Two-column: Roles
txbox(s1, "USER ROLES", 0.4, 1.6, 4, 0.4, size=12, bold=True, color=ACCENT)
card(s1, 0.4, 2.0, 5.7, 2.1, "HR Team",
     ["• Manages the skills database",
      "• Adds & onboards employees",
      "• Reviews and approves AI-extracted profiles",
      "• Searches talent using natural language"],
     title_color=ACCENT)
card(s1, 0.4, 4.2, 5.7, 2.1, "Employee",
     ["• Uploads resume or LinkedIn export",
      "• Reviews AI-extracted profile data",
      "• Refines skills, projects & certifications",
      "• Submits profile for HR approval"],
     title_color=ACCENT2)

# Right column: System layers
txbox(s1, "SYSTEM LAYERS", 6.8, 1.6, 6, 0.4, size=12, bold=True, color=ACCENT)

layers = [
    ("Next.js Frontend", "App Router · Tailwind CSS · shadcn/ui", ACCENT),
    ("Django + DRF Backend", "REST API · Supabase JWT auth · role routing", ACCENT2),
    ("Supabase (PostgreSQL)", "Profiles · Reviews · Resume uploads · RLS policies", ACCENT3),
    ("AI Layer (Phase 3)", "Claude claude-sonnet-4-6 · Ollama embeddings · pgvector", RGBColor(0xFF,0xA5,0x00)),
]
y = 2.0
for title, body, color in layers:
    rect(s1, 6.8, y, 6.1, 0.78, CARD_BG)
    rect(s1, 6.8, y, 0.08, 0.78, color)
    txbox(s1, title, 7.05, y+0.05, 5.8, 0.35, size=13, bold=True, color=color)
    txbox(s1, body,  7.05, y+0.4,  5.8, 0.32, size=11, color=LIGHT_GREY)
    y += 0.88

# Slide number
txbox(s1, "01", 12.8, 7.1, 0.5, 0.35, size=11, color=LIGHT_GREY, align=PP_ALIGN.RIGHT)


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 2 — Platform Flow (Part 2): End-to-End User Journey
# ════════════════════════════════════════════════════════════════════════════
s2 = prs.slides.add_slide(BLANK)
bg(s2)
accent_bar(s2, color=ACCENT2)

rect(s2, 0, 0.06, 13.33, 1.35, CARD_BG)
txbox(s2, "TalentExe — Platform Flow  (2/2)", 0.4, 0.15, 10, 0.55,
      size=30, bold=True, color=WHITE)
txbox(s2, "End-to-end journey from onboarding to HR talent discovery",
      0.4, 0.72, 10, 0.55, size=15, color=LIGHT_GREY)

# Flow steps as numbered boxes
steps = [
    ("1", "Admin Creates\nUser", "Admin fills form → temp\ncredentials sent via Brevo SMTP", ACCENT),
    ("2", "First Login &\nPassword Setup", "User logs in → forced\npassword change flow", ACCENT2),
    ("3", "Employee Builds\nProfile", "Manual entry + resume\nupload (PDF/DOCX)", ACCENT3),
    ("4", "Submit for\nReview", "Profile goes to HR\nReview Queue", RGBColor(0xFF,0xA5,0x00)),
    ("5", "HR Approves\nProfile", "HR approves / rejects\nwith comments + email", ACCENT),
    ("6", "Profile becomes\nSearchable", "Embeddings generated →\nvisible in NLP search", ACCENT2),
]

x = 0.35
for num, title, body, color in steps:
    rect(s2, x, 1.7, 2.0, 2.5, CARD_BG)
    # number badge
    badge = slide_rect = rect(s2, x+0.75, 1.7, 0.5, 0.5, color)
    txbox(s2, num, x+0.75, 1.72, 0.5, 0.46, size=18, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    txbox(s2, title, x+0.1, 2.28, 1.8, 0.55, size=12, bold=True, color=color, align=PP_ALIGN.CENTER)
    txbox(s2, body,  x+0.1, 2.88, 1.8, 0.9,  size=10, color=LIGHT_GREY, align=PP_ALIGN.CENTER)
    if num != "6":
        arrow_right(s2, x+2.0, 2.85, length=0.35, color=color)
    x += 2.2

# Auth flow detail
txbox(s2, "AUTH FLOW DETAIL", 0.4, 4.5, 12, 0.38, size=12, bold=True, color=ACCENT)
auth_flow = "/login  →  supabase.signInWithPassword()  →  JWT issued  →  GET /api/v1/auth/me/  →  role resolved  →  middleware.ts routes:  hr → /hr/dashboard  |  employee → /employee/profile"
txbox(s2, auth_flow, 0.4, 4.9, 12.5, 0.6, size=11, color=LIGHT_GREY)

# Phase labels
phases = [("Phase 1", 0.35, ACCENT), ("Phase 2", 4.75, ACCENT2), ("Phase 3", 9.15, ACCENT3)]
for label, lx, color in phases:
    tag_box(s2, label, lx, 5.65, w=1.8, h=0.35, color=color)

txbox(s2, "Foundation · Auth · Admin Panel", 0.35, 6.05, 4.0, 0.4, size=10, color=LIGHT_GREY)
txbox(s2, "Full CRUD · Email · Review Queue", 4.75, 6.05, 4.0, 0.4, size=10, color=LIGHT_GREY)
txbox(s2, "AI Extraction · Semantic Search",  9.15, 6.05, 4.0, 0.4, size=10, color=LIGHT_GREY)

txbox(s2, "02", 12.8, 7.1, 0.5, 0.35, size=11, color=LIGHT_GREY, align=PP_ALIGN.RIGHT)


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 3 — PDF Extract & AI Use (Part 1): Ingestion Pipeline
# ════════════════════════════════════════════════════════════════════════════
s3 = prs.slides.add_slide(BLANK)
bg(s3)
accent_bar(s3, color=ACCENT3)

rect(s3, 0, 0.06, 13.33, 1.35, CARD_BG)
txbox(s3, "PDF Extract & AI Use  (1/2)", 0.4, 0.15, 10, 0.55,
      size=30, bold=True, color=WHITE)
txbox(s3, "How uploaded resumes are parsed, structured, and enriched by Claude",
      0.4, 0.72, 10, 0.55, size=15, color=LIGHT_GREY)

# Pipeline steps
txbox(s3, "INGESTION PIPELINE", 0.4, 1.6, 12, 0.4, size=12, bold=True, color=ACCENT3)

pipe_steps = [
    ("PDF/DOCX\nUpload", "Employee uploads resume\n≤10MB · .pdf/.doc/.docx\nStored in Supabase Storage", ACCENT),
    ("Text\nExtraction", "pdfminer.six for PDF\npython-docx for DOCX\nRaw text extracted", ACCENT2),
    ("Claude\nExtraction", "claude-sonnet-4-6 parses\nskills · experience · projects\ncertifications · education", ACCENT3),
    ("Skill\nInference", "Claude infers related skills\ne.g. Next.js → React\nConfidence scored 0–1", RGBColor(0xFF,0xA5,0x00)),
    ("Review\nQueue", "Extracted data held\nfor HR + employee review\nbefore acceptance", ACCENT),
    ("Profile\nActivated", "Approved → Embeddings\ngenerated → searchable\nin NLP system", ACCENT2),
]

x = 0.3
for title, body, color in pipe_steps:
    rect(s3, x, 2.1, 1.9, 2.8, CARD_BG)
    rect(s3, x, 2.1, 1.9, 0.06, color)
    txbox(s3, title, x+0.05, 2.18, 1.8, 0.55, size=13, bold=True, color=color, align=PP_ALIGN.CENTER)
    txbox(s3, body,  x+0.05, 2.78, 1.8, 1.5,  size=10, color=LIGHT_GREY, align=PP_ALIGN.CENTER)
    if title != "Profile\nActivated":
        arrow_right(s3, x+1.9, 3.35, length=0.35, color=color)
    x += 2.22

# Claude extraction detail
txbox(s3, "WHAT CLAUDE EXTRACTS", 0.4, 5.1, 12, 0.38, size=12, bold=True, color=ACCENT3)
fields = [
    ("Skills", "name · proficiency level\n(Beginner/Intermediate/Expert) · years", 0.4),
    ("Work Experience", "company · role · dates\ndescription · duration", 3.2),
    ("Projects", "name · tech stack\ndescription · duration", 6.0),
    ("Education &\nCertifications", "degree · institution · year\ncert name · issuer · dates", 8.8),
]
for title, body, lx in fields:
    rect(s3, lx, 5.55, 2.55, 1.6, CARD_BG)
    txbox(s3, title, lx+0.1, 5.62, 2.35, 0.45, size=12, bold=True, color=ACCENT3)
    txbox(s3, body,  lx+0.1, 6.1,  2.35, 0.95, size=10, color=LIGHT_GREY)

txbox(s3, "03", 12.8, 7.1, 0.5, 0.35, size=11, color=LIGHT_GREY, align=PP_ALIGN.RIGHT)


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 4 — PDF Extract & AI Use (Part 2): Review Flow & State Machine
# ════════════════════════════════════════════════════════════════════════════
s4 = prs.slides.add_slide(BLANK)
bg(s4)
accent_bar(s4, color=ACCENT3)

rect(s4, 0, 0.06, 13.33, 1.35, CARD_BG)
txbox(s4, "PDF Extract & AI Use  (2/2)", 0.4, 0.15, 10, 0.55,
      size=30, bold=True, color=WHITE)
txbox(s4, "Human-in-the-loop review, profile state machine, and AI confidence scoring",
      0.4, 0.72, 10, 0.55, size=15, color=LIGHT_GREY)

# Left: State machine
txbox(s4, "PROFILE STATUS STATE MACHINE", 0.4, 1.6, 6, 0.38, size=12, bold=True, color=ACCENT3)
states = [
    ("incomplete", "Profile created,\nno data yet", LIGHT_GREY),
    ("submitted",  "Employee submitted\nfor HR review", RGBColor(0xFF,0xA5,0x00)),
    ("approved",   "HR approved →\nsearchable", RGBColor(0x00,0xC0,0x70)),
    ("rejected",   "HR rejected with\ncomment → re-edit", ACCENT3),
]
y = 2.1
for state, desc, color in states:
    rect(s4, 0.4, y, 2.6, 0.75, CARD_BG)
    rect(s4, 0.4, y, 0.12, 0.75, color)
    txbox(s4, state.upper(), 0.62, y+0.05, 2.3, 0.3, size=12, bold=True, color=color)
    txbox(s4, desc, 0.62, y+0.38, 2.3, 0.32, size=10, color=LIGHT_GREY)
    if state != "rejected":
        txbox(s4, "↓", 1.55, y+0.75, 0.4, 0.3, size=14, color=LIGHT_GREY, align=PP_ALIGN.CENTER)
    y += 1.05

# Right: AI confidence & inference
txbox(s4, "AI CONFIDENCE SCORING", 6.8, 1.6, 6, 0.38, size=12, bold=True, color=ACCENT3)

conf_items = [
    ("Extraction Threshold", "0.7 (default)", "Skills/experience items below\nthis score are flagged for review", ACCENT),
    ("Inference Threshold", "0.6 (default)", "Inferred skills below this score\nare excluded from profile", ACCENT2),
    ("Match Score Range", "0 – 100", "Search result scoring by\nClaude against query intent", ACCENT3),
]
y = 2.1
for title, val, desc, color in conf_items:
    rect(s4, 6.8, y, 6.1, 1.1, CARD_BG)
    txbox(s4, title, 6.95, y+0.08, 3.2, 0.35, size=12, bold=True, color=color)
    txbox(s4, val,   10.5, y+0.08, 2.2, 0.35, size=18, bold=True, color=color, align=PP_ALIGN.RIGHT)
    txbox(s4, desc,  6.95, y+0.52, 5.8, 0.5,  size=10, color=LIGHT_GREY)
    y += 1.2

# Extraction prompt summary
txbox(s4, "CLAUDE EXTRACTION PROMPT PATTERN", 6.8, 5.7, 6, 0.38, size=12, bold=True, color=ACCENT3)
prompt_text = (
    'System: "Parse this resume text and return structured JSON.\n'
    'Extract: skills (name, proficiency, years), experience (company, role,\n'
    'dates), projects (name, tech, description), certifications, education.\n'
    'For each item, include a confidence score 0.0–1.0."'
)
rect(s4, 6.8, 6.12, 6.1, 1.1, RGBColor(0x10,0x1E,0x38))
txbox(s4, prompt_text, 6.95, 6.16, 5.9, 1.0, size=9.5, color=LIGHT_GREY, italic=True)

txbox(s4, "04", 12.8, 7.1, 0.5, 0.35, size=11, color=LIGHT_GREY, align=PP_ALIGN.RIGHT)


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 5 — NLP Use & Flow (Part 1): Pipeline Architecture
# ════════════════════════════════════════════════════════════════════════════
s5 = prs.slides.add_slide(BLANK)
bg(s5)
accent_bar(s5, color=ACCENT2)

rect(s5, 0, 0.06, 13.33, 1.35, CARD_BG)
txbox(s5, "NLP Use & Flow  (1/2)", 0.4, 0.15, 10, 0.55,
      size=30, bold=True, color=WHITE)
txbox(s5, "Semantic natural language search — 6-step pipeline from HR query to ranked results",
      0.4, 0.72, 10, 0.55, size=15, color=LIGHT_GREY)

# 6-step pipeline
steps = [
    ("Step 1", "Query\nParsing", "Claude converts plain-English\nquery → structured JSON intent\n{skills, location, min_years,\nrole_hint, availability}", ACCENT),
    ("Step 2", "Query\nEmbedding", "Ollama nomic-embed-text\nconverts full query text into\na 768-dimensional vector\nrepresentation", ACCENT2),
    ("Step 3", "Vector\nSimilarity", "pgvector cosine search\nagainst pre-computed profile\nembeddings. Top 50 profiles\nreturned (approved only)", ACCENT3),
    ("Step 4", "Hard\nFilters", "Deterministic Python filters:\nlocation · min years exp\ndepartment. Capped\nat top 20 results", RGBColor(0xFF,0xA5,0x00)),
    ("Step 5", "Match\nExplanation", "Single bulk Claude call:\nscores each profile 0–100\n+ 1-2 sentence plain-English\nexplanation per result", ACCENT),
    ("Step 6", "Response\nto Frontend", "Ranked list: match_score,\nexplanation, top_skills,\nprofile link, filter chips\nshown to HR", ACCENT2),
]

x = 0.28
for step_num, title, body, color in steps:
    rect(s5, x, 1.65, 2.05, 3.2, CARD_BG)
    rect(s5, x, 1.65, 2.05, 0.06, color)
    tag_box(s5, step_num, x+0.13, 1.75, w=1.8, h=0.32, color=color)
    txbox(s5, title, x+0.08, 2.15, 1.9, 0.5, size=13, bold=True, color=color, align=PP_ALIGN.CENTER)
    txbox(s5, body,  x+0.08, 2.7,  1.9, 1.7, size=10, color=LIGHT_GREY, align=PP_ALIGN.CENTER)
    if step_num != "Step 6":
        arrow_right(s5, x+2.05, 3.1, length=0.23, color=color)
    x += 2.175

# Tech stack for search
txbox(s5, "TECHNOLOGY STACK FOR SEARCH", 0.4, 5.05, 12, 0.38, size=12, bold=True, color=ACCENT2)
tech = [
    ("Query Intent Parsing", "Claude claude-sonnet-4-6", "Understands ambiguous HR language", 0.4, ACCENT),
    ("Embeddings", "Ollama nomic-embed-text  (768d)", "Free, runs locally, no API cost", 4.55, ACCENT2),
    ("Vector Search", "pgvector cosine  (<=>)", "Already enabled in Supabase", 8.7, ACCENT3),
]
for t_title, t_tech, t_why, tx, color in tech:
    rect(s5, tx, 5.5, 3.8, 1.7, CARD_BG)
    txbox(s5, t_title, tx+0.12, 5.58, 3.6, 0.36, size=11, bold=True, color=color)
    txbox(s5, t_tech,  tx+0.12, 5.96, 3.6, 0.38, size=13, bold=True, color=WHITE)
    txbox(s5, t_why,   tx+0.12, 6.38, 3.6, 0.55, size=10, color=LIGHT_GREY)

txbox(s5, "05", 12.8, 7.1, 0.5, 0.35, size=11, color=LIGHT_GREY, align=PP_ALIGN.RIGHT)


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 6 — NLP Use & Flow (Part 2): UI, API Contract & Example
# ════════════════════════════════════════════════════════════════════════════
s6 = prs.slides.add_slide(BLANK)
bg(s6)
accent_bar(s6, color=ACCENT2)

rect(s6, 0, 0.06, 13.33, 1.35, CARD_BG)
txbox(s6, "NLP Use & Flow  (2/2)", 0.4, 0.15, 10, 0.55,
      size=30, bold=True, color=WHITE)
txbox(s6, "HR Smart Search UI, API contract, and a worked example end-to-end",
      0.4, 0.72, 10, 0.55, size=15, color=LIGHT_GREY)

# Left: HR Search UI mockup
txbox(s6, "HR SMART SEARCH UI", 0.4, 1.6, 5.5, 0.38, size=12, bold=True, color=ACCENT2)
rect(s6, 0.4, 2.05, 5.7, 4.9, RGBColor(0x10,0x1E,0x38))
ui_text = (
    '┌─────────────────────────────────────────┐\n'
    '│  🔍  "Find backend dev in Pune,         │\n'
    '│        3+ yrs Java, payment gateway"    │\n'
    '│                            [Search]     │\n'
    '└─────────────────────────────────────────┘\n'
    '\n'
    'Filter chips (from Claude parse):\n'
    '[Skills: Java, payment gateway]\n'
    '[Location: Pune]  [Min Exp: 3 yrs]\n'
    '[Role: backend]\n'
    '\n'
    '┌──────────────────────────── 94% ─────┐\n'
    '│ Rahul Sharma                  match  │\n'
    '│ Sr. Backend Dev · Engineering · Pune │\n'
    '│ Expert Java dev (6 yrs), Razorpay    │\n'
    '│ & PayU integration. Unallocated.     │\n'
    '│ [Java][Spring Boot][Razorpay]        │\n'
    '│                       [View Profile] │\n'
    '└──────────────────────────────────────┘'
)
txbox(s6, ui_text, 0.5, 2.1, 5.5, 4.75, size=9.5, color=RGBColor(0x7F,0xBF,0xFF), italic=False)

# Right: API contract + score guide
txbox(s6, "API CONTRACT  —  POST /api/v1/search/", 6.6, 1.6, 6.4, 0.38, size=12, bold=True, color=ACCENT2)
rect(s6, 6.6, 2.05, 6.4, 2.4, RGBColor(0x10,0x1E,0x38))
api_text = (
    'Request:\n'
    '{ "query": "backend dev Pune 3+ yrs Java" }\n'
    '\n'
    'Response data:\n'
    '{ "query_parsed": { "skills_required": ["Java",\n'
    '    "payment gateway"], "location": "Pune",\n'
    '    "min_years_experience": 3, "role_hint": "backend" },\n'
    '  "results": [ { "full_name": "Rahul Sharma",\n'
    '    "match_score": 94, "similarity": 0.94,\n'
    '    "explanation": "Expert Java dev (6 yrs)..." } ],\n'
    '  "total": 12 }'
)
txbox(s6, api_text, 6.75, 2.1, 6.1, 2.3, size=9, color=RGBColor(0x7F,0xBF,0xFF), italic=True)

# Score guide
txbox(s6, "MATCH SCORE GUIDE", 6.6, 4.6, 6.4, 0.38, size=12, bold=True, color=ACCENT2)
scores = [
    ("90 – 100", "All required skills + location + experience matched", RGBColor(0x00,0xC0,0x70)),
    ("70 – 89",  "Most required skills matched, minor gaps", RGBColor(0xFF,0xA5,0x00)),
    ("50 – 69",  "Partial match, some relevant experience", ACCENT3),
    ("< 50",     "Weak match — shown last, visually muted", LIGHT_GREY),
]
y = 5.05
for score, label, color in scores:
    rect(s6, 6.6, y, 1.0, 0.42, color)
    txbox(s6, score, 6.6, y+0.04, 1.0, 0.34, size=11, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    txbox(s6, label, 7.68, y+0.06, 5.2, 0.3, size=10.5, color=LIGHT_GREY)
    y += 0.5

# Embedding trigger
txbox(s6, "EMBEDDING TRIGGERS", 6.6, 7.05, 6.4, 0.38, size=11, bold=True, color=ACCENT2)

txbox(s6, "06", 12.8, 7.1, 0.5, 0.35, size=11, color=LIGHT_GREY, align=PP_ALIGN.RIGHT)


# ─── Save ────────────────────────────────────────────────────────────────────
out_path = "/home/saurabhd/Hackathon/Talentexe/docs/Presentation_documentation.pptx"
prs.save(out_path)
print(f"Saved: {out_path}")

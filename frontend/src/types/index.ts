// ─── Auth ────────────────────────────────────────────────────────────────────

export interface MeResponse {
  data: {
    role: 'hr' | 'employee'
    must_change_password: boolean
    user_id: string
    email: string
    full_name: string
    avatar_url?: string
  }
  error: string | null
}

// ─── Profile ─────────────────────────────────────────────────────────────────

export type ProfileStatus = 'incomplete' | 'submitted' | 'approved' | 'rejected'
export type SkillProficiency = 'Beginner' | 'Intermediate' | 'Expert'
export type LanguageProficiency = 'Native' | 'Fluent' | 'Intermediate' | 'Basic'

export interface Skill {
  id?: string
  name: string
  proficiency: SkillProficiency
  years: number
}

export interface ExperienceEntry {
  id?: string
  company: string
  role: string
  start_date: string
  end_date: string | null
  description: string
}

export interface ProjectEntry {
  id?: string
  name: string
  description: string
  tech_stack: string[]
  duration: string
}

export interface EducationEntry {
  id?: string
  degree: string
  institution: string
  graduation_year: number
}

export interface Certification {
  id?: string
  name: string
  issuer: string
  issued_date: string
  expiry_date: string | null
}

export interface Language {
  id?: string
  name: string
  proficiency: LanguageProficiency
}

export interface Links {
  linkedin: string
  github: string
  portfolio: string
}

export interface Profile {
  id: string
  user_id: string
  full_name: string
  email: string
  phone: string
  designation: string
  department: string
  location: string
  experience_years: number | null
  summary: string
  status: ProfileStatus
  avatar_url: string | null
  resume_file_name: string | null
  resume_uploaded_at: string | null
  skills: Skill[]
  experience: ExperienceEntry[]
  projects: ProjectEntry[]
  education: EducationEntry[]
  certifications: Certification[]
  languages: Language[]
  links: Links
  created_at: string
  updated_at: string
}

// ─── Employee List ────────────────────────────────────────────────────────────

export interface EmployeeListItem {
  id: string
  full_name: string
  email: string
  role?: string
  designation: string | null
  department: string | null
  location: string | null
  experience_years: number | null
  skills?: Skill[]
  status: ProfileStatus
  is_active: boolean
}

export interface PaginatedResponse<T> {
  data: T[]
  meta: {
    total: number
    page: number
    page_size: number
    total_pages: number
  }
  error: string | null
}

// ─── Dashboard Stats ─────────────────────────────────────────────────────────

export interface DashboardStats {
  total_employees: number
  pending_reviews: number
  incomplete_profiles: number
  approved_profiles: number
  bench_employees: number
  top_skills: Array<{ name: string; count: number }>
}

// ─── Review ───────────────────────────────────────────────────────────────────

export type ReviewStatus = 'pending' | 'approved' | 'rejected'

export interface Review {
  id: string
  profile_id: string
  employee_name: string
  employee_email: string
  employee_designation: string | null
  employee_department: string | null
  reviewed_by_name: string | null
  status: ReviewStatus
  hr_comment: string | null
  submitted_at: string
  reviewed_at: string | null
}

// ─── Bulk Upload ──────────────────────────────────────────────────────────────

export interface BulkUploadResult {
  created: number
  skipped: number
  errors: string[]
}

// ─── NLP Search ───────────────────────────────────────────────────────────────

export interface QueryParsed {
  skills_required: string[]
  skills_nice_to_have: string[]
  location: string | null
  min_years_experience: number | null
  role_hint: string | null
  department: string | null
  availability_hint: string | null
}

export interface SearchResult {
  profile_id: string
  full_name: string
  designation: string | null
  department: string | null
  location: string | null
  experience_years: number | null
  profile_status: string
  match_score: number
  explanation: string
  top_skills: string[]
  similarity: number
  avatar_url?: string | null
}

export interface SearchResponse {
  query_parsed: QueryParsed
  results: SearchResult[]
  total: number
}

// ─── API envelope ─────────────────────────────────────────────────────────────

export interface ApiEnvelope<T> {
  data: T
  error: string | null
  meta: Record<string, unknown>
}

// ─── Normalized section types (Phase 2.1) ─────────────────────────────────────

export interface EmployeeSkill {
  id: string
  skill_id: string
  name: string
  category?: string
  proficiency_level: 'Beginner' | 'Intermediate' | 'Expert'
  years_of_experience?: number
  is_primary: boolean
  source: 'manual' | 'ai_extracted' | 'inferred'
  verified_by_hr: boolean
}

export interface EmployeeExperience {
  id?: string
  company_name: string
  designation: string
  employment_type?: string
  start_date: string
  end_date?: string | null
  is_current: boolean
  location?: string
  description?: string
}

export interface NormalizedProject {
  id?: string
  name: string
  client_name?: string
  description?: string
  role?: string
  team_size?: number | null
  start_date?: string | null
  end_date?: string | null
  is_current: boolean
  skills?: Array<{ skill_id: string; name: string }>
  skill_names?: string[]
}

export interface NormalizedCertification {
  id?: string
  name: string
  issuer?: string
  issue_date?: string | null
  expiry_date?: string | null
  credential_url?: string
}

export interface NormalizedEducation {
  id?: string
  degree: string
  institution: string
  start_year?: number | null
  end_year?: number | null
  grade?: string
}

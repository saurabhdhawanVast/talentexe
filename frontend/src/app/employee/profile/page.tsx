'use client'

import { Suspense, useEffect, useState, useCallback, useRef } from 'react'
import { toast } from 'sonner'
import { createClient } from '@/lib/supabase'
import { useSearchParams, useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Tabs, TabsContent } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { ProfileStatusBadge } from '@/components/profile/ProfileStatusBadge'
import { LanguagesEditor } from '@/components/profile/LanguagesEditor'
import { ResumeUpload } from '@/components/profile/ResumeUpload'
import {
  Pencil, Save, X, Loader2, FileText, Link2,
  Plus, Trash2, Star,
} from 'lucide-react'
import { format } from 'date-fns'
import type {
  Profile, ProfileStatus, Language,
  EmployeeSkill, EmployeeExperience, NormalizedProject,
  NormalizedCertification, NormalizedEducation,
} from '@/types'

export const dynamic = 'force-dynamic'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

// ─── Helpers ─────────────────────────────────────────────────────────────────

interface RawUser {
  id?: string; email?: string; full_name?: string; phone?: string; designation?: string
  department?: string; location?: string; experience_years?: string | number | null
  avatar_url?: string | null; profile_status?: string; created_at?: string; updated_at?: string
}
interface RawEmployee {
  summary?: string; languages?: Language[]; linkedin_url?: string; github_url?: string; portfolio_url?: string
}

function normalizeProfile(apiData: { user: RawUser; employee: RawEmployee | null }): Profile {
  const { user, employee } = apiData
  return {
    id: user.id ?? '',
    user_id: user.id ?? '',
    full_name: user.full_name ?? '',
    email: user.email ?? '',
    phone: user.phone ?? '',
    designation: user.designation ?? '',
    department: user.department ?? '',
    location: user.location ?? '',
    experience_years: user.experience_years != null ? parseFloat(String(user.experience_years)) : null,
    avatar_url: user.avatar_url ?? null,
    status: (user.profile_status ?? 'incomplete') as ProfileStatus,
    summary: employee?.summary ?? '',
    skills: [],
    experience: [],
    projects: [],
    education: [],
    certifications: [],
    languages: employee?.languages ?? [],
    links: {
      linkedin: employee?.linkedin_url ?? '',
      github: employee?.github_url ?? '',
      portfolio: employee?.portfolio_url ?? '',
    },
    resume_file_name: null,
    resume_uploaded_at: null,
    created_at: user.created_at ?? '',
    updated_at: user.updated_at ?? '',
  }
}

function buildOverviewPatchBody(draft: Profile) {
  return {
    user: {
      full_name: draft.full_name,
      phone: draft.phone,
      designation: draft.designation,
      department: draft.department,
      experience_years: draft.experience_years,
      location: draft.location,
    },
    employee: {
      summary: draft.summary,
      languages: draft.languages,
      linkedin_url: draft.links?.linkedin ?? '',
      github_url: draft.links?.github ?? '',
      portfolio_url: draft.links?.portfolio ?? '',
    },
  }
}

function formatDateSafe(d: string | null | undefined): string {
  if (!d) return 'Present'
  try { return format(new Date(d), 'MMM yyyy') } catch { return d }
}

const proficiencyColors: Record<EmployeeSkill['proficiency_level'], string> = {
  Beginner: 'bg-gray-100 text-gray-700',
  Intermediate: 'bg-blue-100 text-blue-700',
  Expert: 'bg-green-100 text-green-700',
}

// ─── Main content component ───────────────────────────────────────────────────

function EmployeeProfilePageContent() {
  const supabase = createClient()
  const searchParams = useSearchParams()
  const router = useRouter()

  const activeTab = searchParams.get('tab') ?? 'dashboard'

  // ── Core profile state ──
  const [profile, setProfile] = useState<Profile | null>(null)
  const [draft, setDraft] = useState<Profile | null>(null)
  const [profileId, setProfileId] = useState<string | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [hrComment, setHrComment] = useState<string | null>(null)

  // ── Resume / LinkedIn ──
  const [resumeFileName, setResumeFileName] = useState<string | null>(null)
  const [resumeUploadedAt, setResumeUploadedAt] = useState<string | null>(null)
  const [linkedinUrl, setLinkedinUrl] = useState('')
  const [isImportingLinkedin, setIsImportingLinkedin] = useState(false)
  // ── Normalized section state ──
  const [skills, setSkills] = useState<EmployeeSkill[]>([])
  const [experiences, setExperiences] = useState<EmployeeExperience[]>([])
  const [projects, setProjects] = useState<NormalizedProject[]>([])
  const [certifications, setCertifications] = useState<NormalizedCertification[]>([])
  const [education, setEducation] = useState<NormalizedEducation[]>([])

  // ── Section loading states ──
  const [skillsLoading, setSkillsLoading] = useState(false)
  const [experiencesLoading, setExperiencesLoading] = useState(false)
  const [projectsLoading, setProjectsLoading] = useState(false)
  const [certsLoading, setCertsLoading] = useState(false)
  const [educationLoading, setEducationLoading] = useState(false)

  // ── Mounted guards per tab ──
  const skillsFetched = useRef(false)
  const experiencesFetched = useRef(false)
  const projectsFetched = useRef(false)
  const certsFetched = useRef(false)
  const educationFetched = useRef(false)

  // ── Inline add-form state ──
  const [showAddSkill, setShowAddSkill] = useState(false)
  const [newSkill, setNewSkill] = useState({ skill_name: '', proficiency_level: 'Intermediate' as EmployeeSkill['proficiency_level'], years_of_experience: 1, is_primary: false })
  const [addingSkill, setAddingSkill] = useState(false)

  const [showAddExp, setShowAddExp] = useState(false)
  const [newExp, setNewExp] = useState<Omit<EmployeeExperience, 'id'>>({ company_name: '', designation: '', employment_type: '', start_date: '', end_date: null, is_current: false, location: '', description: '' })
  const [addingExp, setAddingExp] = useState(false)

  const [showAddProj, setShowAddProj] = useState(false)
  const [newProj, setNewProj] = useState<Omit<NormalizedProject, 'id' | 'skills'> & { skill_names_raw: string }>({ name: '', client_name: '', description: '', role: '', team_size: null, start_date: null, end_date: null, is_current: false, skill_names_raw: '' })
  const [addingProj, setAddingProj] = useState(false)

  const [showAddCert, setShowAddCert] = useState(false)
  const [newCert, setNewCert] = useState<Omit<NormalizedCertification, 'id'>>({ name: '', issuer: '', issue_date: null, expiry_date: null, credential_url: '' })
  const [addingCert, setAddingCert] = useState(false)

  const [showAddEdu, setShowAddEdu] = useState(false)
  const [newEdu, setNewEdu] = useState<Omit<NormalizedEducation, 'id'>>({ degree: '', institution: '', start_year: null, end_year: null, grade: '' })
  const [addingEdu, setAddingEdu] = useState(false)

  // ─── Auth helper ──────────────────────────────────────────────────────────
  const getToken = useCallback(async () => {
    const { data } = await supabase.auth.getSession()
    return data.session?.access_token ?? ''
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // ─── Resume info ──────────────────────────────────────────────────────────
  const fetchResumeInfo = useCallback(async (uid: string, token: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/profiles/${uid}/resume/`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const body = await res.json()
        setResumeFileName(body.data?.original_name ?? null)
        setResumeUploadedAt(new Date().toISOString())
      } else {
        setResumeFileName(null)
        setResumeUploadedAt(null)
      }
    } catch {
      setResumeFileName(null)
      setResumeUploadedAt(null)
    }
  }, [])

  // ─── Profile fetch ────────────────────────────────────────────────────────
  const fetchProfile = useCallback(async () => {
    setIsLoading(true)
    try {
      const token = await getToken()
      if (!token) return

      const { data: sessionData } = await supabase.auth.getSession()
      const uid: string = sessionData.session?.user?.id ?? ''
      if (!uid) return

      const res = await fetch(`${API_BASE}/api/v1/profiles/${uid}/`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error()
      const body = await res.json()

      const normalized = normalizeProfile(body.data)
      setProfile(normalized)
      setDraft(normalized)
      setProfileId(uid)
      setLinkedinUrl(normalized.links?.linkedin ?? '')
      await fetchResumeInfo(uid, token)

      // Fetch latest HR review to show HR comment to employee
      try {
        const reviewRes = await fetch(`${API_BASE}/api/v1/reviews/me/`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (reviewRes.ok) {
          const reviewBody = await reviewRes.json()
          setHrComment(reviewBody.data?.hr_comment ?? null)
        }
      } catch {
        // Non-critical; silently ignore
      }
    } catch {
      toast.error('Failed to load your profile.')
    } finally {
      setIsLoading(false)
    }
  }, [getToken, fetchResumeInfo])

  useEffect(() => {
    fetchProfile()
  }, [fetchProfile])

  // ─── Section fetch helpers ────────────────────────────────────────────────
  const fetchSkills = useCallback(async (uid: string) => {
    setSkillsLoading(true)
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/api/v1/profiles/${uid}/skills/`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error()
      const body = await res.json()
      setSkills(body.data ?? [])
    } catch {
      toast.error('Failed to load skills.')
    } finally {
      setSkillsLoading(false)
    }
  }, [getToken])

  const fetchExperiences = useCallback(async (uid: string) => {
    setExperiencesLoading(true)
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/api/v1/profiles/${uid}/experiences/`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error()
      const body = await res.json()
      setExperiences(body.data ?? [])
    } catch {
      toast.error('Failed to load experience.')
    } finally {
      setExperiencesLoading(false)
    }
  }, [getToken])

  const fetchProjects = useCallback(async (uid: string) => {
    setProjectsLoading(true)
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/api/v1/profiles/${uid}/projects/`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error()
      const body = await res.json()
      setProjects(body.data ?? [])
    } catch {
      toast.error('Failed to load projects.')
    } finally {
      setProjectsLoading(false)
    }
  }, [getToken])

  const fetchCertifications = useCallback(async (uid: string) => {
    setCertsLoading(true)
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/api/v1/profiles/${uid}/certifications/`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error()
      const body = await res.json()
      setCertifications(body.data ?? [])
    } catch {
      toast.error('Failed to load certifications.')
    } finally {
      setCertsLoading(false)
    }
  }, [getToken])

  const fetchEducation = useCallback(async (uid: string) => {
    setEducationLoading(true)
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/api/v1/profiles/${uid}/education/`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error()
      const body = await res.json()
      setEducation(body.data ?? [])
    } catch {
      toast.error('Failed to load education.')
    } finally {
      setEducationLoading(false)
    }
  }, [getToken])

  // ─── Tab-driven lazy fetch ────────────────────────────────────────────────
  useEffect(() => {
    if (!profileId) return
    if (activeTab === 'dashboard') {
      if (!skillsFetched.current) { skillsFetched.current = true; fetchSkills(profileId) }
      if (!projectsFetched.current) { projectsFetched.current = true; fetchProjects(profileId) }
    }
    if (activeTab === 'skills' && !skillsFetched.current) { skillsFetched.current = true; fetchSkills(profileId) }
    if (activeTab === 'ai-suggestions' && !skillsFetched.current) { skillsFetched.current = true; fetchSkills(profileId) }
    if (activeTab === 'experience' && !experiencesFetched.current) { experiencesFetched.current = true; fetchExperiences(profileId) }
    if (activeTab === 'projects' && !projectsFetched.current) { projectsFetched.current = true; fetchProjects(profileId) }
    if (activeTab === 'certifications' && !certsFetched.current) { certsFetched.current = true; fetchCertifications(profileId) }
    if (activeTab === 'education' && !educationFetched.current) { educationFetched.current = true; fetchEducation(profileId) }
  }, [activeTab, profileId, fetchSkills, fetchExperiences, fetchProjects, fetchCertifications, fetchEducation])

  // ─── Overview handlers ────────────────────────────────────────────────────
  const handleEditToggle = () => {
    if (isEditing) setDraft(profile)
    setIsEditing((v) => !v)
  }

  const handleSave = async () => {
    if (!draft || !profileId) return
    if (draft.experience_years === null || draft.experience_years === undefined) {
      toast.error('Experience (Years) is required.')
      return
    }
    setIsSaving(true)
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/api/v1/profiles/${profileId}/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(buildOverviewPatchBody(draft)),
      })
      if (!res.ok) throw new Error()
      setIsEditing(false)
      toast.success('Profile saved successfully.')
      await fetchProfile()
    } catch {
      toast.error('Failed to save profile.')
    } finally {
      setIsSaving(false)
    }
  }

  const handleLinkedinImport = async () => {
    if (!linkedinUrl.trim() || !draft || !profileId) return
    setIsImportingLinkedin(true)
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/api/v1/ai/extract-linkedin/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ linkedin_url: linkedinUrl.trim() }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body?.error ?? 'Failed to import LinkedIn profile.')
      toast.success('LinkedIn profile imported! Your data has been populated.')
      await fetchProfile()
      skillsFetched.current = false
      experiencesFetched.current = false
      projectsFetched.current = false
      certsFetched.current = false
      educationFetched.current = false
      await Promise.all([
        fetchSkills(profileId),
        fetchExperiences(profileId),
        fetchProjects(profileId),
        fetchCertifications(profileId),
        fetchEducation(profileId),
      ])
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to import LinkedIn profile.')
    } finally {
      setIsImportingLinkedin(false)
    }
  }

  const updateDraft = (field: keyof Profile, value: unknown) =>
    setDraft((prev) => (prev ? { ...prev, [field]: value } : prev))

  // ─── Skills CRUD ──────────────────────────────────────────────────────────
  const handleAddSkill = async () => {
    if (!profileId || !newSkill.skill_name.trim()) return
    setAddingSkill(true)
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/api/v1/profiles/${profileId}/skills/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          skill_name: newSkill.skill_name.trim(),
          proficiency_level: newSkill.proficiency_level,
          years_of_experience: newSkill.years_of_experience,
          is_primary: newSkill.is_primary,
        }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body?.error ?? 'Failed to add skill.')
      setSkills((prev) => [...prev, body.data])
      setNewSkill({ skill_name: '', proficiency_level: 'Intermediate', years_of_experience: 1, is_primary: false })
      setShowAddSkill(false)
      toast.success('Skill added.')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to add skill.')
    } finally {
      setAddingSkill(false)
    }
  }

  const handleDeleteSkill = async (skillId: string) => {
    if (!profileId) return
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/api/v1/profiles/${profileId}/skills/${skillId}/`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body?.error ?? 'Failed to remove skill.')
      }
      setSkills((prev) => prev.filter((s) => s.id !== skillId))
      toast.success('Skill removed.')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to remove skill.')
    }
  }

  // ─── Experience CRUD ──────────────────────────────────────────────────────
  const handleAddExperience = async () => {
    if (!profileId || !newExp.company_name.trim() || !newExp.designation.trim() || !newExp.start_date) return
    setAddingExp(true)
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/api/v1/profiles/${profileId}/experiences/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          ...newExp,
          end_date: newExp.is_current ? null : (newExp.end_date || null),
          employment_type: newExp.employment_type || undefined,
          location: newExp.location || undefined,
          description: newExp.description || undefined,
        }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body?.error ?? 'Failed to add experience.')
      setExperiences((prev) => [...prev, body.data])
      setNewExp({ company_name: '', designation: '', employment_type: '', start_date: '', end_date: null, is_current: false, location: '', description: '' })
      setShowAddExp(false)
      toast.success('Experience added.')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to add experience.')
    } finally {
      setAddingExp(false)
    }
  }

  const handleDeleteExperience = async (expId: string) => {
    if (!profileId) return
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/api/v1/profiles/${profileId}/experiences/${expId}/`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body?.error ?? 'Failed to remove experience.')
      }
      setExperiences((prev) => prev.filter((e) => e.id !== expId))
      toast.success('Experience removed.')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to remove experience.')
    }
  }

  // ─── Projects CRUD ────────────────────────────────────────────────────────
  const handleAddProject = async () => {
    if (!profileId || !newProj.name.trim()) return
    setAddingProj(true)
    try {
      const token = await getToken()
      const skillNames = newProj.skill_names_raw
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
      const res = await fetch(`${API_BASE}/api/v1/profiles/${profileId}/projects/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          name: newProj.name.trim(),
          client_name: newProj.client_name || undefined,
          description: newProj.description || undefined,
          role: newProj.role || undefined,
          team_size: newProj.team_size ?? undefined,
          start_date: newProj.start_date || undefined,
          end_date: newProj.is_current ? null : (newProj.end_date || undefined),
          is_current: newProj.is_current,
          skill_names: skillNames.length > 0 ? skillNames : undefined,
        }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body?.error ?? 'Failed to add project.')
      setProjects((prev) => [...prev, body.data])
      setNewProj({ name: '', client_name: '', description: '', role: '', team_size: null, start_date: null, end_date: null, is_current: false, skill_names_raw: '' })
      setShowAddProj(false)
      toast.success('Project added.')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to add project.')
    } finally {
      setAddingProj(false)
    }
  }

  const handleDeleteProject = async (projId: string) => {
    if (!profileId) return
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/api/v1/profiles/${profileId}/projects/${projId}/`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body?.error ?? 'Failed to remove project.')
      }
      setProjects((prev) => prev.filter((p) => p.id !== projId))
      toast.success('Project removed.')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to remove project.')
    }
  }

  // ─── Certifications CRUD ──────────────────────────────────────────────────
  const handleAddCertification = async () => {
    if (!profileId || !newCert.name.trim()) return
    setAddingCert(true)
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/api/v1/profiles/${profileId}/certifications/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          name: newCert.name.trim(),
          issuer: newCert.issuer || undefined,
          issue_date: newCert.issue_date || undefined,
          expiry_date: newCert.expiry_date || undefined,
          credential_url: newCert.credential_url || undefined,
        }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body?.error ?? 'Failed to add certification.')
      setCertifications((prev) => [...prev, body.data])
      setNewCert({ name: '', issuer: '', issue_date: null, expiry_date: null, credential_url: '' })
      setShowAddCert(false)
      toast.success('Certification added.')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to add certification.')
    } finally {
      setAddingCert(false)
    }
  }

  const handleDeleteCertification = async (certId: string) => {
    if (!profileId) return
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/api/v1/profiles/${profileId}/certifications/${certId}/`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body?.error ?? 'Failed to remove certification.')
      }
      setCertifications((prev) => prev.filter((c) => c.id !== certId))
      toast.success('Certification removed.')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to remove certification.')
    }
  }

  // ─── Education CRUD ───────────────────────────────────────────────────────
  const handleAddEducation = async () => {
    if (!profileId || !newEdu.degree.trim() || !newEdu.institution.trim()) return
    setAddingEdu(true)
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/api/v1/profiles/${profileId}/education/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          degree: newEdu.degree.trim(),
          institution: newEdu.institution.trim(),
          start_year: newEdu.start_year ?? undefined,
          end_year: newEdu.end_year ?? undefined,
          grade: newEdu.grade?.trim() ?? '',
        }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body?.error ?? 'Failed to add education.')
      setEducation((prev) => [...prev, body.data])
      setNewEdu({ degree: '', institution: '', start_year: null, end_year: null, grade: '' })
      setShowAddEdu(false)
      toast.success('Education added.')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to add education.')
    } finally {
      setAddingEdu(false)
    }
  }

  const handleDeleteEducation = async (eduId: string) => {
    if (!profileId) return
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/api/v1/profiles/${profileId}/education/${eduId}/`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body?.error ?? 'Failed to remove education.')
      }
      setEducation((prev) => prev.filter((e) => e.id !== eduId))
      toast.success('Education removed.')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to remove education.')
    }
  }



  const initials = profile?.full_name
    ? profile.full_name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)
    : '?'

  // ─── Loading / error states ───────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    )
  }

  if (!profile || !draft) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3">
        <p className="text-gray-500">Could not load your profile. Please try again.</p>
        <Button onClick={fetchProfile} className="bg-indigo-600 hover:bg-indigo-700">Retry</Button>
      </div>
    )
  }

  // ─── Shared import card JSX (used in resume tab) ──────────────────────────
  const importCard = (
    <div className="flex flex-col sm:flex-row items-stretch gap-0">
      {/* Resume Upload */}
      <div className="flex-1 rounded-xl border border-gray-200 bg-gray-50 p-5">
        <div className="flex items-start gap-3 mb-4">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-indigo-100">
            <FileText className="h-5 w-5 text-indigo-600" />
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-900">Upload Resume</p>
            <p className="text-xs text-gray-500 mt-0.5">Upload your latest resume (PDF or DOCX)</p>
          </div>
        </div>
        <ResumeUpload
          profileId={profileId ?? ''}
          fileName={resumeFileName}
          uploadedAt={resumeUploadedAt}
          onUploadSuccess={() => {
            if (!profileId) return
            getToken().then((t) => fetchResumeInfo(profileId, t))
            skillsFetched.current = false
            experiencesFetched.current = false
            projectsFetched.current = false
            certsFetched.current = false
            educationFetched.current = false
            fetchSkills(profileId)
            fetchProjects(profileId)
            fetchExperiences(profileId)
            fetchCertifications(profileId)
            fetchEducation(profileId)
          }}
        />
      </div>

      {/* OR divider — desktop */}
      <div className="hidden sm:flex flex-col items-center justify-center w-12 shrink-0 py-4">
        <div className="flex-1 w-px bg-gray-200" />
        <span className="shrink-0 my-2 text-xs font-medium text-gray-400 bg-white border border-gray-200 rounded-full px-2 py-1">OR</span>
        <div className="flex-1 w-px bg-gray-200" />
      </div>
      {/* OR divider — mobile */}
      <div className="flex sm:hidden items-center gap-3 py-3">
        <div className="flex-1 h-px bg-gray-200" />
        <span className="shrink-0 text-xs font-medium text-gray-400 bg-white border border-gray-200 rounded-full px-2 py-1">OR</span>
        <div className="flex-1 h-px bg-gray-200" />
      </div>

      {/* LinkedIn Import */}
      <div className="flex-1 rounded-xl border border-gray-200 bg-gray-50 p-5">
        <div className="flex items-start gap-3 mb-4">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#0A66C2]">
            <svg viewBox="0 0 24 24" fill="white" className="h-5 w-5">
              <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-900">Import from LinkedIn</p>
            <p className="text-xs text-gray-500 mt-0.5">Paste your LinkedIn profile URL to auto-import data</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Input
            placeholder="https://www.linkedin.com/in/yourprofile"
            value={linkedinUrl}
            onChange={(e) => setLinkedinUrl(e.target.value)}
            className="flex-1 text-sm"
          />
          <Button
            variant="outline"
            size="sm"
            className="shrink-0 gap-1 border-indigo-300 text-indigo-700 hover:bg-indigo-50"
            disabled={!linkedinUrl.trim() || isImportingLinkedin}
            onClick={handleLinkedinImport}
          >
            {isImportingLinkedin ? (
              <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Importing...</>
            ) : (
              <><Link2 className="h-3.5 w-3.5" /> Import</>
            )}
          </Button>
        </div>
        {profile.links?.linkedin && (
          <p className="mt-2 text-xs text-gray-500 truncate">
            Saved:{' '}
            <a href={profile.links.linkedin} target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:underline">
              {profile.links.linkedin}
            </a>
          </p>
        )}
      </div>
    </div>
  )

  return (
    <section aria-labelledby="my-profile-heading" className="w-full space-y-5">
      {/* Top bar */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 id="my-profile-heading" className="text-2xl font-semibold text-gray-900">My Profile</h1>
          <p className="mt-1 text-sm text-gray-500">Keep your profile up to date for HR review.</p>
        </div>
      </div>

      {/* ── Header card ─────────────────────────────────────────────────── */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-4">
            <Avatar className="h-16 w-16 shrink-0">
              {profile.avatar_url && <AvatarImage src={profile.avatar_url} alt={profile.full_name} />}
              <AvatarFallback className="bg-indigo-100 text-indigo-700 text-xl font-bold">
                {initials}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="text-base font-semibold text-gray-900 truncate">{profile.full_name || '—'}</p>
              {profile.designation && <p className="text-sm text-indigo-600 mt-0.5">{profile.designation}</p>}
              <p className="text-xs text-gray-500 mt-0.5">
                {[profile.department, profile.location].filter(Boolean).join(' · ') || '—'}
              </p>
              {profile.experience_years != null && profile.experience_years > 0 && (
                <p className="text-xs text-gray-500">{profile.experience_years} yrs experience</p>
              )}
            </div>
            <div className="shrink-0">
              <ProfileStatusBadge status={profile.status} size="lg" />
            </div>
          </div>
          {profile.status === 'rejected' && (
            <div className="mt-3 rounded-lg bg-red-50 border border-red-200 px-3 py-2">
              <p className="text-xs font-semibold text-red-700">HR Feedback</p>
              <p className="text-sm text-red-600 mt-0.5">
                {hrComment || 'Your profile was rejected. Please update and resubmit.'}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Tabbed sections (sidebar-driven) ────────────────────────────── */}
      <Tabs value={activeTab}>
        {/* NO TabsList — sidebar handles navigation */}

        {/* ── Dashboard tab ───────────────────────────────────────────── */}
        <TabsContent value="dashboard" className="space-y-6">
          {/* Welcome header */}
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h2 className="text-3xl font-bold text-slate-800">
                Welcome Back, {profile.full_name?.split(' ')[0]}
              </h2>
              <p className="text-slate-500 mt-1">
                {[profile.designation, profile.location].filter(Boolean).join(' • ')}
              </p>
            </div>
            <div className="flex gap-3">
              <Button variant="outline" onClick={() => router.push('/employee/profile?tab=resume')}>
                Upload Resume
              </Button>
            </div>
          </div>

          {/* Stats cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <Card className="rounded-3xl shadow-sm">
              <CardContent className="pt-6">
                <p className="text-slate-500 text-sm">Resume Status</p>
                {resumeFileName ? (
                  <h3 className="text-xl font-bold mt-2 text-green-600">Processed Successfully</h3>
                ) : (
                  <h3 className="text-xl font-bold mt-2 text-amber-500">No Resume Yet</h3>
                )}
                <p className="text-slate-500 mt-1 text-sm">
                  {resumeFileName ? `File: ${resumeFileName}` : 'Upload your resume to get started.'}
                </p>
              </CardContent>
            </Card>

            <Card className="rounded-3xl shadow-sm">
              <CardContent className="pt-6">
                <p className="text-slate-500 text-sm">HR Review</p>
                <h3 className={`text-xl font-bold mt-2 ${
                  profile.status === 'approved' ? 'text-green-600' :
                  profile.status === 'rejected' ? 'text-red-600' :
                  profile.status === 'submitted' ? 'text-amber-500' : 'text-slate-500'
                }`}>
                  {profile.status === 'approved' ? 'Approved' :
                   profile.status === 'rejected' ? 'Rejected' :
                   profile.status === 'submitted' ? 'Pending Approval' : 'Not Submitted'}
                </h3>
                <p className="text-slate-500 mt-1 text-sm">
                  {profile.status === 'submitted' ? 'Under review by HR team.' :
                   profile.status === 'approved' ? 'Your profile is live.' :
                   profile.status === 'rejected' ? (hrComment || 'Please update and resubmit.') :
                   'Complete your profile and submit.'}
                </p>
              </CardContent>
            </Card>

            <Card className="rounded-3xl shadow-sm">
              <CardContent className="pt-6">
                <p className="text-slate-500 text-sm">AI Suggestions</p>
                <h3 className="text-xl font-bold mt-2 text-purple-600">
                  {skills.filter(s => s.source !== 'manual').length} Skills
                </h3>
                <p className="text-slate-500 mt-1 text-sm">AI-extracted from your profile data.</p>
              </CardContent>
            </Card>
          </div>

          {/* Quick Skills preview */}
          {skills.length > 0 && (
            <Card className="rounded-3xl shadow-sm">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-bold text-slate-800">Top Skills</h3>
                  <Button size="sm" variant="outline" onClick={() => router.push('/employee/profile?tab=skills')}>
                    View All
                  </Button>
                </div>
                <div className="space-y-2">
                  {skills.slice(0, 4).map(skill => (
                    <div key={skill.id} className="flex items-center justify-between rounded-xl border border-slate-200 p-3">
                      <div>
                        <p className="font-semibold text-slate-800 text-sm">{skill.name}</p>
                        <p className="text-xs text-slate-500">{skill.proficiency_level}</p>
                      </div>
                      {skill.years_of_experience != null && (
                        <span className="text-sm font-medium text-slate-600">
                          {skill.years_of_experience} yr{skill.years_of_experience !== 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Quick Projects preview */}
          {projects.length > 0 && (
            <Card className="rounded-3xl shadow-sm">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-bold text-slate-800">Recent Projects</h3>
                  <Button size="sm" variant="outline" onClick={() => router.push('/employee/profile?tab=projects')}>
                    View All
                  </Button>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {projects.slice(0, 2).map(proj => (
                    <div key={proj.id ?? proj.name} className="border border-slate-200 rounded-2xl p-4">
                      <h4 className="font-semibold text-slate-800">{proj.name}</h4>
                      {proj.role && <p className="text-sm text-slate-500 mt-1">{proj.role}</p>}
                      {proj.skills && proj.skills.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-3">
                          {proj.skills.slice(0, 4).map(s => (
                            <span key={s.skill_id} className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full text-xs">{s.name}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

        </TabsContent>

        {/* ── Overview tab ────────────────────────────────────────────── */}
        <TabsContent value="overview" className="space-y-4 mt-4">
          {/* Edit / Save buttons for Overview only */}
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <p className="text-xs text-gray-400">
              Fields marked <span className="text-red-500 font-medium">*</span> are required for profile completion.
            </p>
            <div className="flex gap-2">
              {isEditing ? (
                <>
                  <Button variant="outline" onClick={handleEditToggle} disabled={isSaving} className="gap-1">
                    <X className="h-4 w-4" /> Cancel
                  </Button>
                  <Button className="bg-indigo-600 hover:bg-indigo-700 gap-1" onClick={handleSave} disabled={isSaving}>
                    {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                    Save
                  </Button>
                </>
              ) : (
                <Button className="bg-indigo-600 hover:bg-indigo-700 gap-1" onClick={handleEditToggle}>
                  <Pencil className="h-4 w-4" /> Edit
                </Button>
              )}
            </div>
          </div>

          {/* Basic Info */}
          <Card>
            <CardHeader className="pb-3"><CardTitle className="text-base">Basic Info</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {(['designation', 'department', 'location'] as const).map((field) => (
                  <div key={field} className="space-y-1">
                    <Label className="text-xs text-gray-500 capitalize">
                      {field} <span className="text-red-500">*</span>
                    </Label>
                    {isEditing ? (
                      <Input
                        value={(draft as unknown as Record<string, string>)[field] ?? ''}
                        onChange={(e) => updateDraft(field, e.target.value)}
                        placeholder={field}
                      />
                    ) : (
                      <p className="text-sm text-gray-800">
                        {(profile as unknown as Record<string, string>)[field] || <span className="text-gray-400">—</span>}
                      </p>
                    )}
                  </div>
                ))}
                <div className="space-y-1">
                  <Label className="text-xs text-gray-500">
                    Experience (Years) <span className="text-red-500">*</span>
                  </Label>
                  {isEditing ? (
                    <>
                      <Input
                        type="number"
                        min={0}
                        value={draft.experience_years ?? ''}
                        onChange={(e) =>
                          updateDraft(
                            'experience_years',
                            e.target.value === '' ? null : Number(e.target.value)
                          )
                        }
                        placeholder="e.g. 3"
                      />
                      {draft.experience_years === null && (
                        <p className="text-xs text-red-600">Experience is required</p>
                      )}
                    </>
                  ) : (
                    <p className="text-sm text-gray-800">
                      {profile.experience_years != null
                        ? String(profile.experience_years)
                        : <span className="text-gray-400">—</span>}
                    </p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Contact */}
          <Card>
            <CardHeader className="pb-3"><CardTitle className="text-base">Contact</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <Label className="text-xs text-gray-500">Email</Label>
                  <p className="text-sm text-gray-800">{profile.email}</p>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-gray-500">
                    Phone <span className="text-red-500">*</span>
                  </Label>
                  {isEditing ? (
                    <Input value={draft.phone ?? ''} onChange={(e) => updateDraft('phone', e.target.value)} placeholder="+1-555-0100" />
                  ) : (
                    <p className="text-sm text-gray-800">{profile.phone || <span className="text-gray-400">—</span>}</p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Summary */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">
                Summary <span className="text-red-500 text-sm font-normal">*</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isEditing ? (
                <Textarea value={draft.summary ?? ''} onChange={(e) => updateDraft('summary', e.target.value)} placeholder="Brief professional summary..." rows={4} />
              ) : (
                <p className="text-sm text-gray-700 whitespace-pre-wrap">
                  {profile.summary || <span className="text-gray-400">No summary added yet.</span>}
                </p>
              )}
            </CardContent>
          </Card>

          {/* Languages */}
          <Card>
            <CardHeader className="pb-3"><CardTitle className="text-base">Languages</CardTitle></CardHeader>
            <CardContent>
              <LanguagesEditor languages={draft.languages ?? []} isEditing={isEditing} onChange={(l) => updateDraft('languages', l)} />
            </CardContent>
          </Card>

          {/* Links */}
          <Card>
            <CardHeader className="pb-3"><CardTitle className="text-base">Links</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {(['github', 'portfolio'] as const).map((key) => (
                  <div key={key} className="space-y-1">
                    <Label className="text-xs text-gray-500 capitalize">
                      {key}
                    </Label>
                    {isEditing ? (
                      <Input
                        type="url"
                        value={draft.links?.[key] ?? ''}
                        onChange={(e) => updateDraft('links', { ...draft.links, [key]: e.target.value })}
                        placeholder={`https://${key}.com/...`}
                      />
                    ) : (
                      <p className="text-sm">
                        {draft.links?.[key] ? (
                          <a href={draft.links[key]} target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:underline truncate block">
                            {draft.links[key]}
                          </a>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Resume & LinkedIn tab ────────────────────────────────────── */}
        <TabsContent value="resume" className="space-y-5">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Resume &amp; LinkedIn</h2>
            <p className="text-sm text-gray-500 mt-1">Upload your resume or import your LinkedIn profile to auto-populate your data.</p>
          </div>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Import Profile Data</CardTitle>
            </CardHeader>
            <CardContent>
              {importCard}
              {resumeFileName && resumeUploadedAt && (
                <div className="mt-4 flex items-center gap-2 rounded-lg bg-green-50 border border-green-200 px-4 py-2.5">
                  <svg className="h-4 w-4 text-green-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="text-sm font-medium text-green-700">
                    Resume uploaded on {format(new Date(resumeUploadedAt), 'dd MMM yyyy')}
                  </span>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Skills tab ──────────────────────────────────────────────── */}
        <TabsContent value="skills" className="mt-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">
                  Skills <span className="text-red-500 text-sm font-normal">*</span>
                </CardTitle>
                <Button
                  size="sm"
                  className="bg-indigo-600 hover:bg-indigo-700 gap-1"
                  onClick={() => setShowAddSkill((v) => !v)}
                >
                  <Plus className="h-3.5 w-3.5" />
                  Add Skill
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Add skill form */}
              {showAddSkill && (
                <div className="rounded-lg border border-dashed border-indigo-300 bg-indigo-50/30 p-4 space-y-3">
                  <p className="text-sm font-medium text-gray-700">New Skill</p>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="space-y-1 sm:col-span-1">
                      <Label className="text-xs">Skill Name <span className="text-red-500">*</span></Label>
                      <Input
                        placeholder="e.g. TypeScript"
                        value={newSkill.skill_name}
                        onChange={(e) => setNewSkill((p) => ({ ...p, skill_name: e.target.value }))}
                        onKeyDown={(e) => e.key === 'Enter' && handleAddSkill()}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Proficiency <span className="text-red-500">*</span></Label>
                      <Select
                        value={newSkill.proficiency_level}
                        onValueChange={(v) => setNewSkill((p) => ({ ...p, proficiency_level: v as EmployeeSkill['proficiency_level'] }))}
                      >
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Beginner">Beginner</SelectItem>
                          <SelectItem value="Intermediate">Intermediate</SelectItem>
                          <SelectItem value="Expert">Expert</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Years</Label>
                      <Input
                        type="number"
                        min={0}
                        max={50}
                        value={newSkill.years_of_experience}
                        onChange={(e) => setNewSkill((p) => ({ ...p, years_of_experience: Number(e.target.value) }))}
                      />
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={newSkill.is_primary}
                        onChange={(e) => setNewSkill((p) => ({ ...p, is_primary: e.target.checked }))}
                        className="rounded border-gray-300 text-indigo-600"
                      />
                      Mark as primary skill
                    </label>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      className="bg-indigo-600 hover:bg-indigo-700 gap-1"
                      onClick={handleAddSkill}
                      disabled={!newSkill.skill_name.trim() || addingSkill}
                    >
                      {addingSkill ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
                      Add
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => setShowAddSkill(false)}>Cancel</Button>
                  </div>
                </div>
              )}

              {/* Skills list */}
              {skillsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-indigo-600" />
                </div>
              ) : skills.length === 0 ? (
                <p className="text-sm text-gray-400">No skills added yet. Click &quot;Add Skill&quot; to get started.</p>
              ) : (
                <div className="grid grid-cols-3 gap-2">
                  {skills.map((skill) => (
                    <div
                      key={skill.id}
                      className="relative flex flex-col gap-1 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 min-w-0"
                    >
                      <button
                        type="button"
                        onClick={() => handleDeleteSkill(skill.id)}
                        aria-label={`Remove ${skill.name}`}
                        className="absolute top-1 right-1 flex h-4 w-4 items-center justify-center rounded-full bg-gray-200 text-gray-500 hover:bg-red-100 hover:text-red-600 text-[10px] leading-none font-bold"
                      >
                        ×
                      </button>
                      <div className="flex items-center gap-1.5 pr-5 min-w-0">
                        <span className="text-sm font-medium text-gray-900 truncate" title={skill.name}>{skill.name}</span>
                        {skill.is_primary && (
                          <Star className="h-3 w-3 text-amber-500 fill-amber-500 shrink-0" aria-label="Primary skill" />
                        )}
                      </div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`self-start rounded-full px-1.5 py-0.5 text-xs font-semibold ${proficiencyColors[skill.proficiency_level]}`}>
                          {skill.proficiency_level}
                        </span>
                        {skill.verified_by_hr && (
                          <span className="text-xs text-green-600 font-medium">Verified</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Experience tab ──────────────────────────────────────────── */}
        <TabsContent value="experience" className="mt-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">Work Experience</CardTitle>
                <Button
                  size="sm"
                  className="bg-indigo-600 hover:bg-indigo-700 gap-1"
                  onClick={() => setShowAddExp((v) => !v)}
                >
                  <Plus className="h-3.5 w-3.5" />
                  Add Experience
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Add experience form */}
              {showAddExp && (
                <div className="rounded-lg border border-dashed border-indigo-300 bg-indigo-50/30 p-4 space-y-3">
                  <p className="text-sm font-medium text-gray-700">New Experience</p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <Label className="text-xs">Company <span className="text-red-500">*</span></Label>
                      <Input
                        placeholder="Acme Corp"
                        value={newExp.company_name}
                        onChange={(e) => setNewExp((p) => ({ ...p, company_name: e.target.value }))}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Designation / Role <span className="text-red-500">*</span></Label>
                      <Input
                        placeholder="Senior Engineer"
                        value={newExp.designation}
                        onChange={(e) => setNewExp((p) => ({ ...p, designation: e.target.value }))}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Employment Type</Label>
                      <Input
                        placeholder="Full-time"
                        value={newExp.employment_type ?? ''}
                        onChange={(e) => setNewExp((p) => ({ ...p, employment_type: e.target.value }))}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Location</Label>
                      <Input
                        placeholder="San Francisco, CA"
                        value={newExp.location ?? ''}
                        onChange={(e) => setNewExp((p) => ({ ...p, location: e.target.value }))}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Start Date <span className="text-red-500">*</span></Label>
                      <Input
                        type="date"
                        value={newExp.start_date}
                        onChange={(e) => setNewExp((p) => ({ ...p, start_date: e.target.value }))}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">End Date</Label>
                      <Input
                        type="date"
                        value={newExp.end_date ?? ''}
                        disabled={newExp.is_current}
                        onChange={(e) => setNewExp((p) => ({ ...p, end_date: e.target.value || null }))}
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={newExp.is_current}
                          onChange={(e) => setNewExp((p) => ({ ...p, is_current: e.target.checked, end_date: e.target.checked ? null : p.end_date }))}
                          className="rounded border-gray-300 text-indigo-600"
                        />
                        Currently working here
                      </label>
                    </div>
                    <div className="space-y-1 sm:col-span-2">
                      <Label className="text-xs">Description</Label>
                      <Textarea
                        placeholder="Key responsibilities and achievements..."
                        rows={3}
                        value={newExp.description ?? ''}
                        onChange={(e) => setNewExp((p) => ({ ...p, description: e.target.value }))}
                      />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      className="bg-indigo-600 hover:bg-indigo-700 gap-1"
                      onClick={handleAddExperience}
                      disabled={!newExp.company_name.trim() || !newExp.designation.trim() || !newExp.start_date || addingExp}
                    >
                      {addingExp ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
                      Add
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => setShowAddExp(false)}>Cancel</Button>
                  </div>
                </div>
              )}

              {/* Experience list */}
              {experiencesLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-indigo-600" />
                </div>
              ) : experiences.length === 0 ? (
                <p className="text-sm text-gray-400">No experience added yet.</p>
              ) : (
                <div className="space-y-3">
                  {experiences.map((exp) => (
                    <div key={exp.id ?? exp.company_name} className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <p className="font-semibold text-gray-900">{exp.designation}</p>
                          <p className="text-sm text-indigo-600">{exp.company_name}</p>
                          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                            <p className="text-xs text-gray-500">
                              {formatDateSafe(exp.start_date)} – {exp.is_current ? 'Present' : formatDateSafe(exp.end_date ?? null)}
                            </p>
                            {exp.employment_type && (
                              <Badge variant="outline" className="text-xs py-0 h-5">{exp.employment_type}</Badge>
                            )}
                            {exp.location && (
                              <span className="text-xs text-gray-400">{exp.location}</span>
                            )}
                          </div>
                          {exp.description && (
                            <p className="mt-2 text-sm text-gray-600 whitespace-pre-wrap">{exp.description}</p>
                          )}
                        </div>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 shrink-0"
                          onClick={() => exp.id && handleDeleteExperience(exp.id)}
                          aria-label="Remove experience"
                        >
                          <Trash2 className="h-3.5 w-3.5 text-red-500" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Projects tab ────────────────────────────────────────────── */}
        <TabsContent value="projects" className="mt-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">Projects</CardTitle>
                <Button
                  size="sm"
                  className="bg-indigo-600 hover:bg-indigo-700 gap-1"
                  onClick={() => setShowAddProj((v) => !v)}
                >
                  <Plus className="h-3.5 w-3.5" />
                  Add Project
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Add project form */}
              {showAddProj && (
                <div className="rounded-lg border border-dashed border-indigo-300 bg-indigo-50/30 p-4 space-y-3">
                  <p className="text-sm font-medium text-gray-700">New Project</p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <Label className="text-xs">Project Name <span className="text-red-500">*</span></Label>
                      <Input
                        placeholder="My Awesome Project"
                        value={newProj.name}
                        onChange={(e) => setNewProj((p) => ({ ...p, name: e.target.value }))}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Client Name</Label>
                      <Input
                        placeholder="Acme Corp"
                        value={newProj.client_name ?? ''}
                        onChange={(e) => setNewProj((p) => ({ ...p, client_name: e.target.value }))}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Your Role</Label>
                      <Input
                        placeholder="Lead Developer"
                        value={newProj.role ?? ''}
                        onChange={(e) => setNewProj((p) => ({ ...p, role: e.target.value }))}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Team Size</Label>
                      <Input
                        type="number"
                        min={1}
                        placeholder="5"
                        value={newProj.team_size ?? ''}
                        onChange={(e) => setNewProj((p) => ({ ...p, team_size: e.target.value ? Number(e.target.value) : null }))}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Start Date</Label>
                      <Input
                        type="date"
                        value={newProj.start_date ?? ''}
                        onChange={(e) => setNewProj((p) => ({ ...p, start_date: e.target.value || null }))}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">End Date</Label>
                      <Input
                        type="date"
                        value={newProj.end_date ?? ''}
                        disabled={newProj.is_current}
                        onChange={(e) => setNewProj((p) => ({ ...p, end_date: e.target.value || null }))}
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={newProj.is_current}
                          onChange={(e) => setNewProj((p) => ({ ...p, is_current: e.target.checked, end_date: e.target.checked ? null : p.end_date }))}
                          className="rounded border-gray-300 text-indigo-600"
                        />
                        Currently active
                      </label>
                    </div>
                    <div className="space-y-1 sm:col-span-2">
                      <Label className="text-xs">Description</Label>
                      <Textarea
                        placeholder="What the project does, your role, and impact..."
                        rows={3}
                        value={newProj.description ?? ''}
                        onChange={(e) => setNewProj((p) => ({ ...p, description: e.target.value }))}
                      />
                    </div>
                    <div className="space-y-1 sm:col-span-2">
                      <Label className="text-xs">Skills (comma-separated)</Label>
                      <Input
                        placeholder="React, TypeScript, Node.js"
                        value={newProj.skill_names_raw}
                        onChange={(e) => setNewProj((p) => ({ ...p, skill_names_raw: e.target.value }))}
                      />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      className="bg-indigo-600 hover:bg-indigo-700 gap-1"
                      onClick={handleAddProject}
                      disabled={!newProj.name.trim() || addingProj}
                    >
                      {addingProj ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
                      Add
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => setShowAddProj(false)}>Cancel</Button>
                  </div>
                </div>
              )}

              {/* Projects list */}
              {projectsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-indigo-600" />
                </div>
              ) : projects.length === 0 ? (
                <p className="text-sm text-gray-400">No projects added yet.</p>
              ) : (
                <div className="space-y-3">
                  {projects.map((proj) => (
                    <div key={proj.id ?? proj.name} className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <p className="font-semibold text-gray-900">{proj.name}</p>
                            {proj.is_current && (
                              <Badge className="text-xs bg-green-100 text-green-700 border-green-200 py-0 h-5">Active</Badge>
                            )}
                          </div>
                          {proj.client_name && (
                            <p className="text-sm text-indigo-600 mt-0.5">{proj.client_name}</p>
                          )}
                          <div className="flex items-center gap-3 mt-0.5 flex-wrap text-xs text-gray-500">
                            {proj.role && <span>{proj.role}</span>}
                            {proj.team_size && <span>Team of {proj.team_size}</span>}
                            {(proj.start_date || proj.end_date) && (
                              <span>
                                {formatDateSafe(proj.start_date)} – {proj.is_current ? 'Present' : formatDateSafe(proj.end_date ?? null)}
                              </span>
                            )}
                          </div>
                          {proj.description && (
                            <p className="mt-2 text-sm text-gray-600">{proj.description}</p>
                          )}
                          {proj.skills && proj.skills.length > 0 && (
                            <div className="mt-2 flex flex-wrap gap-1">
                              {proj.skills.map((s) => (
                                <span key={s.skill_id} className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
                                  {s.name}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 shrink-0"
                          onClick={() => proj.id && handleDeleteProject(proj.id)}
                          aria-label="Remove project"
                        >
                          <Trash2 className="h-3.5 w-3.5 text-red-500" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Certifications tab ──────────────────────────────────────── */}
        <TabsContent value="certifications" className="mt-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">Certifications</CardTitle>
                <Button
                  size="sm"
                  className="bg-indigo-600 hover:bg-indigo-700 gap-1"
                  onClick={() => setShowAddCert((v) => !v)}
                >
                  <Plus className="h-3.5 w-3.5" />
                  Add Certification
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Add cert form */}
              {showAddCert && (
                <div className="rounded-lg border border-dashed border-indigo-300 bg-indigo-50/30 p-4 space-y-3">
                  <p className="text-sm font-medium text-gray-700">New Certification</p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <Label className="text-xs">Certification Name <span className="text-red-500">*</span></Label>
                      <Input
                        placeholder="AWS Certified Developer"
                        value={newCert.name}
                        onChange={(e) => setNewCert((p) => ({ ...p, name: e.target.value }))}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Issuer</Label>
                      <Input
                        placeholder="Amazon Web Services"
                        value={newCert.issuer ?? ''}
                        onChange={(e) => setNewCert((p) => ({ ...p, issuer: e.target.value }))}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Issue Date</Label>
                      <Input
                        type="date"
                        value={newCert.issue_date ?? ''}
                        onChange={(e) => setNewCert((p) => ({ ...p, issue_date: e.target.value || null }))}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Expiry Date (optional)</Label>
                      <Input
                        type="date"
                        value={newCert.expiry_date ?? ''}
                        onChange={(e) => setNewCert((p) => ({ ...p, expiry_date: e.target.value || null }))}
                      />
                    </div>
                    <div className="space-y-1 sm:col-span-2">
                      <Label className="text-xs">Credential URL (optional)</Label>
                      <Input
                        type="url"
                        placeholder="https://credential.url"
                        value={newCert.credential_url ?? ''}
                        onChange={(e) => setNewCert((p) => ({ ...p, credential_url: e.target.value }))}
                      />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      className="bg-indigo-600 hover:bg-indigo-700 gap-1"
                      onClick={handleAddCertification}
                      disabled={!newCert.name.trim() || addingCert}
                    >
                      {addingCert ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
                      Add
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => setShowAddCert(false)}>Cancel</Button>
                  </div>
                </div>
              )}

              {/* Certifications list */}
              {certsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-indigo-600" />
                </div>
              ) : certifications.length === 0 ? (
                <p className="text-sm text-gray-400">No certifications added yet.</p>
              ) : (
                <div className="space-y-3">
                  {certifications.map((cert) => (
                    <div key={cert.id ?? cert.name} className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <p className="font-semibold text-gray-900">{cert.name}</p>
                          {cert.issuer && <p className="text-sm text-gray-600 mt-0.5">{cert.issuer}</p>}
                          <div className="flex items-center gap-3 mt-1 text-xs text-gray-500 flex-wrap">
                            {cert.issue_date && <span>Issued: {formatDateSafe(cert.issue_date)}</span>}
                            {cert.expiry_date && <span>Expires: {formatDateSafe(cert.expiry_date)}</span>}
                            {cert.credential_url && (
                              <a href={cert.credential_url} target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:underline">
                                View Credential
                              </a>
                            )}
                          </div>
                        </div>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 shrink-0"
                          onClick={() => cert.id && handleDeleteCertification(cert.id)}
                          aria-label="Remove certification"
                        >
                          <Trash2 className="h-3.5 w-3.5 text-red-500" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Education tab ────────────────────────────────────────────── */}
        <TabsContent value="education" className="mt-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">Education</CardTitle>
                <Button
                  size="sm"
                  className="bg-indigo-600 hover:bg-indigo-700 gap-1"
                  onClick={() => setShowAddEdu((v) => !v)}
                >
                  <Plus className="h-3.5 w-3.5" />
                  Add Education
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Add education form */}
              {showAddEdu && (
                <div className="rounded-lg border border-dashed border-indigo-300 bg-indigo-50/30 p-4 space-y-3">
                  <p className="text-sm font-medium text-gray-700">New Education</p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="space-y-1 sm:col-span-2">
                      <Label className="text-xs">Degree <span className="text-red-500">*</span></Label>
                      <Input
                        placeholder="B.S. Computer Science"
                        value={newEdu.degree}
                        onChange={(e) => setNewEdu((p) => ({ ...p, degree: e.target.value }))}
                      />
                    </div>
                    <div className="space-y-1 sm:col-span-2">
                      <Label className="text-xs">Institution <span className="text-red-500">*</span></Label>
                      <Input
                        placeholder="MIT"
                        value={newEdu.institution}
                        onChange={(e) => setNewEdu((p) => ({ ...p, institution: e.target.value }))}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Start Year</Label>
                      <Input
                        type="number"
                        placeholder="2016"
                        min={1950}
                        max={2040}
                        value={newEdu.start_year ?? ''}
                        onChange={(e) => setNewEdu((p) => ({ ...p, start_year: e.target.value ? Number(e.target.value) : null }))}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">End Year</Label>
                      <Input
                        type="number"
                        placeholder="2020"
                        min={1950}
                        max={2040}
                        value={newEdu.end_year ?? ''}
                        onChange={(e) => setNewEdu((p) => ({ ...p, end_year: e.target.value ? Number(e.target.value) : null }))}
                      />
                    </div>
                    <div className="space-y-1 sm:col-span-2">
                      <Label className="text-xs">Grade / GPA <span className="text-red-500">*</span></Label>
                      <Input
                        placeholder="3.8 / 4.0"
                        value={newEdu.grade ?? ''}
                        onChange={(e) => setNewEdu((p) => ({ ...p, grade: e.target.value }))}
                      />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      className="bg-indigo-600 hover:bg-indigo-700 gap-1"
                      onClick={handleAddEducation}
                      disabled={!newEdu.degree.trim() || !newEdu.institution.trim() || addingEdu}
                    >
                      {addingEdu ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
                      Add
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => setShowAddEdu(false)}>Cancel</Button>
                  </div>
                </div>
              )}

              {/* Education list */}
              {educationLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-indigo-600" />
                </div>
              ) : education.length === 0 ? (
                <p className="text-sm text-gray-400">No education added yet.</p>
              ) : (
                <div className="space-y-3">
                  {education.map((edu) => (
                    <div key={edu.id ?? edu.degree} className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <p className="font-semibold text-gray-900">{edu.degree}</p>
                          <p className="text-sm text-indigo-600 mt-0.5">{edu.institution}</p>
                          <div className="flex items-center gap-3 mt-0.5 text-xs text-gray-500 flex-wrap">
                            {(edu.start_year || edu.end_year) && (
                              <span>
                                {edu.start_year ?? '?'} – {edu.end_year ?? 'Present'}
                              </span>
                            )}
                            {edu.grade && <span>Grade: {edu.grade}</span>}
                          </div>
                        </div>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 shrink-0"
                          onClick={() => edu.id && handleDeleteEducation(edu.id)}
                          aria-label="Remove education"
                        >
                          <Trash2 className="h-3.5 w-3.5 text-red-500" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── AI Suggestions tab ──────────────────────────────────────── */}
        <TabsContent value="ai-suggestions" className="space-y-4 mt-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">AI Skill Suggestions</CardTitle>
              <p className="text-sm text-gray-500 mt-0.5">
                Skills inferred from your resume and project history by AI.
              </p>
            </CardHeader>
            <CardContent className="space-y-3">
              {skillsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-indigo-600" />
                </div>
              ) : skills.filter(s => s.source !== 'manual').length === 0 ? (
                <p className="text-sm text-gray-400">
                  No AI suggestions yet. Upload your resume to generate skill suggestions.
                </p>
              ) : (
                skills.filter(s => s.source !== 'manual').map(skill => (
                  <div key={skill.id} className="bg-purple-50 border border-purple-200 rounded-2xl p-4">
                    <p className="font-medium text-slate-700">
                      {skill.name} — {skill.source === 'ai_extracted' ? 'extracted from resume' : 'inferred from projects'}
                    </p>
                    <p className="text-xs text-slate-500 mt-0.5">{skill.proficiency_level} • {skill.years_of_experience} yrs</p>
                    <div className="flex gap-3 mt-3">
                      <Button
                        size="sm"
                        className="bg-purple-600 hover:bg-purple-700 text-white text-xs"
                        onClick={() => router.push('/employee/profile?tab=skills')}
                      >
                        View in Skills
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="text-xs"
                        onClick={() => handleDeleteSkill(skill.id)}
                      >
                        Remove
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Review Status tab ────────────────────────────────────────── */}
        <TabsContent value="review" className="space-y-4 mt-4">
          <Card>
            <CardHeader className="pb-3"><CardTitle className="text-base">Review Status</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-4">
                <ProfileStatusBadge status={profile.status} size="lg" />
                <div>
                  <p className="font-medium text-gray-900">
                    {profile.status === 'approved' ? 'Your profile has been approved by HR.' :
                     profile.status === 'submitted' ? 'Your profile is currently under review.' :
                     profile.status === 'rejected' ? 'Your profile was rejected. Please update and resubmit.' :
                     'Your profile has not been submitted for review yet.'}
                  </p>
                </div>
              </div>
              {profile.status === 'rejected' && (
                <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3">
                  <p className="text-sm font-semibold text-red-700">HR Feedback</p>
                  <p className="text-sm text-red-600 mt-1">
                    {hrComment || 'Your profile was rejected. Please update and resubmit.'}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Settings tab ─────────────────────────────────────────────── */}
        <TabsContent value="settings" className="space-y-4 mt-4">
          <Card>
            <CardHeader className="pb-3"><CardTitle className="text-base">Settings</CardTitle></CardHeader>
            <CardContent>
              <p className="text-sm text-gray-500">Settings and account preferences are coming soon.</p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* ── Submit for Review (shown only on non-dashboard tabs) ────────── */}
      {activeTab !== 'dashboard' && (
        <Card className="border-indigo-100 bg-indigo-50">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div>
                <h3 className="font-semibold text-gray-900">Ready for review?</h3>
                <p className="mt-0.5 text-sm text-gray-600">
                  {profile.status === 'submitted' && 'Your profile is currently under review.'}
                  {profile.status === 'approved' && 'Your profile has been approved by HR.'}
                  {profile.status === 'rejected' && 'Profile was rejected. Update and resubmit.'}
                  {profile.status === 'incomplete' && 'Submit your profile for HR review when ready.'}
                </p>
              </div>
              {profile.status === 'submitted' ? (
                <Button disabled className="gap-2 bg-blue-50 text-blue-600 border border-blue-200 hover:bg-blue-50">
                  <Clock className="h-4 w-4" /> Awaiting Review
                </Button>
              ) : profile.status === 'approved' ? (
                <Button disabled className="gap-2 bg-green-50 text-green-600 border border-green-200 hover:bg-green-50">
                  Approved
                </Button>
              ) : (
                <Button
                  className="gap-2 bg-indigo-600 hover:bg-indigo-700"
                  disabled={!canSubmit || isSubmitting}
                  onClick={handleSubmitForReview}
                >
                  {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  Submit for Review
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </section>
  )
}

export default function EmployeeProfilePage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    }>
      <EmployeeProfilePageContent />
    </Suspense>
  )
}

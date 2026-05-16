'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { createClient } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { ProfileStatusBadge } from '@/components/profile/ProfileStatusBadge'
import { SkillsEditor } from '@/components/profile/SkillsEditor'
import { ExperienceEditor } from '@/components/profile/ExperienceEditor'
import { ProjectsEditor } from '@/components/profile/ProjectsEditor'
import { EducationEditor } from '@/components/profile/EducationEditor'
import { CertificationsEditor } from '@/components/profile/CertificationsEditor'
import { LanguagesEditor } from '@/components/profile/LanguagesEditor'
import { ResumeUpload } from '@/components/profile/ResumeUpload'
import { ArrowLeft, Pencil, Save, X, Loader2, CheckCircle, XCircle, FileText, Link2 } from 'lucide-react'
import Link from 'next/link'
import { RejectModal } from '@/components/reviews/RejectModal'
import type { Profile, ProfileStatus, Skill, ProjectEntry, EducationEntry, Certification, Language } from '@/types'

export const dynamic = 'force-dynamic'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

// ─── Same helpers as employee profile page ────────────────────────────────────

interface RawHRUser {
  id?: string; email?: string; full_name?: string; phone?: string; designation?: string
  department?: string; location?: string; experience_years?: string | number | null
  avatar_url?: string | null; profile_status?: string; created_at?: string; updated_at?: string
}
interface RawHREmployee {
  summary?: string; skills?: Skill[]; projects?: ProjectEntry[]; education?: EducationEntry[]
  certifications?: Certification[]; languages?: Language[]; linkedin_url?: string
  github_url?: string; portfolio_url?: string
}

function normalizeProfile(apiData: { user: RawHRUser; employee: RawHREmployee | null }): Profile {
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

function buildPatchBody(draft: Profile) {
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
      skills: draft.skills,
      projects: draft.projects,
      education: draft.education,
      certifications: draft.certifications,
      languages: draft.languages,
      linkedin_url: draft.links?.linkedin ?? '',
      github_url: draft.links?.github ?? '',
      portfolio_url: draft.links?.portfolio ?? '',
    },
  }
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function EmployeeDetailPage() {
  const params = useParams()
  const router = useRouter()
  const supabase = createClient()

  const id = params.id as string
  const [profile, setProfile] = useState<Profile | null>(null)
  const [draft, setDraft] = useState<Profile | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [resumeFileName, setResumeFileName] = useState<string | null>(null)
  const [resumeUploadedAt, setResumeUploadedAt] = useState<string | null>(null)
  const [linkedinUrl, setLinkedinUrl] = useState('')
  const [isImportingLinkedin, setIsImportingLinkedin] = useState(false)
  const [pendingReviewId, setPendingReviewId] = useState<string | null>(null)
  const [isApproving, setIsApproving] = useState(false)
  const [showRejectModal, setShowRejectModal] = useState(false)

  const getToken = useCallback(async () => {
    const { data } = await supabase.auth.getSession()
    return data.session?.access_token ?? ''
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const fetchResumeInfo = useCallback(async (token: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/profiles/${id}/resume/`, {
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
  }, [id])

  const fetchProfile = useCallback(async () => {
    setIsLoading(true)
    try {
      const token = await getToken()

      // Fetch profile + all sub-resources in parallel
      const [profileRes, skillsRes, expRes, projRes, eduRes, certRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/profiles/${id}/`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_BASE}/api/v1/profiles/${id}/skills/`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_BASE}/api/v1/profiles/${id}/experiences/`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_BASE}/api/v1/profiles/${id}/projects/`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_BASE}/api/v1/profiles/${id}/education/`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_BASE}/api/v1/profiles/${id}/certifications/`, { headers: { Authorization: `Bearer ${token}` } }),
      ])

      if (!profileRes.ok) throw new Error()
      const body = await profileRes.json()
      const normalized = normalizeProfile(body.data)

      // Map sub-resources to the types the editor components expect
      if (skillsRes.ok) {
        const { data: raw } = await skillsRes.json()
        normalized.skills = (raw ?? []).map((s: Record<string, unknown>) => ({
          id: s.id,
          name: s.name,
          proficiency: s.proficiency_level,
          years: s.years_of_experience ?? 0,
        }))
      }
      if (expRes.ok) {
        const { data: raw } = await expRes.json()
        normalized.experience = (raw ?? []).map((e: Record<string, unknown>) => ({
          id: e.id,
          company: e.company_name,
          role: e.designation,
          start_date: e.start_date,
          end_date: e.end_date ?? null,
          description: e.description ?? '',
        }))
      }
      if (projRes.ok) {
        const { data: raw } = await projRes.json()
        normalized.projects = (raw ?? []).map((p: Record<string, unknown>) => ({
          id: p.id,
          name: p.name,
          description: p.description ?? '',
          tech_stack: Array.isArray(p.skills)
            ? (p.skills as Array<{ name: string }>).map((s) => s.name)
            : [],
          duration: '',
        }))
      }
      if (eduRes.ok) {
        const { data: raw } = await eduRes.json()
        normalized.education = (raw ?? []).map((e: Record<string, unknown>) => ({
          id: e.id,
          degree: e.degree,
          institution: e.institution,
          graduation_year: (e.end_year as number) ?? 0,
        }))
      }
      if (certRes.ok) {
        const { data: raw } = await certRes.json()
        normalized.certifications = (raw ?? []).map((c: Record<string, unknown>) => ({
          id: c.id,
          name: c.name,
          issuer: c.issuer ?? '',
          issued_date: c.issue_date ?? '',
          expiry_date: (c.expiry_date as string) ?? null,
        }))
      }

      setProfile(normalized)
      setDraft(normalized)
      setLinkedinUrl(normalized.links?.linkedin ?? '')
      await fetchResumeInfo(token)

      // If profile is submitted, fetch the pending review ID so we can approve/reject
      if ((body.data?.user?.profile_status ?? 'incomplete') === 'submitted') {
        try {
          const reviewRes = await fetch(
            `${API_BASE}/api/v1/reviews/?status=pending&profile_id=${id}`,
            { headers: { Authorization: `Bearer ${token}` } }
          )
          if (reviewRes.ok) {
            const reviewBody = await reviewRes.json()
            const reviews = reviewBody.data ?? []
            setPendingReviewId(reviews.length > 0 ? reviews[0].id : null)
          }
        } catch {
          setPendingReviewId(null)
        }
      } else {
        setPendingReviewId(null)
      }
    } catch {
      toast.error('Failed to load profile.')
    } finally {
      setIsLoading(false)
    }
  }, [id, getToken, fetchResumeInfo])

  useEffect(() => {
    fetchProfile()
  }, [fetchProfile])

  const handleLinkedinImport = async () => {
    if (!linkedinUrl.trim()) return
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
      toast.success('LinkedIn profile imported successfully!')
      await fetchProfile()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to import LinkedIn profile.')
    } finally {
      setIsImportingLinkedin(false)
    }
  }

  const handleEditToggle = () => {
    if (isEditing) setDraft(profile)
    setIsEditing((v) => !v)
  }

  const handleSave = async () => {
    if (!draft) return
    setIsSaving(true)
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/api/v1/profiles/${id}/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(buildPatchBody(draft)),
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

  const updateDraft = (field: keyof Profile, value: unknown) =>
    setDraft((prev) => (prev ? { ...prev, [field]: value } : prev))

  const handleApprove = async () => {
    if (!pendingReviewId) return
    setIsApproving(true)
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/api/v1/reviews/${pendingReviewId}/approve/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error()
      toast.success('Profile approved.')
      await fetchProfile()
    } catch {
      toast.error('Failed to approve profile.')
    } finally {
      setIsApproving(false)
    }
  }

  const handleReject = async (comment: string) => {
    if (!pendingReviewId) return
    const token = await getToken()
    const res = await fetch(`${API_BASE}/api/v1/reviews/${pendingReviewId}/reject/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ comment }),
    })
    if (!res.ok) throw new Error()
    toast.success('Profile rejected.')
    await fetchProfile()
  }

  const initials = profile?.full_name
    ? profile.full_name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)
    : '?'

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
        <p className="text-gray-500">Profile not found.</p>
        <Button variant="outline" onClick={() => router.push('/hr/employees')}>Back to Employees</Button>
      </div>
    )
  }

  return (
    <section aria-labelledby="employee-detail-heading" className="w-full space-y-5">
      {/* Top bar */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Link href="/hr/employees">
            <Button variant="ghost" size="icon" aria-label="Back">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <span className="text-sm text-gray-500">Employee Profile</span>
        </div>
        {pendingReviewId && !isEditing && (
          <div className="flex items-center gap-2 flex-wrap">
            <Button
              className="bg-green-600 hover:bg-green-700 text-white gap-1"
              onClick={handleApprove}
              disabled={isApproving}
            >
              {isApproving ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle className="h-4 w-4" />}
              Approve
            </Button>
            <Button
              variant="outline"
              className="border-red-300 text-red-600 hover:bg-red-50 gap-1"
              onClick={() => setShowRejectModal(true)}
              disabled={isApproving}
            >
              <XCircle className="h-4 w-4" /> Reject
            </Button>
          </div>
        )}
      </div>

      {/* Pending review banner */}
      {pendingReviewId && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 flex items-center gap-2">
          <Loader2 className="h-4 w-4 text-amber-500 shrink-0" />
          <p className="text-sm text-amber-700">
            This profile is <span className="font-semibold">awaiting HR review</span>. Use the Approve or Reject buttons above to act on it.
          </p>
        </div>
      )}

      {/* Header card */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-start gap-4">
            <Avatar className="h-16 w-16 shrink-0">
              {profile.avatar_url && <AvatarImage src={profile.avatar_url} alt={profile.full_name} />}
              <AvatarFallback className="bg-indigo-100 text-indigo-700 text-xl font-bold">
                {initials}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between flex-wrap gap-2">
                <div>
                  <p className="text-base font-semibold text-gray-900 truncate">{profile.full_name || '—'}</p>
                  {profile.designation && <p className="text-sm font-medium text-indigo-600 mt-0.5">{profile.designation}</p>}
                  <div className="mt-1 flex flex-wrap gap-x-3 text-xs text-gray-500">
                    {profile.department && <span>{profile.department}</span>}
                    {profile.location && <span>{profile.location}</span>}
                    {profile.experience_years != null && profile.experience_years > 0 && (
                      <span>{profile.experience_years} yrs exp</span>
                    )}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-2 shrink-0">
                  <ProfileStatusBadge status={profile.status} size="lg" />
                  <div className="flex items-center gap-1">
                    {isEditing ? (
                      <>
                        <Button variant="ghost" size="icon" onClick={handleEditToggle} disabled={isSaving} className="h-7 w-7 text-gray-400 hover:text-gray-600" title="Cancel">
                          <X className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={handleSave} disabled={isSaving} className="h-7 w-7 text-indigo-600 hover:text-indigo-700" title="Save">
                          {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                        </Button>
                      </>
                    ) : (
                      <Button variant="ghost" size="icon" onClick={handleEditToggle} className="h-7 w-7 text-gray-400 hover:text-indigo-600" title="Edit Profile">
                        <Pencil className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Resume & LinkedIn */}
      <ProfileSection title="Resume &amp; LinkedIn">
        <div className="flex flex-col sm:flex-row items-stretch gap-0">
          {/* Resume Upload */}
          <div className="flex-1 rounded-xl border border-gray-200 bg-gray-50 p-5">
            <div className="flex items-start gap-3 mb-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-indigo-100">
                <FileText className="h-5 w-5 text-indigo-600" />
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-900">Upload Resume</p>
                <p className="text-xs text-gray-500 mt-0.5">Upload employee&apos;s resume (PDF or DOCX)</p>
              </div>
            </div>
            <ResumeUpload
              profileId={id}
              fileName={resumeFileName}
              uploadedAt={resumeUploadedAt}
              onUploadSuccess={() => fetchProfile()}
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
                <p className="text-xs text-gray-500 mt-0.5">Paste employee&apos;s LinkedIn URL to auto-import data</p>
              </div>
            </div>
            <div className="flex gap-2">
              <Input
                placeholder="https://www.linkedin.com/in/username"
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
      </ProfileSection>

      {/* Basic Info */}
      <ProfileSection title="Basic Info">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <FieldRow label="Full Name" value={draft.full_name} isEditing={isEditing} onChange={(v) => updateDraft('full_name', v)} />
          <FieldRow label="Designation" value={draft.designation} isEditing={isEditing} onChange={(v) => updateDraft('designation', v)} />
          <FieldRow label="Department" value={draft.department} isEditing={isEditing} onChange={(v) => updateDraft('department', v)} />
          <FieldRow label="Location" value={draft.location} isEditing={isEditing} onChange={(v) => updateDraft('location', v)} />
          <div className="space-y-1">
            <Label className="text-xs text-gray-500">Experience (Years)</Label>
            {isEditing ? (
              <Input type="number" min={0} value={draft.experience_years ?? ''} onChange={(e) => updateDraft('experience_years', Number(e.target.value))} />
            ) : (
              <p className="text-sm text-gray-800">{profile.experience_years && profile.experience_years > 0 ? String(profile.experience_years) : '—'}</p>
            )}
          </div>
        </div>
      </ProfileSection>

      {/* Contact */}
      <ProfileSection title="Contact">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <FieldRow label="Email" value={draft.email} readOnly />
          <FieldRow label="Phone" value={draft.phone} isEditing={isEditing} onChange={(v) => updateDraft('phone', v)} placeholder="+1-555-0100" />
        </div>
      </ProfileSection>

      {/* Summary */}
      <ProfileSection title="Summary">
        {isEditing ? (
          <Textarea value={draft.summary ?? ''} onChange={(e) => updateDraft('summary', e.target.value)} placeholder="Brief professional summary..." rows={4} />
        ) : (
          <p className="text-sm text-gray-700 whitespace-pre-wrap">
            {profile.summary || <span className="text-gray-400">No summary added.</span>}
          </p>
        )}
      </ProfileSection>

      <ProfileSection title="Skills">
        <SkillsEditor skills={draft.skills ?? []} isEditing={isEditing} onChange={(s) => updateDraft('skills', s)} />
      </ProfileSection>

      <ProfileSection title="Work Experience">
        <ExperienceEditor experience={draft.experience ?? []} isEditing={isEditing} onChange={(e) => updateDraft('experience', e)} />
      </ProfileSection>

      <ProfileSection title="Projects">
        <ProjectsEditor projects={draft.projects ?? []} isEditing={isEditing} onChange={(p) => updateDraft('projects', p)} />
      </ProfileSection>

      <ProfileSection title="Education">
        <EducationEditor education={draft.education ?? []} isEditing={isEditing} onChange={(e) => updateDraft('education', e)} />
      </ProfileSection>

      <ProfileSection title="Certifications">
        <CertificationsEditor certifications={draft.certifications ?? []} isEditing={isEditing} onChange={(c) => updateDraft('certifications', c)} />
      </ProfileSection>

      <ProfileSection title="Languages">
        <LanguagesEditor languages={draft.languages ?? []} isEditing={isEditing} onChange={(l) => updateDraft('languages', l)} />
      </ProfileSection>

      <ProfileSection title="Links">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <FieldRow label="GitHub" value={draft.links?.github ?? ''} isEditing={isEditing} onChange={(v) => updateDraft('links', { ...draft.links, github: v })} placeholder="https://github.com/..." type="url" />
          <FieldRow label="Portfolio" value={draft.links?.portfolio ?? ''} isEditing={isEditing} onChange={(v) => updateDraft('links', { ...draft.links, portfolio: v })} placeholder="https://yoursite.com" type="url" />
        </div>
      </ProfileSection>

      {showRejectModal && profile && (
        <RejectModal
          open={showRejectModal}
          onOpenChange={(open) => setShowRejectModal(open)}
          employeeName={profile.full_name}
          onConfirm={handleReject}
        />
      )}
    </section>
  )
}

// ─── Helper components ────────────────────────────────────────────────────────

function ProfileSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader className="pb-3"><CardTitle className="text-base">{title}</CardTitle></CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}

interface FieldRowProps {
  label: string
  value: string | number | undefined | null
  isEditing?: boolean
  readOnly?: boolean
  onChange?: (value: string) => void
  placeholder?: string
  type?: string
}

function FieldRow({ label, value, isEditing, readOnly, onChange, placeholder, type = 'text' }: FieldRowProps) {
  return (
    <div className="space-y-1">
      <Label className="text-xs text-gray-500">{label}</Label>
      {isEditing && !readOnly ? (
        <Input type={type} value={value ?? ''} onChange={(e) => onChange?.(e.target.value)} placeholder={placeholder} />
      ) : (
        <p className="text-sm text-gray-800">{value || <span className="text-gray-400">—</span>}</p>
      )}
    </div>
  )
}

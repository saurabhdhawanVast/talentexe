'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams } from 'next/navigation'
import { toast } from 'sonner'
import { createClient } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ProfileStatusBadge } from '@/components/profile/ProfileStatusBadge'
import { SkillsEditor } from '@/components/profile/SkillsEditor'
import { ExperienceEditor } from '@/components/profile/ExperienceEditor'
import { ProjectsEditor } from '@/components/profile/ProjectsEditor'
import { EducationEditor } from '@/components/profile/EducationEditor'
import { CertificationsEditor } from '@/components/profile/CertificationsEditor'
import { LanguagesEditor } from '@/components/profile/LanguagesEditor'
import { ArrowLeft, Download, Loader2, User, Link as LinkIcon } from 'lucide-react'
import Link from 'next/link'
import type { Profile } from '@/types'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

export default function ProfilePreviewPage() {
  const params = useParams()
  const supabase = createClient()
  const id = params.id as string

  const [profile, setProfile] = useState<Profile | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isDownloading, setIsDownloading] = useState(false)

  const fetchProfile = useCallback(async () => {
    setIsLoading(true)
    try {
      const { data: sessionData } = await supabase.auth.getSession()
      if (!sessionData.session) return
      const res = await fetch(`${API_BASE}/api/v1/profiles/${id}/`, {
        headers: { Authorization: `Bearer ${sessionData.session.access_token}` },
      })
      if (!res.ok) throw new Error()
      const body = await res.json()
      setProfile(body.data)
    } catch {
      toast.error('Failed to load profile.')
    } finally {
      setIsLoading(false)
    }
  }, [id, supabase])

  useEffect(() => { fetchProfile() }, [fetchProfile])

  const handleDownload = async () => {
    setIsDownloading(true)
    try {
      const { data: sessionData } = await supabase.auth.getSession()
      if (!sessionData.session) return
      const res = await fetch(`${API_BASE}/api/v1/profiles/${id}/download/`, {
        headers: { Authorization: `Bearer ${sessionData.session.access_token}` },
      })
      if (!res.ok) throw new Error()

      const contentType = res.headers.get('content-type') ?? ''
      if (contentType.includes('application/json')) {
        const body = await res.json()
        if (body.data?.url) {
          window.open(body.data.url, '_blank', 'noopener,noreferrer')
        }
      } else {
        const blob = await res.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `profile_${id}.pdf`
        a.click()
        URL.revokeObjectURL(url)
      }
    } catch {
      toast.error('Failed to download profile.')
    } finally {
      setIsDownloading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3">
        <p className="text-gray-500">Profile not found.</p>
        <Link href="/hr/search"><Button variant="outline">Back to Search</Button></Link>
      </div>
    )
  }

  return (
    <section className="w-full space-y-5">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link href="/hr/search">
            <Button variant="ghost" size="icon" aria-label="Back to search">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <h1 className="text-2xl font-semibold text-gray-900">Profile Preview</h1>
        </div>
        <Button className="bg-indigo-600 hover:bg-indigo-700 gap-1" onClick={handleDownload} disabled={isDownloading}>
          {isDownloading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
          Download Profile
        </Button>
      </div>

      {/* Header */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-start gap-4">
            <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-indigo-700 text-xl font-bold">
              {profile.full_name ? profile.full_name[0].toUpperCase() : <User className="h-8 w-8" />}
            </div>
            <div className="flex-1">
              <div className="flex items-start justify-between flex-wrap gap-2">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">{profile.full_name}</h2>
                  {profile.designation && <p className="text-sm text-indigo-600">{profile.designation}</p>}
                  <p className="mt-0.5 text-xs text-gray-500">{[profile.department, profile.location].filter(Boolean).join(' · ')}</p>
                </div>
                <ProfileStatusBadge status={profile.status} size="lg" />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {profile.summary && (
        <Card>
          <CardHeader className="pb-3"><CardTitle className="text-base">Summary</CardTitle></CardHeader>
          <CardContent><p className="text-sm text-gray-700 whitespace-pre-wrap">{profile.summary}</p></CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-3"><CardTitle className="text-base">Skills</CardTitle></CardHeader>
        <CardContent><SkillsEditor skills={profile.skills ?? []} isEditing={false} /></CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3"><CardTitle className="text-base">Work Experience</CardTitle></CardHeader>
        <CardContent><ExperienceEditor experience={profile.experience ?? []} isEditing={false} /></CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3"><CardTitle className="text-base">Projects</CardTitle></CardHeader>
        <CardContent><ProjectsEditor projects={profile.projects ?? []} isEditing={false} /></CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3"><CardTitle className="text-base">Education</CardTitle></CardHeader>
        <CardContent><EducationEditor education={profile.education ?? []} isEditing={false} /></CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3"><CardTitle className="text-base">Certifications</CardTitle></CardHeader>
        <CardContent><CertificationsEditor certifications={profile.certifications ?? []} isEditing={false} /></CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3"><CardTitle className="text-base">Languages</CardTitle></CardHeader>
        <CardContent><LanguagesEditor languages={profile.languages ?? []} isEditing={false} /></CardContent>
      </Card>

      {(profile.links?.linkedin || profile.links?.github || profile.links?.portfolio) && (
        <Card>
          <CardHeader className="pb-3"><CardTitle className="text-base">Links</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-1.5">
              {profile.links?.linkedin && (
                <a href={profile.links.linkedin} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-sm text-indigo-600 hover:underline">
                  <LinkIcon className="h-4 w-4" /> LinkedIn
                </a>
              )}
              {profile.links?.github && (
                <a href={profile.links.github} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-sm text-indigo-600 hover:underline">
                  <LinkIcon className="h-4 w-4" /> GitHub
                </a>
              )}
              {profile.links?.portfolio && (
                <a href={profile.links.portfolio} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-sm text-indigo-600 hover:underline">
                  <LinkIcon className="h-4 w-4" /> Portfolio
                </a>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </section>
  )
}

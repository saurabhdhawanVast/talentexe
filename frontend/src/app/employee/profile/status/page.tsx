'use client'

import { useEffect, useState, useCallback } from 'react'
import { toast } from 'sonner'
import { createClient } from '@/lib/supabase'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ProfileStatusBadge } from '@/components/profile/ProfileStatusBadge'
import { Loader2, CheckCircle, Clock, FileText, MessageSquare } from 'lucide-react'
import { format } from 'date-fns'
import type { Profile, Review } from '@/types'

export const dynamic = 'force-dynamic'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

interface TimelineItem {
  label: string
  date: string | null
  icon: React.ReactNode
  done: boolean
}

export default function ProfileStatusPage() {
  const supabase = createClient()
  const [profile, setProfile] = useState<Profile | null>(null)
  const [review, setReview] = useState<Review | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const fetchData = useCallback(async () => {
    setIsLoading(true)
    try {
      const { data: sessionData } = await supabase.auth.getSession()
      if (!sessionData.session) return

      const uid = sessionData.session.user.id

      const [profileRes, reviewRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/profiles/${uid}/`, {
          headers: { Authorization: `Bearer ${sessionData.session.access_token}` },
        }),
        fetch(`${API_BASE}/api/v1/reviews/me/`, {
          headers: { Authorization: `Bearer ${sessionData.session.access_token}` },
        }),
      ])

      if (profileRes.ok) {
        const body = await profileRes.json()
        setProfile(body.data)
      }

      if (reviewRes.ok) {
        const body = await reviewRes.json()
        setReview(body.data ?? null)
      }
    } catch {
      toast.error('Failed to load profile status.')
    } finally {
      setIsLoading(false)
    }
  }, [supabase])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <p className="text-gray-500 text-sm">Profile data unavailable.</p>
      </div>
    )
  }

  // profile.data has user + employee nested, handle both shapes
  type RawProfile = { user?: { created_at?: string; profile_status?: string }; created_at?: string; status?: string }
  const profileAny = profile as unknown as RawProfile
  const createdAt: string = profileAny?.user?.created_at ?? profileAny?.created_at ?? ''
  const profileStatus: string = profileAny?.user?.profile_status ?? profileAny?.status ?? 'incomplete'

  const timeline: TimelineItem[] = [
    {
      label: 'Profile Created',
      date: createdAt,
      icon: <FileText className="h-4 w-4" />,
      done: true,
    },
    {
      label: 'Submitted for Review',
      date: review?.submitted_at ?? null,
      icon: <Clock className="h-4 w-4" />,
      done: ['submitted', 'approved', 'rejected'].includes(profileStatus),
    },
    {
      label: 'HR Review Complete',
      date: review?.reviewed_at ?? null,
      icon: <CheckCircle className="h-4 w-4" />,
      done: ['approved', 'rejected'].includes(profileStatus),
    },
  ]

  return (
    <section aria-labelledby="status-heading" className="w-full max-w-2xl space-y-5">
      <div>
        <h1 id="status-heading" className="text-2xl font-semibold text-gray-900">
          Profile Status
        </h1>
        <p className="mt-1 text-sm text-gray-500">Track your profile submission and review progress.</p>
      </div>

      {/* Status card */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <p className="text-sm font-medium text-gray-500 mb-2">Current Status</p>
              <ProfileStatusBadge status={profileStatus as Profile['status']} size="lg" />
            </div>
            {review?.reviewed_by_name && (
              <div className="text-right">
                <p className="text-xs text-gray-500">Reviewed by</p>
                <p className="text-sm font-medium text-gray-800">{review.reviewed_by_name}</p>
                {review.reviewed_at && (
                  <p className="text-xs text-gray-500">
                    {format(new Date(review.reviewed_at), 'MMM d, yyyy')}
                  </p>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* HR Comment */}
      {review?.hr_comment && (
        <Card className={profileStatus === 'rejected' ? 'border-red-200 bg-red-50' : 'border-green-200 bg-green-50'}>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <MessageSquare className="h-4 w-4" />
              HR Feedback
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-gray-700 whitespace-pre-wrap">{review.hr_comment}</p>
          </CardContent>
        </Card>
      )}

      {/* Timeline */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="relative border-l border-gray-200 ml-3 space-y-6" aria-label="Profile timeline">
            {timeline.map((item, i) => (
              <li key={i} className="ml-6">
                <span
                  className={`absolute -left-3 flex h-6 w-6 items-center justify-center rounded-full ring-4 ring-white ${
                    item.done ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-400'
                  }`}
                >
                  {item.icon}
                </span>
                <div>
                  <p className={`text-sm font-medium ${item.done ? 'text-gray-900' : 'text-gray-400'}`}>
                    {item.label}
                  </p>
                  {item.date ? (
                    <p className="text-xs text-gray-500">
                      {format(new Date(item.date), 'MMMM d, yyyy')}
                    </p>
                  ) : (
                    <p className="text-xs text-gray-400">Pending</p>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </CardContent>
      </Card>
    </section>
  )
}

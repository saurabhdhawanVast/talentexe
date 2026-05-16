'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { createClient } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import { ProfileStatusBadge } from '@/components/profile/ProfileStatusBadge'
import { RejectModal } from '@/components/reviews/RejectModal'
import { CheckCircle, Eye, Loader2, ClipboardCheck } from 'lucide-react'
import { format } from 'date-fns'
import type { Review } from '@/types'

export const dynamic = 'force-dynamic'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

export default function ReviewQueuePage() {
  const router = useRouter()
  const supabase = createClient()
  const [reviews, setReviews] = useState<Review[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [rejectTarget, setRejectTarget] = useState<Review | null>(null)
  const [approvingId, setApprovingId] = useState<string | null>(null)

  const getToken = useCallback(async () => {
    const { data } = await supabase.auth.getSession()
    return data.session?.access_token ?? ''
  }, [supabase])

  const fetchReviews = useCallback(async () => {
    setIsLoading(true)
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/api/v1/reviews/?status=pending`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error()
      const body = await res.json()
      setReviews(body.data)
    } catch {
      toast.error('Failed to load review queue.')
    } finally {
      setIsLoading(false)
    }
  }, [getToken])

  useEffect(() => {
    fetchReviews()
  }, [fetchReviews])

  const handleApprove = async (review: Review) => {
    setApprovingId(review.id)
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/api/v1/reviews/${review.id}/approve/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
      })
      if (!res.ok) throw new Error()
      toast.success(`${review.employee_name}'s profile approved.`)
      setReviews((prev) => prev.filter((r) => r.id !== review.id))
    } catch {
      toast.error('Failed to approve profile.')
    } finally {
      setApprovingId(null)
    }
  }

  const handleReject = async (review: Review, comment: string) => {
    const token = await getToken()
    const res = await fetch(`${API_BASE}/api/v1/reviews/${review.id}/reject/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ comment }),
    })
    if (!res.ok) throw new Error()
    toast.success(`${review.employee_name}'s profile rejected.`)
    setReviews((prev) => prev.filter((r) => r.id !== review.id))
  }

  return (
    <section aria-labelledby="reviews-heading">
      <div className="mb-6">
        <h1 id="reviews-heading" className="text-2xl font-semibold text-gray-900">
          Review Queue
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Employee profiles awaiting HR review and approval.
        </p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
        </div>
      ) : reviews.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 gap-4 rounded-xl border border-dashed border-gray-300">
          <ClipboardCheck className="h-12 w-12 text-gray-200" />
          <div className="text-center">
            <p className="text-sm font-medium text-gray-600">No profiles pending review.</p>
            <p className="mt-1 text-xs text-gray-400">
              Employees will appear here when they submit their profiles for approval.
            </p>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200" role="table">
            <thead className="bg-gray-50">
              <tr>
                {['Employee', 'Department', 'Submitted', 'Status', 'HR Comment', 'Actions'].map((col) => (
                  <th
                    key={col}
                    scope="col"
                    className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider"
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {reviews.map((review) => (
                <tr key={review.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <p className="text-sm font-medium text-gray-900">{review.employee_name}</p>
                    <p className="text-xs text-gray-500">{review.employee_email || '—'}</p>
                    {review.employee_designation && (
                      <p className="text-xs text-indigo-600 font-medium">{review.employee_designation}</p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">{review.employee_department || '—'}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {review.submitted_at
                      ? format(new Date(review.submitted_at), 'MMM d, yyyy')
                      : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <ProfileStatusBadge status={review.status === 'pending' ? 'submitted' : review.status} />
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500 max-w-[200px] truncate">
                    {review.hr_comment || '—'}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        title="View profile"
                        aria-label="View employee profile"
                        onClick={() => router.push(`/hr/employees/${review.profile_id}`)}
                      >
                        <Eye className="h-4 w-4 text-gray-500" />
                      </Button>

                      <Button
                        size="sm"
                        className="bg-green-600 hover:bg-green-700 text-white gap-1"
                        disabled={approvingId === review.id}
                        onClick={() => handleApprove(review)}
                      >
                        {approvingId === review.id ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <CheckCircle className="h-3.5 w-3.5" />
                        )}
                        Approve
                      </Button>

                      <Button
                        size="sm"
                        className="bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 gap-1"
                        onClick={() => setRejectTarget(review)}
                      >
                        Reject
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {rejectTarget && (
        <RejectModal
          open={!!rejectTarget}
          onOpenChange={(open) => !open && setRejectTarget(null)}
          employeeName={rejectTarget.employee_name}
          onConfirm={(comment) => handleReject(rejectTarget, comment)}
        />
      )}
    </section>
  )
}

import { redirect } from 'next/navigation'
import { createServerSupabaseClient } from '@/lib/supabase-server'
import { StatCard, StatCardSkeleton } from '@/components/dashboard/StatCard'
import {
  Users,
  ClipboardCheck,
  AlertCircle,
  CheckCircle2,
  Briefcase,
  TrendingUp,
} from 'lucide-react'
import type { DashboardStats } from '@/types'
import type { Metadata } from 'next'
import { Suspense } from 'react'

export const metadata: Metadata = {
  title: 'HR Dashboard | TalentExe',
}

export const dynamic = 'force-dynamic'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

async function DashboardContent({ token }: { token: string }) {
  let stats: DashboardStats | null = null

  try {
    const res = await fetch(`${API_BASE}/api/v1/dashboard/stats/`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    })
    if (res.ok) {
      const body = await res.json()
      stats = body.data
    }
  } catch {
    // Render empty state if backend is unreachable
  }

  if (!stats) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700">
        Could not load dashboard statistics. Please check that the backend is running.
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Row 1 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        <StatCard
          title="Total Employees"
          value={stats.total_employees}
          icon={Users}
          color="bg-indigo-100 text-indigo-600"
          description="Active accounts in the system"
        />
        <StatCard
          title="Pending Reviews"
          value={stats.pending_reviews}
          icon={ClipboardCheck}
          color="bg-amber-100 text-amber-600"
          description="Profiles awaiting HR approval"
        />
        <StatCard
          title="Incomplete Profiles"
          value={stats.incomplete_profiles}
          icon={AlertCircle}
          color="bg-gray-100 text-gray-600"
          description="Employees yet to submit profiles"
        />
      </div>

      {/* Row 2 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        <StatCard
          title="Approved Profiles"
          value={stats.approved_profiles}
          icon={CheckCircle2}
          color="bg-green-100 text-green-600"
          description="Fully verified employee profiles"
        />
        <StatCard
          title="Bench Employees"
          value={stats.bench_employees}
          icon={Briefcase}
          color="bg-blue-100 text-blue-600"
          description="Currently unassigned to projects"
        />

        {/* Top Skills */}
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm font-medium text-gray-500">Top Skills</p>
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-purple-100 text-purple-600">
              <TrendingUp className="h-5 w-5" />
            </div>
          </div>
          {stats.top_skills.length === 0 ? (
            <p className="text-sm text-gray-400">No skill data yet.</p>
          ) : (
            <ul className="space-y-2">
              {stats.top_skills.slice(0, 5).map((skill) => (
                <li key={skill.name} className="flex items-center justify-between">
                  <span className="text-sm text-gray-700 truncate">{skill.name}</span>
                  <span className="ml-2 shrink-0 inline-flex items-center rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-semibold text-indigo-700">
                    {skill.count}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}

export default async function HRDashboardPage() {
  const supabase = createServerSupabaseClient()
  const {
    data: { session },
  } = await supabase.auth.getSession()

  if (!session) {
    redirect('/login')
  }

  return (
    <section aria-labelledby="dashboard-heading">
      <div className="mb-6">
        <h1 id="dashboard-heading" className="text-2xl font-semibold text-gray-900">
          HR Dashboard
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Workforce overview and key metrics at a glance.
        </p>
      </div>

      <Suspense
        fallback={
          <div className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <StatCardSkeleton key={i} />
              ))}
            </div>
          </div>
        }
      >
        <DashboardContent token={session.access_token} />
      </Suspense>
    </section>
  )
}

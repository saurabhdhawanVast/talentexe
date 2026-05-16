import type { Metadata } from 'next'
import { BarChart3 } from 'lucide-react'

export const metadata: Metadata = {
  title: 'Reports | TalentExe',
}

export default function ReportsPage() {
  return (
    <section aria-labelledby="reports-heading">
      <div className="mb-6">
        <h1 id="reports-heading" className="text-2xl font-semibold text-gray-900">
          Reports
        </h1>
        <p className="mt-1 text-sm text-gray-500">Workforce analytics and insights.</p>
      </div>

      <div className="flex flex-col items-center justify-center py-32 gap-5 rounded-xl border border-dashed border-gray-300 bg-white">
        <div className="flex h-20 w-20 items-center justify-center rounded-full bg-indigo-50">
          <BarChart3 className="h-10 w-10 text-indigo-400" />
        </div>
        <div className="text-center max-w-sm">
          <h2 className="text-xl font-semibold text-gray-900">Reports &amp; Analytics</h2>
          <p className="mt-2 text-sm text-gray-500">This feature is coming soon.</p>
          <p className="mt-1 text-sm text-gray-400">
            Stay tuned for workforce insights, skill gap analysis, and more.
          </p>
        </div>
      </div>
    </section>
  )
}

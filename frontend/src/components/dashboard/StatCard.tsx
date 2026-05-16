import { type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface StatCardProps {
  title: string
  value: number | string
  icon: LucideIcon
  color: string
  description?: string
}

export function StatCard({ title, value, icon: Icon, color, description }: StatCardProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm p-6">
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm font-medium text-gray-500">{title}</p>
        <div className={cn('flex h-10 w-10 items-center justify-center rounded-full', color)}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
      <p className="text-3xl font-bold text-gray-900">{value}</p>
      {description && <p className="mt-1 text-xs text-gray-500">{description}</p>}
    </div>
  )
}

export function StatCardSkeleton() {
  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm p-6 animate-pulse">
      <div className="flex items-center justify-between mb-4">
        <div className="h-4 w-32 bg-gray-200 rounded" />
        <div className="h-10 w-10 bg-gray-200 rounded-full" />
      </div>
      <div className="h-8 w-20 bg-gray-200 rounded" />
      <div className="mt-1 h-3 w-40 bg-gray-100 rounded" />
    </div>
  )
}

import { cn } from '@/lib/utils'
import type { ProfileStatus } from '@/types'

interface ProfileStatusBadgeProps {
  status: ProfileStatus
  className?: string
  size?: 'sm' | 'md' | 'lg'
}

// Colors per spec: Approved #22C55E · Rejected #EF4444 · Complete/Submitted #3B82F6 · Incomplete #F59E0B
const statusConfig: Record<ProfileStatus, { label: string; style: React.CSSProperties }> = {
  incomplete: {
    label: 'Incomplete',
    style: { backgroundColor: '#FEF3C7', color: '#F59E0B', borderColor: '#FDE68A' },
  },
  submitted: {
    label: 'Submitted',
    style: { backgroundColor: '#EFF6FF', color: '#3B82F6', borderColor: '#BFDBFE' },
  },
  approved: {
    label: 'Approved',
    style: { backgroundColor: '#F0FDF4', color: '#22C55E', borderColor: '#BBF7D0' },
  },
  rejected: {
    label: 'Rejected',
    style: { backgroundColor: '#FEF2F2', color: '#EF4444', borderColor: '#FECACA' },
  },
}

const sizeClasses = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-0.5 text-xs',
  lg: 'px-3 py-1 text-sm',
}

export function ProfileStatusBadge({ status, className, size = 'md' }: ProfileStatusBadgeProps) {
  const config = statusConfig[status] ?? statusConfig.incomplete
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border font-semibold',
        sizeClasses[size],
        className
      )}
      style={config.style}
    >
      {config.label}
    </span>
  )
}

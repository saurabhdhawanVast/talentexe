'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  Users,
  Search,
  ClipboardCheck,
  BarChart3,
  LogOut,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'

const navItems = [
  { label: 'Dashboard', href: '/hr/dashboard', icon: LayoutDashboard },
  { label: 'Employee List', href: '/hr/employees', icon: Users },
  { label: 'Smart Search', href: '/hr/search', icon: Search },
  { label: 'Review Queue', href: '/hr/reviews', icon: ClipboardCheck },
  { label: 'Reports', href: '/hr/reports', icon: BarChart3 },
] as const

export function HrSidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const supabase = createClient()
  const [collapsed, setCollapsed] = useState(false)

  const handleLogout = async () => {
    await supabase.auth.signOut()
    router.push('/login')
  }

  return (
    <nav
      className={cn(
        'bg-white border-r border-gray-200 h-full flex flex-col shrink-0 transition-all duration-200',
        collapsed ? 'w-16' : 'w-64'
      )}
      aria-label="HR navigation"
    >
      {/* Toggle button row */}
      <div className={cn(
        'h-14 flex items-center border-b border-gray-200 shrink-0',
        collapsed ? 'justify-center px-0' : 'justify-end px-3'
      )}>
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="p-1.5 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>
      </div>

      {/* Nav items */}
      <ul className="flex-1 overflow-y-auto py-4 space-y-1 px-2" role="list">
        {navItems.map(({ label, href, icon: Icon }) => {
          const isActive = pathname === href || pathname.startsWith(href + '/')
          return (
            <li key={href}>
              <Link
                href={href}
                title={collapsed ? label : undefined}
                className={cn(
                  'flex items-center gap-3 px-2.5 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  collapsed && 'justify-center',
                  isActive
                    ? 'bg-indigo-50 text-indigo-600'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                )}
                aria-current={isActive ? 'page' : undefined}
              >
                <Icon className={cn('h-4 w-4 shrink-0', isActive ? 'text-indigo-600' : 'text-gray-400')} />
                {!collapsed && label}
              </Link>
            </li>
          )
        })}
      </ul>

      {/* Logout */}
      <div className="p-2 border-t border-gray-200 shrink-0">
        <button
          onClick={handleLogout}
          title={collapsed ? 'Logout' : undefined}
          className={cn(
            'flex w-full items-center gap-3 px-2.5 py-2.5 rounded-lg text-sm font-medium text-gray-600 hover:bg-red-50 hover:text-red-600 transition-colors',
            collapsed && 'justify-center'
          )}
        >
          <LogOut className="h-4 w-4 shrink-0 text-gray-400" />
          {!collapsed && 'Logout'}
        </button>
      </div>
    </nav>
  )
}

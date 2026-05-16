'use client'

import { Suspense, useState } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase'
import { cn } from '@/lib/utils'
import { Sheet, SheetContent } from '@/components/ui/sheet'
import {
  LayoutDashboard,
  User,
  FileText,
  Zap,
  Briefcase,
  FolderOpen,
  Award,
  GraduationCap,
  ClipboardCheck,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Menu,
} from 'lucide-react'

const navItems = [
  { label: 'Dashboard',          tab: 'dashboard',      icon: LayoutDashboard },
  { label: 'My Profile',         tab: 'overview',       icon: User },
  { label: 'Resume & LinkedIn',  tab: 'resume',         icon: FileText },
  { label: 'Skills',             tab: 'skills',         icon: Zap },
  { label: 'Work Experience',    tab: 'experience',     icon: Briefcase },
  { label: 'Projects',           tab: 'projects',       icon: FolderOpen },
  { label: 'Certifications',     tab: 'certifications', icon: Award },
  { label: 'Education',          tab: 'education',      icon: GraduationCap },
  { label: 'Review Status',      tab: 'review',         icon: ClipboardCheck },
  { label: 'Settings',           tab: 'settings',       icon: Settings },
] as const

interface SidebarInnerProps {}

function NavList({
  activeTab,
  collapsed,
  onNavigate,
}: {
  activeTab: string
  collapsed: boolean
  onNavigate: (tab: string) => void
}) {
  return (
    <ul
      className="flex-1 overflow-y-auto scrollbar-hide py-4 space-y-1 px-2"
      role="list"
    >
      {navItems.map(({ label, tab, icon: Icon }) => {
        const isActive = activeTab === tab
        return (
          <li key={tab}>
            <button
              type="button"
              onClick={() => onNavigate(tab)}
              title={collapsed ? label : undefined}
              aria-current={isActive ? 'page' : undefined}
              className={cn(
                'flex w-full items-center gap-3 px-2.5 py-2.5 rounded-lg text-sm font-medium transition-colors',
                collapsed && 'justify-center',
                isActive
                  ? 'bg-indigo-50 text-indigo-600'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              )}
            >
              <Icon
                className={cn(
                  'h-4 w-4 shrink-0',
                  isActive ? 'text-indigo-600' : 'text-gray-400'
                )}
              />
              {!collapsed && label}
            </button>
          </li>
        )
      })}
    </ul>
  )
}


function SidebarInner({}: SidebarInnerProps) {
  const searchParams = useSearchParams()
  const router = useRouter()
  const supabase = createClient()
  const [collapsed, setCollapsed] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const activeTab = searchParams.get('tab') ?? 'dashboard'

  const handleLogout = async () => {
    await supabase.auth.signOut()
    router.push('/login')
  }

  const navigate = (tab: string) => {
    router.push(`/employee/profile?tab=${tab}`)
    setDrawerOpen(false)
  }

  return (
    <>
      {/* ── Desktop sidebar ───────────────────────────────────────────────── */}
      <nav
        className={cn(
          'hidden md:flex bg-white border-r border-gray-200 h-full flex-col shrink-0 transition-all duration-200',
          collapsed ? 'w-16' : 'w-64'
        )}
        aria-label="Employee navigation"
      >
        {/* Toggle row */}
        <div
          className={cn(
            'h-14 flex items-center border-b border-gray-200 shrink-0',
            collapsed ? 'justify-center px-0' : 'justify-end px-3'
          )}
        >
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

        <NavList
          activeTab={activeTab}
          collapsed={collapsed}
          onNavigate={navigate}
        />

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

      {/* ── Mobile: thin trigger strip ───────────────────────────────────── */}
      <div className="md:hidden flex items-start justify-center w-12 bg-white border-r border-gray-200 shrink-0 pt-3">
        <button
          onClick={() => setDrawerOpen(true)}
          className="p-1.5 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          aria-label="Open navigation menu"
        >
          <Menu className="h-5 w-5" />
        </button>
      </div>

      {/* ── Mobile: Sheet/Drawer ─────────────────────────────────────────── */}
      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetContent side="left" className="p-0 w-64">
          <nav className="flex flex-col h-full" aria-label="Employee navigation">
            <div className="h-14 flex items-center justify-end border-b border-gray-200 px-3 shrink-0">
              <button
                onClick={() => setDrawerOpen(false)}
                className="p-1.5 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
                aria-label="Close menu"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
            </div>

            <NavList
              activeTab={activeTab}
              collapsed={false}
              onNavigate={navigate}
            />

            <div className="p-2 border-t border-gray-200 shrink-0">
              <button
                onClick={handleLogout}
                className="flex w-full items-center gap-3 px-2.5 py-2.5 rounded-lg text-sm font-medium text-gray-600 hover:bg-red-50 hover:text-red-600 transition-colors"
              >
                <LogOut className="h-4 w-4 shrink-0 text-gray-400" />
                Logout
              </button>
            </div>
          </nav>
        </SheetContent>
      </Sheet>
    </>
  )
}

export function EmployeeSidebar() {
  return (
    <Suspense
      fallback={
        <div className="hidden md:block w-64 bg-white border-r border-gray-200 shrink-0" />
      }
    >
      <SidebarInner />
    </Suspense>
  )
}

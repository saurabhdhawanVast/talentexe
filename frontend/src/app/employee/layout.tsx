import { redirect } from 'next/navigation'
import { createServerSupabaseClient } from '@/lib/supabase-server'
import { EmployeeSidebar } from '@/components/layout/EmployeeSidebar'
import { Navbar } from '@/components/layout/Navbar'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

interface EmployeeLayoutProps {
  children: React.ReactNode
}

export default async function EmployeeLayout({ children }: EmployeeLayoutProps) {
  const supabase = createServerSupabaseClient()

  const { data: { session } } = await supabase.auth.getSession()
  if (!session) {
    redirect('/login')
  }

  const user = session.user

  let userName = ''
  let userEmail = user.email ?? ''
  let avatarUrl: string | undefined
  let userId = user.id

  try {
    const meRes = await fetch(`${API_BASE}/api/v1/auth/me/`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
      cache: 'no-store',
    })
    if (meRes.ok) {
      const { data } = await meRes.json()
      if (data.role !== 'employee') {
        redirect('/hr/dashboard')
      }
      userName = data.full_name ?? ''
      avatarUrl = data.avatar_url ?? undefined
      userId = data.id ?? user.id
    }
  } catch {
    // Continue with session data if backend is unreachable
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <EmployeeSidebar />
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        <Navbar
          userEmail={userEmail}
          userName={userName}
          avatarUrl={avatarUrl}
          role="employee"
          userId={userId}
        />
        <main className="flex-1 overflow-auto p-6 bg-gray-50">
          {children}
        </main>
      </div>
    </div>
  )
}

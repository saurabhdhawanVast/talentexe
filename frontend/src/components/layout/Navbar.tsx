'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ChangePasswordModal } from './ChangePasswordModal'
import { AvatarUploadModal } from './AvatarUploadModal'
import { KeyRound, ImageIcon, LogOut, ChevronDown } from 'lucide-react'

interface NavbarProps {
  userEmail: string
  userName: string
  avatarUrl?: string
  role: 'hr' | 'employee'
  userId: string
}

export function Navbar({ userEmail, userName, avatarUrl, role, userId }: NavbarProps) {
  const router = useRouter()
  const supabase = createClient()
  const [changePasswordOpen, setChangePasswordOpen] = useState(false)
  const [avatarUploadOpen, setAvatarUploadOpen] = useState(false)
  const [currentAvatarUrl, setCurrentAvatarUrl] = useState(avatarUrl)

  const dashboardHref = role === 'hr' ? '/hr/dashboard' : '/employee/profile'
  const initials = userName
    ? userName
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : userEmail.slice(0, 2).toUpperCase()

  const handleLogout = async () => {
    await supabase.auth.signOut()
    router.push('/login')
  }

  return (
    <>
      <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 shrink-0">
        <Link
          href={dashboardHref}
          className="text-xl font-bold text-indigo-600 tracking-tight hover:text-indigo-700 transition-colors"
        >
          Talent.exe
        </Link>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              className="flex items-center gap-2 rounded-full focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:ring-offset-2"
              aria-label="User menu"
            >
              <Avatar className="h-9 w-9">
                {currentAvatarUrl && <AvatarImage src={currentAvatarUrl} alt={userName} />}
                <AvatarFallback>{initials}</AvatarFallback>
              </Avatar>
              <ChevronDown className="h-4 w-4 text-gray-500" />
            </button>
          </DropdownMenuTrigger>

          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <div className="flex flex-col gap-0.5">
                <span className="font-semibold text-gray-900 truncate">{userName || userEmail}</span>
                <span className="text-xs font-normal text-gray-500 truncate">{userEmail}</span>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />

            <DropdownMenuItem
              className="cursor-pointer"
              onSelect={() => setChangePasswordOpen(true)}
            >
              <KeyRound className="mr-2 h-4 w-4 text-gray-500" />
              Change Password
            </DropdownMenuItem>

            <DropdownMenuItem
              className="cursor-pointer"
              onSelect={() => setAvatarUploadOpen(true)}
            >
              <ImageIcon className="mr-2 h-4 w-4 text-gray-500" />
              Set Profile Picture
            </DropdownMenuItem>

            <DropdownMenuSeparator />

            <DropdownMenuItem
              className="cursor-pointer text-red-600 focus:text-red-600 focus:bg-red-50"
              onSelect={handleLogout}
            >
              <LogOut className="mr-2 h-4 w-4" />
              Logout
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </header>

      <ChangePasswordModal open={changePasswordOpen} onOpenChange={setChangePasswordOpen} />
      <AvatarUploadModal
        open={avatarUploadOpen}
        onOpenChange={setAvatarUploadOpen}
        userId={userId}
        onSuccess={(url) => setCurrentAvatarUrl(url)}
      />
    </>
  )
}

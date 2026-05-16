'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { createClient } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Eye, Pencil, ToggleLeft, ToggleRight, Mail, Trash2, Loader2 } from 'lucide-react'
import type { EmployeeListItem } from '@/types'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

interface EmployeeActionsProps {
  employee: EmployeeListItem
  onMutate: () => void
}

export function EmployeeActions({ employee, onMutate }: EmployeeActionsProps) {
  const router = useRouter()
  const supabase = createClient()
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isToggling, setIsToggling] = useState(false)
  const [isResending, setIsResending] = useState(false)

  const getToken = async () => {
    const { data } = await supabase.auth.getSession()
    return data.session?.access_token ?? ''
  }

  const handleToggleActive = async () => {
    setIsToggling(true)
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/api/v1/users/${employee.id}/disable/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
      })
      if (!res.ok) throw new Error()
      toast.success(employee.is_active ? 'Employee disabled.' : 'Employee enabled.')
      onMutate()
    } catch {
      toast.error('Failed to update employee status.')
    } finally {
      setIsToggling(false)
    }
  }

  const handleResendInvite = async () => {
    setIsResending(true)
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/api/v1/users/${employee.id}/resend-invite/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
      })
      if (!res.ok) throw new Error()
      toast.success('Invitation email resent.')
    } catch {
      toast.error('Failed to resend invitation.')
    } finally {
      setIsResending(false)
    }
  }

  const handleDelete = async () => {
    setIsDeleting(true)
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/api/v1/users/${employee.id}/`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error()
      toast.success(`${employee.full_name} has been removed.`)
      setDeleteOpen(false)
      onMutate()
    } catch {
      toast.error('Failed to delete employee.')
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <>
      <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
        <Button
          variant="ghost"
          size="icon"
          title="View Profile"
          aria-label="View employee profile"
          onClick={() => router.push(`/hr/employees/${employee.id}`)}
        >
          <Eye className="h-4 w-4 text-gray-500" />
        </Button>

        <Button
          variant="ghost"
          size="icon"
          title="Edit Profile"
          aria-label="Edit employee profile"
          onClick={() => router.push(`/hr/employees/${employee.id}?edit=true`)}
        >
          <Pencil className="h-4 w-4 text-gray-500" />
        </Button>

        <Button
          variant="ghost"
          size="icon"
          title={employee.is_active ? 'Disable employee' : 'Enable employee'}
          aria-label={employee.is_active ? 'Disable employee' : 'Enable employee'}
          disabled={isToggling}
          onClick={handleToggleActive}
        >
          {isToggling ? (
            <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
          ) : employee.is_active ? (
            <ToggleRight className="h-4 w-4 text-green-600" />
          ) : (
            <ToggleLeft className="h-4 w-4 text-gray-400" />
          )}
        </Button>

        <Button
          variant="ghost"
          size="icon"
          title="Resend invite email"
          aria-label="Resend invite email"
          disabled={isResending}
          onClick={handleResendInvite}
        >
          {isResending ? (
            <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
          ) : (
            <Mail className="h-4 w-4 text-gray-500" />
          )}
        </Button>

        <Button
          variant="ghost"
          size="icon"
          title="Delete employee"
          aria-label="Delete employee"
          onClick={() => setDeleteOpen(true)}
        >
          <Trash2 className="h-4 w-4 text-red-500" />
        </Button>
      </div>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Employee</DialogTitle>
            <DialogDescription>
              Are you sure you want to permanently delete{' '}
              <span className="font-semibold text-gray-900">{employee.full_name}</span>? This action
              cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)} disabled={isDeleting}>
              Cancel
            </Button>
            <Button
              className="bg-red-600 hover:bg-red-700 text-white"
              onClick={handleDelete}
              disabled={isDeleting}
            >
              {isDeleting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Deleting...
                </>
              ) : (
                'Delete'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

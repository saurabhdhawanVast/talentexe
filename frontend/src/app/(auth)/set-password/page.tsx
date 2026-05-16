'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { createClient } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Loader2, Lock } from 'lucide-react'

const schema = z
  .object({
    newPassword: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string().min(8, 'Password must be at least 8 characters'),
  })
  .refine((d) => d.newPassword === d.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })

type FormValues = z.infer<typeof schema>

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

export default function SetPasswordPage() {
  const router = useRouter()
  const supabase = createClient()
  const [isLoading, setIsLoading] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const onSubmit = async (values: FormValues) => {
    setIsLoading(true)
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession()

      if (!session) {
        toast.error('Session expired. Please log in again.')
        router.push('/login')
        return
      }

      const res = await fetch(`${API_BASE}/api/v1/auth/change-password/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ new_password: values.newPassword }),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        toast.error(body?.error ?? 'Failed to change password. Please try again.')
        return
      }

      // Re-fetch role after password change
      const meRes = await fetch(`${API_BASE}/api/v1/auth/me/`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      })

      if (meRes.ok) {
        const { data } = await meRes.json()
        toast.success('Password updated successfully!')
        if (data.role === 'hr') {
          router.push('/hr/dashboard')
        } else {
          router.push('/employee/profile')
        }
      } else {
        router.push('/login')
      }
    } catch {
      toast.error('An unexpected error occurred. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="inline-flex h-14 w-14 items-center justify-center rounded-full bg-indigo-100 mb-4">
            <Lock className="h-7 w-7 text-indigo-600" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Set Your New Password</h1>
          <p className="mt-2 text-sm text-gray-500">
            Your account requires a password change before continuing.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Create a new password</CardTitle>
            <CardDescription>Choose a strong password with at least 8 characters.</CardDescription>
          </CardHeader>

          <form onSubmit={handleSubmit(onSubmit)} noValidate>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="newPassword">New Password</Label>
                <Input
                  id="newPassword"
                  type="password"
                  autoComplete="new-password"
                  placeholder="At least 8 characters"
                  disabled={isLoading}
                  {...register('newPassword')}
                />
                {errors.newPassword && (
                  <p className="text-xs text-red-600">{errors.newPassword.message}</p>
                )}
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="confirmPassword">Confirm Password</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  autoComplete="new-password"
                  placeholder="Repeat your new password"
                  disabled={isLoading}
                  {...register('confirmPassword')}
                />
                {errors.confirmPassword && (
                  <p className="text-xs text-red-600">{errors.confirmPassword.message}</p>
                )}
              </div>
            </CardContent>

            <CardFooter>
              <Button type="submit" className="w-full bg-indigo-600 hover:bg-indigo-700" disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  'Set New Password'
                )}
              </Button>
            </CardFooter>
          </form>
        </Card>
      </div>
    </div>
  )
}

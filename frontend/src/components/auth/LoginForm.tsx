'use client'

import { useState, type FormEvent } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { createClient } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from '@/components/ui/card'

interface MeResponse {
  data: {
    role: 'hr' | 'employee' | string
    must_change_password: boolean
  }
}

export function LoginForm() {
  const router = useRouter()
  const supabase = createClient()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError(null)
    setIsLoading(true)

    try {
      const { data, error: authError } = await supabase.auth.signInWithPassword({
        email,
        password,
      })

      if (authError) {
        const msg = authError.message.toLowerCase()
        if (msg.includes('rate limit') || msg.includes('too many')) {
          setError('Too many login attempts. Please wait a few minutes and try again.')
        } else {
          setError(authError.message)
        }
        return
      }

      if (!data.session) {
        setError('Sign-in failed. Please try again.')
        return
      }

      const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'
      const res = await fetch(`${apiBase}/api/v1/auth/me/`, {
        headers: {
          Authorization: `Bearer ${data.session.access_token}`,
          'Content-Type': 'application/json',
        },
      })

      if (!res.ok) {
        setError('Unable to load your profile. Please contact support.')
        return
      }

      const { data: profile }: MeResponse = await res.json()

      if (profile.must_change_password) {
        router.push('/set-password')
        return
      }

      if (profile.role === 'hr') {
        router.push('/hr/dashboard')
      } else if (profile.role === 'employee') {
        router.push('/employee/profile')
      } else {
        setError('Your account does not have an assigned role. Please contact HR.')
      }
    } catch {
      setError('An unexpected error occurred. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">TalentExe</h1>
          <p className="mt-2 text-sm text-gray-500">Talent management, simplified</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Sign in to your account</CardTitle>
            <CardDescription>
              Enter your email and password to continue
            </CardDescription>
          </CardHeader>

          <form onSubmit={handleSubmit} noValidate>
            <CardContent className="space-y-4">
              {error && (
                <div
                  role="alert"
                  className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700"
                >
                  {error}
                </div>
              )}

              <div className="space-y-1.5">
                <Label htmlFor="email">Email address</Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isLoading}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  placeholder="Your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                />
              </div>
            </CardContent>

            <CardFooter className="flex-col gap-3">
              <Button
                type="submit"
                className="w-full bg-indigo-600 hover:bg-indigo-700"
                disabled={isLoading || !email || !password}
                aria-busy={isLoading}
              >
                {isLoading ? 'Signing in...' : 'Sign in'}
              </Button>
              <Link
                href="/forgot-password"
                className="text-sm text-indigo-600 hover:text-indigo-700"
              >
                Forgot your password?
              </Link>
            </CardFooter>
          </form>
        </Card>
      </div>
    </div>
  )
}

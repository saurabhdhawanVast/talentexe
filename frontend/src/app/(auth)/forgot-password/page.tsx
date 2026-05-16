'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Loader2, Mail, CheckCircle } from 'lucide-react'

const schema = z.object({
  email: z.string().email('Please enter a valid email address'),
})

type FormValues = z.infer<typeof schema>

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

export default function ForgotPasswordPage() {
  const [submitted, setSubmitted] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const onSubmit = async (values: FormValues) => {
    setIsLoading(true)
    setServerError(null)
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/forgot-password/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: values.email }),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        setServerError(body?.error ?? 'Something went wrong. Please try again.')
        return
      }

      setSubmitted(true)
    } catch {
      setServerError('An unexpected error occurred. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Talent.exe</h1>
          <p className="mt-2 text-sm text-gray-500">Talent management, simplified</p>
        </div>

        <Card>
          {submitted ? (
            <CardContent className="pt-6 pb-6 text-center space-y-4">
              <div className="flex justify-center">
                <CheckCircle className="h-12 w-12 text-green-500" />
              </div>
              <h2 className="text-lg font-semibold text-gray-900">Check your email</h2>
              <p className="text-sm text-gray-500">
                We&apos;ve sent a password reset link to your email address. Please check your inbox (and spam folder).
              </p>
              <Link
                href="/login"
                className="inline-block mt-2 text-sm text-indigo-600 hover:text-indigo-700 font-medium"
              >
                Back to sign in
              </Link>
            </CardContent>
          ) : (
            <>
              <CardHeader>
                <div className="flex items-center gap-3 mb-1">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-100">
                    <Mail className="h-5 w-5 text-indigo-600" />
                  </div>
                  <CardTitle>Forgot your password?</CardTitle>
                </div>
                <CardDescription>
                  Enter your email address and we&apos;ll send you a link to reset your password.
                </CardDescription>
              </CardHeader>

              <form onSubmit={handleSubmit(onSubmit)} noValidate>
                <CardContent className="space-y-4">
                  {serverError && (
                    <div
                      role="alert"
                      className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700"
                    >
                      {serverError}
                    </div>
                  )}
                  <div className="space-y-1.5">
                    <Label htmlFor="email">Email address</Label>
                    <Input
                      id="email"
                      type="email"
                      autoComplete="email"
                      placeholder="you@example.com"
                      disabled={isLoading}
                      {...register('email')}
                    />
                    {errors.email && (
                      <p className="text-xs text-red-600">{errors.email.message}</p>
                    )}
                  </div>
                </CardContent>

                <CardFooter className="flex-col gap-3">
                  <Button
                    type="submit"
                    className="w-full bg-indigo-600 hover:bg-indigo-700"
                    disabled={isLoading}
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Sending...
                      </>
                    ) : (
                      'Send Reset Link'
                    )}
                  </Button>
                  <Link
                    href="/login"
                    className="text-sm text-gray-500 hover:text-gray-700"
                  >
                    Back to sign in
                  </Link>
                </CardFooter>
              </form>
            </>
          )}
        </Card>
      </div>
    </div>
  )
}

'use client'

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { toast } from 'sonner'
import { createClient } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { ArrowLeft, Loader2 } from 'lucide-react'

const schema = z.object({
  full_name: z.string().min(1, 'Full name is required'),
  email: z.string().email('Valid email is required'),
  phone: z.string().optional(),
  designation: z.string().min(1, 'Designation is required'),
  department: z.string().min(1, 'Department is required'),
  experience_years: z
    .string()
    .min(1, 'Experience is required')
    .refine((v) => !isNaN(Number(v)) && Number(v) >= 0, 'Enter a valid number (0 or more)'),
  location: z.string().optional(),
})

type FormValues = z.infer<typeof schema>

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

export default function NewEmployeePage() {
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
      const { data: sessionData } = await supabase.auth.getSession()
      if (!sessionData.session) {
        toast.error('Session expired. Please log in again.')
        return
      }

      const payload = {
        full_name: values.full_name,
        email: values.email,
        role: 'employee',
        phone: values.phone || undefined,
        designation: values.designation,
        department: values.department,
        experience_years: values.experience_years ? parseFloat(values.experience_years) : undefined,
        location: values.location || undefined,
      }

      const res = await fetch(`${API_BASE}/api/v1/users/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${sessionData.session.access_token}`,
        },
        body: JSON.stringify(payload),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        toast.error(body?.error ?? `Failed to create employee (${res.status})`)
        return
      }

      toast.success('Employee added and welcome email sent.')
      router.push('/hr/employees')
    } catch {
      toast.error('An unexpected error occurred. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <section aria-labelledby="new-employee-heading">
      <div className="mb-6 flex items-center gap-3">
        <Link href="/hr/employees">
          <Button variant="ghost" size="icon" aria-label="Back to employee list">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 id="new-employee-heading" className="text-2xl font-semibold text-gray-900">
            Add New Employee
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Create an employee account. A welcome email will be sent automatically.
          </p>
        </div>
      </div>

      <div className="max-w-2xl">
        <Card>
          <CardHeader>
            <CardTitle>Employee Details</CardTitle>
            <CardDescription>Fields marked with * are required.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label htmlFor="full_name">Full Name <span className="text-red-500">*</span></Label>
                  <Input id="full_name" placeholder="Jane Doe" disabled={isLoading} {...register('full_name')} />
                  {errors.full_name && <p className="text-xs text-red-600">{errors.full_name.message}</p>}
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="email">Email Address <span className="text-red-500">*</span></Label>
                  <Input id="email" type="email" placeholder="jane@company.com" disabled={isLoading} {...register('email')} />
                  {errors.email && <p className="text-xs text-red-600">{errors.email.message}</p>}
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="phone">Phone</Label>
                  <Input id="phone" type="tel" placeholder="+1-555-0100" disabled={isLoading} {...register('phone')} />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="designation">Designation <span className="text-red-500">*</span></Label>
                  <Input id="designation" placeholder="e.g. Software Engineer" disabled={isLoading} {...register('designation')} />
                  {errors.designation && <p className="text-xs text-red-600">{errors.designation.message}</p>}
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="department">Department <span className="text-red-500">*</span></Label>
                  <Input id="department" placeholder="e.g. Engineering" disabled={isLoading} {...register('department')} />
                  {errors.department && <p className="text-xs text-red-600">{errors.department.message}</p>}
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="experience_years">Experience (Years) <span className="text-red-500">*</span></Label>
                  <Input id="experience_years" type="number" min={0} placeholder="0" disabled={isLoading} {...register('experience_years')} />
                  {errors.experience_years && <p className="text-xs text-red-600">{errors.experience_years.message}</p>}
                </div>

                <div className="space-y-1.5 sm:col-span-2">
                  <Label htmlFor="location">Location</Label>
                  <Input id="location" placeholder="e.g. New York, NY" disabled={isLoading} {...register('location')} />
                </div>
              </div>

              <div className="flex items-center gap-3 pt-2">
                <Button type="submit" className="bg-indigo-600 hover:bg-indigo-700" disabled={isLoading}>
                  {isLoading ? (
                    <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Creating...</>
                  ) : (
                    'Create Employee'
                  )}
                </Button>
                <Link href="/hr/employees">
                  <Button type="button" variant="outline" disabled={isLoading}>Cancel</Button>
                </Link>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </section>
  )
}

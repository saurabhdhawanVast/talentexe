import type { Metadata } from 'next'
import { LoginForm } from '@/components/auth/LoginForm'

export const metadata: Metadata = {
  title: 'Sign In | TalentExe',
  description: 'Sign in to your TalentExe account',
}

export default function LoginPage() {
  return <LoginForm />
}

import { redirect } from 'next/navigation'

// Redirect employee dashboard → profile (the main employee page)
export default function EmployeeDashboardPage() {
  redirect('/employee/profile')
}

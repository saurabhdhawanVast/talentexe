'use client'

import { useRouter } from 'next/navigation'
import { ProfileStatusBadge } from '@/components/profile/ProfileStatusBadge'
import { EmployeeActions } from './EmployeeActions'
import type { EmployeeListItem } from '@/types'

interface EmployeeTableProps {
  employees: EmployeeListItem[]
  onMutate: () => void
}

export function EmployeeTable({ employees, onMutate }: EmployeeTableProps) {
  const router = useRouter()

  if (employees.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <p className="text-gray-400 text-sm">No employees found matching your filters.</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-gray-200" role="table">
        <thead className="bg-gray-50">
          <tr>
            {['Name', 'Designation', 'Department', 'Experience', 'Top Skills', 'Status', 'Actions'].map(
              (col) => (
                <th
                  key={col}
                  scope="col"
                  className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider"
                >
                  {col}
                </th>
              )
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {employees.map((emp) => (
            <tr
              key={emp.id}
              className="hover:bg-gray-50 cursor-pointer transition-colors"
              onClick={() => router.push(`/hr/employees/${emp.id}`)}
            >
              <td className="px-4 py-3">
                <div>
                  <p className="text-sm font-medium text-gray-900">{emp.full_name}</p>
                  <p className="text-xs text-gray-500">{emp.email}</p>
                </div>
              </td>
              <td className="px-4 py-3 text-sm text-gray-700">{emp.designation || '—'}</td>
              <td className="px-4 py-3 text-sm text-gray-700">{emp.department || '—'}</td>
              <td className="px-4 py-3 text-sm text-gray-700">
                {emp.experience_years != null ? `${emp.experience_years} yr${emp.experience_years !== 1 ? 's' : ''}` : '—'}
              </td>
              <td className="px-4 py-3">
                <div className="flex flex-wrap gap-1 max-w-[200px]">
                  {(emp.skills ?? []).slice(0, 3).map((skill) => (
                    <span
                      key={skill.name}
                      className="inline-flex items-center rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700"
                    >
                      {skill.name}
                    </span>
                  ))}
                  {(emp.skills ?? []).length > 3 && (
                    <span className="text-xs text-gray-400">+{(emp.skills ?? []).length - 3}</span>
                  )}
                </div>
              </td>
              <td className="px-4 py-3">
                <ProfileStatusBadge status={emp.status} />
              </td>
              <td className="px-4 py-3">
                <EmployeeActions employee={emp} onMutate={onMutate} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

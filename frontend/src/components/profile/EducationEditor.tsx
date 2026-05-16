'use client'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Plus, Trash2 } from 'lucide-react'
import type { EducationEntry } from '@/types'

interface EducationEditorProps {
  education: EducationEntry[]
  isEditing: boolean
  onChange?: (education: EducationEntry[]) => void
}

const emptyEntry = (): EducationEntry => ({
  degree: '',
  institution: '',
  graduation_year: new Date().getFullYear(),
})

export function EducationEditor({ education, isEditing, onChange }: EducationEditorProps) {
  const handleAdd = () => onChange?.([...education, emptyEntry()])
  const handleRemove = (i: number) => onChange?.(education.filter((_, idx) => idx !== i))
  const handleChange = (i: number, field: keyof EducationEntry, value: string | number) => {
    onChange?.(education.map((e, idx) => (idx === i ? { ...e, [field]: value } : e)))
  }

  if (!isEditing) {
    if (education.length === 0) return <p className="text-sm text-gray-400">No education added.</p>
    return (
      <div className="space-y-3">
        {education.map((edu, i) => (
          <div key={i} className="flex items-start justify-between">
            <div>
              <p className="font-semibold text-gray-900">{edu.degree}</p>
              <p className="text-sm text-gray-600">{edu.institution}</p>
            </div>
            <span className="text-sm text-gray-500 shrink-0">{edu.graduation_year}</span>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {education.map((edu, i) => (
        <div key={i} className="rounded-lg border border-gray-200 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">Education {i + 1}</span>
            <Button type="button" variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleRemove(i)} aria-label="Remove education entry">
              <Trash2 className="h-3.5 w-3.5 text-red-500" />
            </Button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="space-y-1 sm:col-span-2">
              <Label className="text-xs">Degree</Label>
              <Input value={edu.degree} onChange={(e) => handleChange(i, 'degree', e.target.value)} placeholder="B.S. Computer Science" />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Graduation Year</Label>
              <Input type="number" value={edu.graduation_year} onChange={(e) => handleChange(i, 'graduation_year', Number(e.target.value))} placeholder="2020" min={1950} max={2040} />
            </div>
            <div className="space-y-1 sm:col-span-3">
              <Label className="text-xs">Institution</Label>
              <Input value={edu.institution} onChange={(e) => handleChange(i, 'institution', e.target.value)} placeholder="MIT" />
            </div>
          </div>
        </div>
      ))}
      <Button type="button" variant="outline" size="sm" className="gap-1" onClick={handleAdd}>
        <Plus className="h-3.5 w-3.5" /> Add Education
      </Button>
    </div>
  )
}

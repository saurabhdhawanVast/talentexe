'use client'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Plus, Trash2 } from 'lucide-react'
import { format } from 'date-fns'
import type { ExperienceEntry } from '@/types'

interface ExperienceEditorProps {
  experience: ExperienceEntry[]
  isEditing: boolean
  onChange?: (experience: ExperienceEntry[]) => void
}

const emptyEntry = (): ExperienceEntry => ({
  company: '',
  role: '',
  start_date: '',
  end_date: null,
  description: '',
})

function formatDateSafe(d: string | null): string {
  if (!d) return 'Present'
  try { return format(new Date(d), 'MMM yyyy') } catch { return d }
}

export function ExperienceEditor({ experience, isEditing, onChange }: ExperienceEditorProps) {
  const handleAdd = () => onChange?.([...experience, emptyEntry()])
  const handleRemove = (i: number) => onChange?.(experience.filter((_, idx) => idx !== i))
  const handleChange = (i: number, field: keyof ExperienceEntry, value: string | null) => {
    onChange?.(experience.map((e, idx) => (idx === i ? { ...e, [field]: value } : e)))
  }

  if (!isEditing) {
    if (experience.length === 0) return <p className="text-sm text-gray-400">No experience added.</p>
    return (
      <div className="space-y-4">
        {experience.map((exp, i) => (
          <div key={i} className="border-l-2 border-indigo-200 pl-4">
            <p className="font-semibold text-gray-900">{exp.role}</p>
            <p className="text-sm text-indigo-600">{exp.company}</p>
            <p className="text-xs text-gray-500 mt-0.5">
              {formatDateSafe(exp.start_date)} – {formatDateSafe(exp.end_date)}
            </p>
            {exp.description && <p className="mt-2 text-sm text-gray-600">{exp.description}</p>}
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {experience.map((exp, i) => (
        <div key={i} className="rounded-lg border border-gray-200 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">Experience {i + 1}</span>
            <Button type="button" variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleRemove(i)} aria-label="Remove entry">
              <Trash2 className="h-3.5 w-3.5 text-red-500" />
            </Button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Company</Label>
              <Input value={exp.company} onChange={(e) => handleChange(i, 'company', e.target.value)} placeholder="Acme Corp" />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Role / Title</Label>
              <Input value={exp.role} onChange={(e) => handleChange(i, 'role', e.target.value)} placeholder="Senior Engineer" />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Start Date</Label>
              <Input type="date" value={exp.start_date} onChange={(e) => handleChange(i, 'start_date', e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">End Date (leave blank if current)</Label>
              <Input type="date" value={exp.end_date ?? ''} onChange={(e) => handleChange(i, 'end_date', e.target.value || null)} />
            </div>
            <div className="space-y-1 sm:col-span-2">
              <Label className="text-xs">Description</Label>
              <Textarea value={exp.description} onChange={(e) => handleChange(i, 'description', e.target.value)} placeholder="Key responsibilities and achievements..." rows={3} />
            </div>
          </div>
        </div>
      ))}
      <Button type="button" variant="outline" size="sm" className="gap-1" onClick={handleAdd}>
        <Plus className="h-3.5 w-3.5" /> Add Experience
      </Button>
    </div>
  )
}

'use client'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Plus, Trash2, X } from 'lucide-react'
import type { ProjectEntry } from '@/types'

interface ProjectsEditorProps {
  projects: ProjectEntry[]
  isEditing: boolean
  onChange?: (projects: ProjectEntry[]) => void
}

const emptyEntry = (): ProjectEntry => ({
  name: '',
  description: '',
  tech_stack: [],
  duration: '',
})

export function ProjectsEditor({ projects, isEditing, onChange }: ProjectsEditorProps) {
  const handleAdd = () => onChange?.([...projects, emptyEntry()])
  const handleRemove = (i: number) => onChange?.(projects.filter((_, idx) => idx !== i))
  const handleChange = (i: number, field: keyof ProjectEntry, value: string | string[]) => {
    onChange?.(projects.map((p, idx) => (idx === i ? { ...p, [field]: value } : p)))
  }

  const handleAddTech = (i: number, tech: string) => {
    if (!tech.trim()) return
    const updated = [...(projects[i].tech_stack ?? []), tech.trim()]
    handleChange(i, 'tech_stack', updated)
  }

  const handleRemoveTech = (i: number, techIdx: number) => {
    handleChange(i, 'tech_stack', projects[i].tech_stack.filter((_, ti) => ti !== techIdx))
  }

  if (!isEditing) {
    if (projects.length === 0) return <p className="text-sm text-gray-400">No projects added.</p>
    return (
      <div className="space-y-4">
        {projects.map((proj, i) => (
          <div key={i} className="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <div className="flex items-start justify-between">
              <p className="font-semibold text-gray-900">{proj.name}</p>
              {proj.duration && <span className="text-xs text-gray-500">{proj.duration}</span>}
            </div>
            {proj.description && <p className="mt-1 text-sm text-gray-600">{proj.description}</p>}
            {proj.tech_stack?.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {proj.tech_stack.map((t) => (
                  <span key={t} className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">{t}</span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {projects.map((proj, i) => (
        <div key={i} className="rounded-lg border border-gray-200 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">Project {i + 1}</span>
            <Button type="button" variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleRemove(i)} aria-label="Remove project">
              <Trash2 className="h-3.5 w-3.5 text-red-500" />
            </Button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Project Name</Label>
              <Input value={proj.name} onChange={(e) => handleChange(i, 'name', e.target.value)} placeholder="My Awesome Project" />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Duration</Label>
              <Input value={proj.duration} onChange={(e) => handleChange(i, 'duration', e.target.value)} placeholder="e.g. 6 months" />
            </div>
            <div className="space-y-1 sm:col-span-2">
              <Label className="text-xs">Description</Label>
              <Textarea value={proj.description} onChange={(e) => handleChange(i, 'description', e.target.value)} placeholder="What the project does, your role, and impact..." rows={3} />
            </div>
            <div className="space-y-1 sm:col-span-2">
              <Label className="text-xs">Tech Stack</Label>
              <div className="flex flex-wrap gap-1 mb-1">
                {proj.tech_stack?.map((t, ti) => (
                  <span key={ti} className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
                    {t}
                    <button type="button" onClick={() => handleRemoveTech(i, ti)} className="ml-0.5 hover:text-red-600" aria-label={`Remove ${t}`}>
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex gap-2">
                <Input
                  placeholder="Add technology (press Enter)"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      handleAddTech(i, (e.target as HTMLInputElement).value)
                      ;(e.target as HTMLInputElement).value = ''
                    }
                  }}
                />
              </div>
            </div>
          </div>
        </div>
      ))}
      <Button type="button" variant="outline" size="sm" className="gap-1" onClick={handleAdd}>
        <Plus className="h-3.5 w-3.5" /> Add Project
      </Button>
    </div>
  )
}

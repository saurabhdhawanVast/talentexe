'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Plus } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Skill, SkillProficiency } from '@/types'

const proficiencyColors: Record<SkillProficiency, string> = {
  Beginner: 'bg-gray-100 text-gray-700',
  Intermediate: 'bg-blue-100 text-blue-700',
  Expert: 'bg-green-100 text-green-700',
}

interface SkillsEditorProps {
  skills: Skill[]
  isEditing: boolean
  onChange?: (skills: Skill[]) => void
}

export function SkillsEditor({ skills, isEditing, onChange }: SkillsEditorProps) {
  const [newName, setNewName] = useState('')
  const [newProficiency, setNewProficiency] = useState<SkillProficiency>('Intermediate')
  const [newYears, setNewYears] = useState<number>(1)

  const handleAdd = () => {
    if (!newName.trim()) return
    const updated: Skill[] = [
      ...skills,
      { name: newName.trim(), proficiency: newProficiency, years: newYears },
    ]
    onChange?.(updated)
    setNewName('')
    setNewYears(1)
  }

  const handleRemove = (index: number) => {
    onChange?.(skills.filter((_, i) => i !== index))
  }

  if (!isEditing) {
    if (skills.length === 0) {
      return <p className="text-sm text-gray-400">No skills added yet.</p>
    }
    return (
      <div className="grid grid-cols-3 gap-2">
        {skills.map((skill, i) => (
          <div key={i} className="flex flex-col gap-1 rounded-lg border border-gray-200 bg-white px-3 py-2 min-w-0">
            <span className="text-sm font-medium text-gray-800 truncate" title={skill.name}>{skill.name}</span>
            <span className={cn('self-start rounded-full px-1.5 py-0.5 text-xs font-semibold', proficiencyColors[skill.proficiency])}>
              {skill.proficiency}
            </span>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Existing skills */}
      {skills.length > 0 && (
        <div className="grid grid-cols-3 gap-2">
          {skills.map((skill, i) => (
            <div key={i} className="relative flex flex-col gap-1 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 min-w-0">
              <button
                type="button"
                onClick={() => handleRemove(i)}
                aria-label={`Remove ${skill.name}`}
                className="absolute top-1 right-1 flex h-4 w-4 items-center justify-center rounded-full bg-gray-200 text-gray-500 hover:bg-red-100 hover:text-red-600 text-[10px] leading-none font-bold"
              >
                ×
              </button>
              <span className="text-sm font-medium text-gray-800 truncate pr-5" title={skill.name}>{skill.name}</span>
              <span className={cn('self-start rounded-full px-1.5 py-0.5 text-xs font-semibold', proficiencyColors[skill.proficiency])}>
                {skill.proficiency}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Add new skill */}
      <div className="flex flex-wrap items-end gap-2 rounded-lg border border-dashed border-gray-300 p-3">
        <div className="flex-1 min-w-[140px] space-y-1">
          <Label className="text-xs">Skill Name</Label>
          <Input
            placeholder="e.g. TypeScript"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAdd())}
          />
        </div>
        <div className="w-36 space-y-1">
          <Label className="text-xs">Proficiency</Label>
          <Select value={newProficiency} onValueChange={(v) => setNewProficiency(v as SkillProficiency)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="Beginner">Beginner</SelectItem>
              <SelectItem value="Intermediate">Intermediate</SelectItem>
              <SelectItem value="Expert">Expert</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="w-20 space-y-1">
          <Label className="text-xs">Years</Label>
          <Input
            type="number"
            min={0}
            max={50}
            value={newYears}
            onChange={(e) => setNewYears(Number(e.target.value))}
          />
        </div>
        <Button
          type="button"
          size="sm"
          className="bg-indigo-600 hover:bg-indigo-700 gap-1"
          onClick={handleAdd}
          disabled={!newName.trim()}
        >
          <Plus className="h-3.5 w-3.5" />
          Add
        </Button>
      </div>
    </div>
  )
}

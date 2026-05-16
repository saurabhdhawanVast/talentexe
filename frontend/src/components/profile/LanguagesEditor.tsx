'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Plus, Trash2 } from 'lucide-react'
import type { Language, LanguageProficiency } from '@/types'

interface LanguagesEditorProps {
  languages: Language[]
  isEditing: boolean
  onChange?: (languages: Language[]) => void
}

const PROFICIENCIES: LanguageProficiency[] = ['Native', 'Fluent', 'Intermediate', 'Basic']

export function LanguagesEditor({ languages, isEditing, onChange }: LanguagesEditorProps) {
  const [newName, setNewName] = useState('')
  const [newProficiency, setNewProficiency] = useState<LanguageProficiency>('Fluent')

  const handleAdd = () => {
    if (!newName.trim()) return
    onChange?.([...languages, { name: newName.trim(), proficiency: newProficiency }])
    setNewName('')
  }

  const handleRemove = (i: number) => onChange?.(languages.filter((_, idx) => idx !== i))

  if (!isEditing) {
    if (languages.length === 0) return <p className="text-sm text-gray-400">No languages added.</p>
    return (
      <div className="flex flex-wrap gap-2">
        {languages.map((lang, i) => (
          <div key={i} className="flex items-center gap-1.5 rounded-full border border-gray-200 bg-white px-3 py-1">
            <span className="text-sm font-medium text-gray-800">{lang.name}</span>
            <span className="text-xs text-gray-400">{lang.proficiency}</span>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {languages.length > 0 && (
        <div className="space-y-2">
          {languages.map((lang, i) => (
            <div key={i} className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
              <span className="flex-1 text-sm font-medium text-gray-800">{lang.name}</span>
              <span className="text-xs text-gray-500">{lang.proficiency}</span>
              <Button type="button" variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleRemove(i)} aria-label={`Remove ${lang.name}`}>
                <Trash2 className="h-3.5 w-3.5 text-red-500" />
              </Button>
            </div>
          ))}
        </div>
      )}

      <div className="flex flex-wrap items-end gap-2 rounded-lg border border-dashed border-gray-300 p-3">
        <div className="flex-1 min-w-[120px] space-y-1">
          <Label className="text-xs">Language</Label>
          <Input placeholder="e.g. Spanish" value={newName} onChange={(e) => setNewName(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAdd())} />
        </div>
        <div className="w-36 space-y-1">
          <Label className="text-xs">Proficiency</Label>
          <Select value={newProficiency} onValueChange={(v) => setNewProficiency(v as LanguageProficiency)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {PROFICIENCIES.map((p) => <SelectItem key={p} value={p}>{p}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <Button type="button" size="sm" className="bg-indigo-600 hover:bg-indigo-700 gap-1" onClick={handleAdd} disabled={!newName.trim()}>
          <Plus className="h-3.5 w-3.5" /> Add
        </Button>
      </div>
    </div>
  )
}

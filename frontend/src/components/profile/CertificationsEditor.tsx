'use client'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Plus, Trash2 } from 'lucide-react'
import type { Certification } from '@/types'
import { format } from 'date-fns'

interface CertificationsEditorProps {
  certifications: Certification[]
  isEditing: boolean
  onChange?: (certifications: Certification[]) => void
}

const emptyEntry = (): Certification => ({
  name: '',
  issuer: '',
  issued_date: '',
  expiry_date: null,
})

export function CertificationsEditor({ certifications, isEditing, onChange }: CertificationsEditorProps) {
  const handleAdd = () => onChange?.([...certifications, emptyEntry()])

  const handleRemove = (i: number) => onChange?.(certifications.filter((_, idx) => idx !== i))

  const handleChange = (i: number, field: keyof Certification, value: string | null) => {
    const updated = certifications.map((c, idx) => (idx === i ? { ...c, [field]: value } : c))
    onChange?.(updated)
  }

  if (!isEditing) {
    if (certifications.length === 0) {
      return <p className="text-sm text-gray-400">No certifications added.</p>
    }
    return (
      <div className="space-y-3">
        {certifications.map((cert, i) => (
          <div key={i} className="rounded-lg border border-gray-200 bg-gray-50 p-3">
            <p className="font-medium text-gray-900">{cert.name}</p>
            <p className="text-sm text-gray-600">{cert.issuer}</p>
            <div className="mt-1 flex gap-3 text-xs text-gray-500">
              {cert.issued_date && (
                <span>Issued: {formatDateSafe(cert.issued_date)}</span>
              )}
              {cert.expiry_date && (
                <span>Expires: {formatDateSafe(cert.expiry_date)}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {certifications.map((cert, i) => (
        <div key={i} className="rounded-lg border border-gray-200 p-4 space-y-3">
          <div className="flex items-start justify-between">
            <span className="text-sm font-medium text-gray-700">Certification {i + 1}</span>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => handleRemove(i)}
              aria-label="Remove certification"
            >
              <Trash2 className="h-3.5 w-3.5 text-red-500" />
            </Button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Certification Name</Label>
              <Input
                value={cert.name}
                onChange={(e) => handleChange(i, 'name', e.target.value)}
                placeholder="AWS Certified Developer"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Issuer</Label>
              <Input
                value={cert.issuer}
                onChange={(e) => handleChange(i, 'issuer', e.target.value)}
                placeholder="Amazon Web Services"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Issued Date</Label>
              <Input
                type="date"
                value={cert.issued_date}
                onChange={(e) => handleChange(i, 'issued_date', e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Expiry Date (optional)</Label>
              <Input
                type="date"
                value={cert.expiry_date ?? ''}
                onChange={(e) => handleChange(i, 'expiry_date', e.target.value || null)}
              />
            </div>
          </div>
        </div>
      ))}

      <Button
        type="button"
        variant="outline"
        size="sm"
        className="gap-1"
        onClick={handleAdd}
      >
        <Plus className="h-3.5 w-3.5" />
        Add Certification
      </Button>
    </div>
  )
}

function formatDateSafe(dateStr: string): string {
  try {
    return format(new Date(dateStr), 'MMM yyyy')
  } catch {
    return dateStr
  }
}

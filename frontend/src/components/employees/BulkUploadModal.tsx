'use client'

import { useState, useRef } from 'react'
import { toast } from 'sonner'
import { createClient } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Loader2, Upload, FileIcon, Download } from 'lucide-react'
import type { BulkUploadResult } from '@/types'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

const TEMPLATE_JSON = JSON.stringify(
  [
    {
      full_name: 'Jane Doe',
      email: 'jane.doe@example.com',
      phone: '+1-555-0100',
      designation: 'Software Engineer',
      department: 'Engineering',
      experience_years: 3,
      location: 'New York, NY',
    },
  ],
  null,
  2
)

interface BulkUploadModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

export function BulkUploadModal({ open, onOpenChange, onSuccess }: BulkUploadModalProps) {
  const supabase = createClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<BulkUploadResult | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setSelectedFile(file)
    setResult(null)
  }

  const handleUpload = async () => {
    if (!selectedFile) return
    setIsLoading(true)

    try {
      const { data: sessionData } = await supabase.auth.getSession()
      if (!sessionData.session) {
        toast.error('Session expired. Please log in again.')
        return
      }

      const formData = new FormData()
      formData.append('file', selectedFile)

      const res = await fetch(`${API_BASE}/api/v1/users/bulk-upload/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${sessionData.session.access_token}`,
          // Do NOT set Content-Type — let browser set it with multipart boundary
        },
        body: formData,
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        toast.error(body?.error ?? `Upload failed (${res.status})`)
        return
      }

      const body = await res.json()
      setResult(body.data)
      toast.success(`Bulk upload complete: ${body.data.created} employees created.`)
      onSuccess?.()
    } catch {
      toast.error('An unexpected error occurred during upload.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleClose = () => {
    setSelectedFile(null)
    setResult(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
    onOpenChange(false)
  }

  const downloadTemplate = () => {
    const blob = new Blob([TEMPLATE_JSON], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'employee_template.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && handleClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Bulk Upload Employees</DialogTitle>
          <DialogDescription>
            Upload a JSON or Excel file containing employee records.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <button
            type="button"
            onClick={downloadTemplate}
            className="flex items-center gap-2 text-sm text-indigo-600 hover:text-indigo-700 font-medium"
          >
            <Download className="h-4 w-4" />
            Download JSON Template
          </button>

          <div
            className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 p-8 cursor-pointer hover:border-indigo-400 hover:bg-indigo-50 transition-colors"
            onClick={() => fileInputRef.current?.click()}
            onKeyDown={(e) => e.key === 'Enter' && fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
            aria-label="Click to select a file"
          >
            <FileIcon className="h-10 w-10 text-gray-300 mb-3" />
            <p className="text-sm text-gray-500">Click to select a file</p>
            <p className="text-xs text-gray-400 mt-1">.json, .xlsx, .xls accepted</p>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept=".json,.xlsx,.xls"
            className="hidden"
            onChange={handleFileChange}
          />

          {selectedFile && (
            <p className="text-sm text-gray-600">
              Selected: <span className="font-medium">{selectedFile.name}</span>
            </p>
          )}

          {/* Result summary */}
          {result && (
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-2">
              <p className="text-sm font-semibold text-gray-900">Upload Results</p>
              <div className="flex gap-4 text-sm">
                <span className="text-green-700">
                  Created: <span className="font-semibold">{result.created}</span>
                </span>
                <span className="text-amber-700">
                  Skipped: <span className="font-semibold">{result.skipped}</span>
                </span>
              </div>
              {result.errors.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-red-700 mb-1">Errors:</p>
                  <ul className="space-y-1 max-h-32 overflow-y-auto">
                    {result.errors.map((err, i) => (
                      <li key={i} className="text-xs text-red-600">
                        {err}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={handleClose} disabled={isLoading}>
            {result ? 'Close' : 'Cancel'}
          </Button>
          {!result && (
            <Button
              type="button"
              className="bg-indigo-600 hover:bg-indigo-700"
              disabled={!selectedFile || isLoading}
              onClick={handleUpload}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-4 w-4" />
                  Upload
                </>
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

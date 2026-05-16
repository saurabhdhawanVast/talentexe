'use client'

import { useRef, useState } from 'react'
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
import { FileText, Download, Upload, Loader2, Trash2 } from 'lucide-react'
import { format } from 'date-fns'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'
const MAX_SIZE_BYTES = 10 * 1024 * 1024 // 10MB

interface ResumeUploadProps {
  profileId: string
  fileName: string | null
  uploadedAt: string | null
  onUploadSuccess?: () => void
}

export function ResumeUpload({ profileId, fileName, uploadedAt, onUploadSuccess }: ResumeUploadProps) {
  const supabase = createClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isDownloading, setIsDownloading] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [isExtracting, setIsExtracting] = useState(false)
  const [isRemoving, setIsRemoving] = useState(false)
  const [showRemoveDialog, setShowRemoveDialog] = useState(false)

  const handleDownload = async () => {
    setIsDownloading(true)
    try {
      const { data: sessionData } = await supabase.auth.getSession()
      if (!sessionData.session) {
        toast.error('Session expired.')
        return
      }

      const res = await fetch(`${API_BASE}/api/v1/profiles/${profileId}/resume/`, {
        headers: { Authorization: `Bearer ${sessionData.session.access_token}` },
      })

      if (!res.ok) throw new Error()

      const body = await res.json()
      const url = body.data?.url
      if (url) {
        window.open(url, '_blank', 'noopener,noreferrer')
      }
    } catch {
      toast.error('Failed to retrieve resume download link.')
    } finally {
      setIsDownloading(false)
    }
  }

  const handleRemoveConfirm = async () => {
    setIsRemoving(true)
    try {
      const { data: sessionData } = await supabase.auth.getSession()
      if (!sessionData.session) {
        toast.error('Session expired.')
        return
      }

      const res = await fetch(`${API_BASE}/api/v1/profiles/${profileId}/resume/`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${sessionData.session.access_token}` },
      })

      if (!res.ok) throw new Error()
      toast.success('Resume removed.')
      setShowRemoveDialog(false)
      onUploadSuccess?.()
    } catch {
      toast.error('Failed to remove resume.')
    } finally {
      setIsRemoving(false)
    }
  }

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const allowed = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
    if (!allowed.includes(file.type)) {
      toast.error('Only PDF, DOC, and DOCX files are accepted.')
      return
    }

    if (file.size > MAX_SIZE_BYTES) {
      toast.error('Resume must be smaller than 10MB.')
      return
    }

    setIsUploading(true)
    try {
      const { data: sessionData } = await supabase.auth.getSession()
      if (!sessionData.session) {
        toast.error('Session expired.')
        return
      }

      const formData = new FormData()
      formData.append('file', file)

      const res = await fetch(`${API_BASE}/api/v1/profiles/${profileId}/resume/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${sessionData.session.access_token}`,
          // Do NOT set Content-Type manually — browser sets it with boundary
        },
        body: formData,
      })

      if (!res.ok) throw new Error()

      const uploadBody = await res.json()
      const resumeUploadId: string | undefined = uploadBody.data?.id

      setIsUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''

      if (resumeUploadId) {
        setIsExtracting(true)
        try {
          const extractRes = await fetch(
            `${API_BASE}/api/v1/ai/extract/${resumeUploadId}/`,
            {
              method: 'POST',
              headers: { Authorization: `Bearer ${sessionData.session.access_token}` },
            }
          )

          if (extractRes.ok) {
            toast.success('Profile data extracted and added to your profile!')
          } else {
            toast.warning('Resume uploaded. AI extraction failed — please fill in your profile manually.')
          }
        } catch {
          toast.warning('Resume uploaded. AI extraction failed — please fill in your profile manually.')
        } finally {
          setIsExtracting(false)
        }
      } else {
        toast.success('Resume uploaded successfully!')
      }

      onUploadSuccess?.()
      return
    } catch {
      toast.error('Failed to upload resume. Please try again.')
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  return (
    <>
      <div className="flex items-center justify-between gap-4 rounded-lg border border-gray-200 bg-gray-50 p-4">
        <div className="flex items-center gap-3">
          <FileText className="h-8 w-8 text-indigo-400 shrink-0" />
          <div>
            {fileName ? (
              <>
                <p className="text-sm font-medium text-gray-900 truncate max-w-[200px]">{fileName}</p>
                {uploadedAt && (
                  <p className="text-xs text-gray-500">
                    Uploaded {format(new Date(uploadedAt), 'MMM d, yyyy')}
                  </p>
                )}
              </>
            ) : (
              <p className="text-sm text-gray-400">No resume uploaded yet</p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {fileName && (
            <>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={isDownloading}
                onClick={handleDownload}
                className="gap-1"
              >
                {isDownloading ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Download className="h-3.5 w-3.5" />
                )}
                Download
              </Button>

              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setShowRemoveDialog(true)}
                className="gap-1 text-red-600 border-red-200 hover:bg-red-50 hover:text-red-700"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Remove
              </Button>
            </>
          )}

          <Button
            type="button"
            size="sm"
            className="bg-indigo-600 hover:bg-indigo-700 gap-1"
            disabled={isUploading || isExtracting}
            onClick={() => fileInputRef.current?.click()}
          >
            {isExtracting ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Extracting profile data...
              </>
            ) : isUploading ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="h-3.5 w-3.5" />
                {fileName ? 'Replace' : 'Upload Resume'}
              </>
            )}
          </Button>

          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.doc,.docx"
            className="hidden"
            onChange={handleFileSelect}
          />
        </div>
      </div>

      <Dialog open={showRemoveDialog} onOpenChange={setShowRemoveDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Remove Resume</DialogTitle>
            <DialogDescription>
              Are you sure you want to remove <span className="font-medium text-gray-900">{fileName}</span>?
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              onClick={() => setShowRemoveDialog(false)}
              disabled={isRemoving}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={handleRemoveConfirm}
              disabled={isRemoving}
              className="gap-1"
            >
              {isRemoving ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Removing...
                </>
              ) : (
                <>
                  <Trash2 className="h-3.5 w-3.5" />
                  Remove Resume
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

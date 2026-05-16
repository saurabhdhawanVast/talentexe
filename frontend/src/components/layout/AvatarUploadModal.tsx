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
import { Loader2, Upload, ImageIcon } from 'lucide-react'
import Image from 'next/image'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'
const MAX_SIZE_BYTES = 2 * 1024 * 1024 // 2MB

interface AvatarUploadModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  userId: string
  onSuccess?: (avatarUrl: string) => void
}

export function AvatarUploadModal({ open, onOpenChange, userId, onSuccess }: AvatarUploadModalProps) {
  const supabase = createClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      toast.error('Only JPG, PNG, and WebP images are supported.')
      return
    }

    if (file.size > MAX_SIZE_BYTES) {
      toast.error('Image must be smaller than 2MB.')
      return
    }

    setSelectedFile(file)
    const reader = new FileReader()
    reader.onload = (ev) => setPreviewUrl(ev.target?.result as string)
    reader.readAsDataURL(file)
  }

  const handleUpload = async () => {
    if (!selectedFile) return
    setIsLoading(true)

    try {
      const { data: sessionData } = await supabase.auth.getSession()
      if (!sessionData.session) {
        toast.error('Not authenticated. Please log in again.')
        return
      }

      const formData = new FormData()
      formData.append('avatar', selectedFile)

      const res = await fetch(`${API_BASE}/api/v1/users/${userId}/avatar/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${sessionData.session.access_token}`,
        },
        body: formData,
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        toast.error(body?.error ?? 'Failed to upload image.')
        return
      }

      const body = await res.json()
      const publicUrl: string = body?.data?.avatar_url ?? ''

      toast.success('Profile picture updated!')
      onSuccess?.(publicUrl)
      handleClose()
    } catch {
      toast.error('Failed to upload image. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleClose = () => {
    setPreviewUrl(null)
    setSelectedFile(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && handleClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Update Profile Picture</DialogTitle>
          <DialogDescription>
            Upload a JPG, PNG, or WebP image. Maximum size: 2MB.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div
            className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 p-8 cursor-pointer hover:border-indigo-400 hover:bg-indigo-50 transition-colors"
            onClick={() => fileInputRef.current?.click()}
            onKeyDown={(e) => e.key === 'Enter' && fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
            aria-label="Click to select an image"
          >
            {previewUrl ? (
              <div className="relative h-32 w-32 rounded-full overflow-hidden">
                <Image src={previewUrl} alt="Avatar preview" fill className="object-cover" />
              </div>
            ) : (
              <>
                <ImageIcon className="h-12 w-12 text-gray-300 mb-3" />
                <p className="text-sm text-gray-500">Click to select an image</p>
                <p className="text-xs text-gray-400 mt-1">JPG, PNG, WebP up to 2MB</p>
              </>
            )}
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={handleFileChange}
          />

          {selectedFile && (
            <p className="text-sm text-gray-600 text-center">
              Selected: <span className="font-medium">{selectedFile.name}</span>
            </p>
          )}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={handleClose} disabled={isLoading}>
            Cancel
          </Button>
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
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

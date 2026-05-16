'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Loader2 } from 'lucide-react'

interface RejectModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  employeeName: string
  onConfirm: (comment: string) => Promise<void>
}

export function RejectModal({ open, onOpenChange, employeeName, onConfirm }: RejectModalProps) {
  const [comment, setComment] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleConfirm = async () => {
    setIsLoading(true)
    try {
      await onConfirm(comment)
      setComment('')
      onOpenChange(false)
    } finally {
      setIsLoading(false)
    }
  }

  const handleOpenChange = (open: boolean) => {
    if (!open) setComment('')
    onOpenChange(open)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Reject Profile</DialogTitle>
          <DialogDescription>
            Rejecting the profile for <span className="font-semibold text-gray-900">{employeeName}</span>.
            Add a comment to help them understand what needs to be improved.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2">
          <Label htmlFor="reject-comment">Comment</Label>
          <Textarea
            id="reject-comment"
            placeholder="Please explain why this profile is being rejected..."
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={4}
            disabled={isLoading}
          />
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            className="bg-red-600 hover:bg-red-700 text-white"
            onClick={handleConfirm}
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Rejecting...
              </>
            ) : (
              'Reject Profile'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

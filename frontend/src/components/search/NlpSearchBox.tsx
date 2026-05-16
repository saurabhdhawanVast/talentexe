'use client'

import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Search } from 'lucide-react'

interface NlpSearchBoxProps {
  value: string
  onChange: (value: string) => void
  onSearch: () => void
  isLoading: boolean
}

export function NlpSearchBox({ value, onChange, onSearch, isLoading }: NlpSearchBoxProps) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && value.trim().length >= 3) {
      onSearch()
    }
  }

  return (
    <div className="flex gap-2">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400 pointer-events-none" />
        <Input
          className="pl-10 h-12 text-base"
          placeholder='e.g. "Find backend developers with Java and 5+ years experience in fintech"'
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          aria-label="Natural language search query"
        />
      </div>
      <Button
        className="h-12 px-6 bg-indigo-600 hover:bg-indigo-700"
        onClick={onSearch}
        disabled={isLoading || value.trim().length < 3}
        aria-label="Search"
      >
        {isLoading ? 'Searching...' : 'Search'}
      </Button>
    </div>
  )
}

'use client'

import { useState } from 'react'
import { NlpSearchBox } from '@/components/search/NlpSearchBox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { BrainCircuit } from 'lucide-react'

export default function SmartSearchPage() {
  const [query, setQuery] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [submittedQuery, setSubmittedQuery] = useState<string | null>(null)

  // Filter state — UI-only for now
  const [skillFilter, setSkillFilter] = useState('')
  const [locationFilter, setLocationFilter] = useState('')
  const [expFilter, setExpFilter] = useState('')
  const [departmentFilter, setDepartmentFilter] = useState('')

  const handleSearch = () => {
    if (query.trim().length < 3) return
    setIsLoading(true)
    // Simulate a 1s loading state, then show the placeholder message
    setTimeout(() => {
      setSubmittedQuery(query.trim())
      setIsLoading(false)
    }, 1000)
  }

  return (
    <section aria-labelledby="search-heading" className="w-full">
      <div className="mb-6">
        <h1 id="search-heading" className="text-2xl font-semibold text-gray-900">
          Smart Talent Search
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Describe the talent you need in plain English and let AI find the best matches.
        </p>
      </div>

      {/* Search box */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm p-6 space-y-4">
        <NlpSearchBox
          value={query}
          onChange={setQuery}
          onSearch={handleSearch}
          isLoading={isLoading}
        />

        {/* Filter row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 border-t border-gray-100">
          <div className="space-y-1">
            <Label className="text-xs text-gray-500">Skill</Label>
            <Input
              placeholder="e.g. React"
              value={skillFilter}
              onChange={(e) => setSkillFilter(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs text-gray-500">Location</Label>
            <Input
              placeholder="e.g. London"
              value={locationFilter}
              onChange={(e) => setLocationFilter(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs text-gray-500">Min Experience</Label>
            <Input
              type="number"
              placeholder="0"
              value={expFilter}
              onChange={(e) => setExpFilter(e.target.value)}
              min={0}
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs text-gray-500">Department</Label>
            <Input
              placeholder="e.g. Engineering"
              value={departmentFilter}
              onChange={(e) => setDepartmentFilter(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* Results area */}
      {isLoading && (
        <div className="mt-8 flex flex-col items-center gap-3 text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600" />
          <p className="text-sm text-gray-500">Searching talent pool...</p>
        </div>
      )}

      {!isLoading && submittedQuery && (
        <div className="mt-8 flex flex-col items-center gap-4 text-center py-16 rounded-xl border border-dashed border-indigo-200 bg-indigo-50">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-indigo-100">
            <BrainCircuit className="h-8 w-8 text-indigo-500" />
          </div>
          <div className="max-w-md">
            <h2 className="text-lg font-semibold text-indigo-900">AI-powered search is coming in Phase 3.</h2>
            <p className="mt-2 text-sm text-indigo-700">
              Your query has been captured:{' '}
              <span className="font-medium">&quot;{submittedQuery}&quot;</span>
            </p>
            <p className="mt-3 text-xs text-indigo-500">
              Natural language talent matching with semantic search will be available in the next release.
            </p>
          </div>
        </div>
      )}

      {!isLoading && !submittedQuery && (
        <div className="mt-8 flex flex-col items-center gap-3 text-center py-16 text-gray-400">
          <BrainCircuit className="h-12 w-12 text-gray-200" />
          <p className="text-sm">Enter a search query above to find talent.</p>
        </div>
      )}
    </section>
  )
}

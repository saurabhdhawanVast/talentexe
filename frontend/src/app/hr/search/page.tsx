'use client'

import { useState } from 'react'
import { BrainCircuit, X } from 'lucide-react'
import { toast } from 'sonner'
import { createClient } from '@/lib/supabase'
import { NlpSearchBox } from '@/components/search/NlpSearchBox'
import { SearchResults } from '@/components/search/SearchResults'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { ApiEnvelope, QueryParsed, SearchResponse, SearchResult } from '@/types'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

function QueryChips({ parsed }: { parsed: QueryParsed }) {
  const chips: { label: string; value: string }[] = []

  if (parsed.skills_required.length > 0)
    chips.push({ label: 'Skills', value: parsed.skills_required.join(', ') })
  if (parsed.skills_nice_to_have.length > 0)
    chips.push({ label: 'Nice-to-have', value: parsed.skills_nice_to_have.join(', ') })
  if (parsed.location)
    chips.push({ label: 'Location', value: parsed.location })
  if (parsed.min_years_experience != null)
    chips.push({ label: 'Min exp', value: `${parsed.min_years_experience} yrs` })
  if (parsed.role_hint)
    chips.push({ label: 'Role', value: parsed.role_hint })
  if (parsed.department)
    chips.push({ label: 'Dept', value: parsed.department })
  if (parsed.availability_hint)
    chips.push({ label: 'Availability', value: parsed.availability_hint })

  if (chips.length === 0) return null

  return (
    <div className="flex flex-wrap gap-2 pt-2">
      <span className="text-xs text-gray-400 self-center">AI understood:</span>
      {chips.map((chip) => (
        <Badge
          key={chip.label}
          variant="secondary"
          className="text-xs gap-1 bg-indigo-50 text-indigo-700 border border-indigo-200"
        >
          <span className="font-medium">{chip.label}:</span> {chip.value}
        </Badge>
      ))}
    </div>
  )
}

export default function SmartSearchPage() {
  const supabase = createClient()

  const [query, setQuery] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [results, setResults] = useState<SearchResult[] | null>(null)
  const [queryParsed, setQueryParsed] = useState<QueryParsed | null>(null)
  const [totalResults, setTotalResults] = useState(0)
  const [searchError, setSearchError] = useState<string | null>(null)

  // Optional explicit filters (override AI-parsed values)
  const [locationFilter, setLocationFilter] = useState('')
  const [expFilter, setExpFilter] = useState('')
  const [departmentFilter, setDepartmentFilter] = useState('')

  const handleSearch = async () => {
    if (query.trim().split(/\s+/).length < 3) return

    setIsLoading(true)
    setResults(null)
    setQueryParsed(null)
    setSearchError(null)

    try {
      const { data: sessionData } = await supabase.auth.getSession()
      if (!sessionData.session) {
        toast.error('Session expired. Please log in again.')
        return
      }

      const body = {
        query: query.trim(),
        filters: {
          location: locationFilter || null,
          min_years: expFilter ? Number(expFilter) : null,
          department: departmentFilter || null,
        },
      }

      const res = await fetch(`${API_BASE}/api/v1/search/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${sessionData.session.access_token}`,
        },
        body: JSON.stringify(body),
      })

      const json: ApiEnvelope<SearchResponse> = await res.json()

      if (!res.ok) {
        const msg = json.error ?? `Search failed (${res.status})`
        setSearchError(msg)
        return
      }

      setQueryParsed(json.data.query_parsed)
      setResults(json.data.results)
      setTotalResults(json.data.total)
    } catch {
      setSearchError('Search temporarily unavailable — please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleClear = () => {
    setQuery('')
    setResults(null)
    setQueryParsed(null)
    setSearchError(null)
    setTotalResults(0)
  }

  const hasSearched = results !== null || searchError !== null

  return (
    <section aria-labelledby="search-heading" className="w-full">
      <div className="mb-6">
        <h1 id="search-heading" className="text-2xl font-semibold text-gray-900">
          Smart Talent Search
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Describe the talent you need in plain English. Results are ranked by AI match score
          and limited to approved employee profiles.
        </p>
      </div>

      {/* Search box + filters */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm p-6 space-y-4">
        <NlpSearchBox
          value={query}
          onChange={setQuery}
          onSearch={handleSearch}
          isLoading={isLoading}
        />

        {/* Query chips — shown after search */}
        {queryParsed && <QueryChips parsed={queryParsed} />}

      </div>

      {/* Loading */}
      {isLoading && (
        <div className="mt-10 flex flex-col items-center gap-3 text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600" />
          <p className="text-sm text-gray-500">
            AI is analysing your query and searching the talent pool…
          </p>
        </div>
      )}

      {/* Error state */}
      {!isLoading && searchError && (
        <div className="mt-8 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-5">
          <div className="flex-1">
            <p className="text-sm font-medium text-red-800">{searchError}</p>
          </div>
          <button onClick={handleClear} className="text-red-400 hover:text-red-600">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Results */}
      {!isLoading && results !== null && !searchError && (
        <>
          {results.length === 0 ? (
            <div className="mt-8 flex flex-col items-center gap-4 text-center py-16 rounded-xl border border-dashed border-gray-200 bg-gray-50">
              <BrainCircuit className="h-10 w-10 text-gray-300" />
              <div className="max-w-sm">
                <p className="text-sm font-medium text-gray-700">No approved profiles match your search.</p>
                <p className="mt-1 text-xs text-gray-500">
                  Try different skills, remove location filters, or check that employees have approved profiles.
                </p>
              </div>
            </div>
          ) : (
            <SearchResults results={results} />
          )}
        </>
      )}

      {/* Idle state */}
      {!isLoading && !hasSearched && (
        <div className="mt-10 flex flex-col items-center gap-3 text-center py-16 text-gray-400">
          <BrainCircuit className="h-12 w-12 text-gray-200" />
          <p className="text-sm">Enter a search query above to find talent.</p>
          <p className="text-xs text-gray-400 max-w-xs">
            Try: &quot;Senior React developer in Mumbai with fintech experience&quot; or
            &quot;Backend engineer with 5+ years Java and Spring Boot&quot;
          </p>
        </div>
      )}
    </section>
  )
}

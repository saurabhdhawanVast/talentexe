'use client'

import Link from 'next/link'
import { User, MapPin, Briefcase, Clock } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import type { SearchResult } from '@/types'

interface SearchResultsProps {
  results: SearchResult[]
}

function MatchScoreBadge({ score }: { score: number }) {
  const color =
    score >= 80
      ? 'bg-green-100 text-green-800 border-green-200'
      : score >= 60
      ? 'bg-amber-100 text-amber-800 border-amber-200'
      : 'bg-red-100 text-red-800 border-red-200'

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${color}`}
      aria-label={`Match score: ${score}%`}
    >
      {score}% match
    </span>
  )
}

function ResultCard({ result }: { result: SearchResult }) {
  const initials = result.full_name
    ? result.full_name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : '?'

  const meta = [result.department, result.location]
    .filter(Boolean)
    .join(' · ')

  return (
    <Card className="w-full">
      <CardContent className="pt-5 pb-4">
        <div className="flex items-start gap-4">
          {/* Avatar */}
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-indigo-700 font-semibold text-sm">
            {result.avatar_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={result.avatar_url}
                alt={result.full_name}
                className="h-11 w-11 rounded-full object-cover"
              />
            ) : (
              initials || <User className="h-5 w-5" />
            )}
          </div>

          {/* Main content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-3 flex-wrap">
              {/* Name + role */}
              <div>
                <h3 className="font-semibold text-gray-900 leading-tight">
                  {result.full_name}
                </h3>
                <p className="text-sm text-indigo-600 mt-0.5">{result.designation}</p>
                {meta && (
                  <p className="text-xs text-gray-500 mt-0.5 flex items-center gap-1">
                    {result.location && <MapPin className="h-3 w-3 inline" />}
                    {meta}
                    {result.experience_years != null && (
                      <>
                        <span>·</span>
                        <Clock className="h-3 w-3 inline" />
                        {result.experience_years} yrs exp
                      </>
                    )}
                  </p>
                )}
              </div>
              {/* Score badge */}
              <MatchScoreBadge score={result.match_score} />
            </div>

            {/* Explanation */}
            {result.explanation && (
              <p className="mt-2 text-sm text-gray-600 leading-relaxed">
                {result.explanation}
              </p>
            )}

            {/* Skills + action */}
            <div className="mt-3 flex items-center justify-between gap-3 flex-wrap">
              <div className="flex flex-wrap gap-1.5">
                {result.top_skills.slice(0, 5).map((skill) => (
                  <Badge
                    key={skill}
                    variant="secondary"
                    className="text-xs px-2 py-0.5"
                  >
                    {skill}
                  </Badge>
                ))}
              </div>
              <Link href={`/hr/search/${result.profile_id}/preview`}>
                <Button
                  size="sm"
                  variant="outline"
                  className="text-indigo-600 border-indigo-200 hover:bg-indigo-50 shrink-0"
                >
                  View Profile
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export function SearchResults({ results }: SearchResultsProps) {
  if (results.length === 0) return null

  return (
    <div className="mt-6 space-y-3">
      <p className="text-sm text-gray-500">
        {results.length} result{results.length !== 1 ? 's' : ''} found
      </p>
      {results.map((result) => (
        <ResultCard key={result.profile_id} result={result} />
      ))}
    </div>
  )
}

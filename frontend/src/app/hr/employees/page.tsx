'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import Link from 'next/link'
import { toast } from 'sonner'
import { getAccessToken } from '@/lib/auth'
import { EmployeeTable } from '@/components/employees/EmployeeTable'
import { BulkUploadModal } from '@/components/employees/BulkUploadModal'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import {
  UserPlus,
  Upload,
  Search,
  ChevronLeft,
  ChevronRight,
  Loader2,
  SlidersHorizontal,
  X,
} from 'lucide-react'
import type { EmployeeListItem, PaginatedResponse } from '@/types'

export const dynamic = 'force-dynamic'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'
const PAGE_SIZE = 20

const STATUS_OPTIONS = [
  { value: 'all', label: 'All Statuses' },
  { value: 'incomplete', label: 'Incomplete' },
  { value: 'submitted', label: 'Submitted' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
]

export default function EmployeesPage() {
  const [employees, setEmployees] = useState<EmployeeListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [isLoading, setIsLoading] = useState(true)
  const [bulkUploadOpen, setBulkUploadOpen] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)

  // Inline filter (always visible)
  const [search, setSearch] = useState('')

  // Drawer filters
  const [status, setStatus] = useState('all')
  const [designation, setDesignation] = useState('')
  const [department, setDepartment] = useState('')
  const [location, setLocation] = useState('')
  const [expMin, setExpMin] = useState('')
  const [expMax, setExpMax] = useState('')

  // Draft state inside the drawer (applied on "Apply")
  const [draftStatus, setDraftStatus] = useState('all')
  const [draftDesignation, setDraftDesignation] = useState('')
  const [draftDepartment, setDraftDepartment] = useState('')
  const [draftLocation, setDraftLocation] = useState('')
  const [draftExpMin, setDraftExpMin] = useState('')
  const [draftExpMax, setDraftExpMax] = useState('')

  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [debouncedSearch, setDebouncedSearch] = useState('')

  useEffect(() => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    searchTimerRef.current = setTimeout(() => setDebouncedSearch(search), 300)
    return () => {
      if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    }
  }, [search])

  const fetchEmployees = useCallback(async () => {
    setIsLoading(true)
    try {
      const token = await getAccessToken()
      if (!token) {
        toast.error('Session expired. Please log in again.')
        return
      }

      const params = new URLSearchParams()
      params.set('page', String(page))
      params.set('page_size', String(PAGE_SIZE))
      if (debouncedSearch) params.set('search', debouncedSearch)
      if (designation) params.set('designation', designation)
      if (department) params.set('department', department)
      if (location) params.set('location', location)
      if (status !== 'all') params.set('status', status)
      if (expMin) params.set('exp_min', expMin)
      if (expMax) params.set('exp_max', expMax)

      const res = await fetch(`${API_BASE}/api/v1/users/?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body?.error ?? `Server error (${res.status})`)
      }

      const body: PaginatedResponse<EmployeeListItem> = await res.json()
      setEmployees(body.data)
      setTotal(body.meta.total)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to load employees.')
    } finally {
      setIsLoading(false)
    }
  }, [page, debouncedSearch, designation, department, location, status, expMin, expMax])

  useEffect(() => {
    fetchEmployees()
  }, [fetchEmployees])

  useEffect(() => {
    setPage(1)
  }, [debouncedSearch, designation, department, location, status, expMin, expMax])

  const openDrawer = () => {
    // Sync draft state with current applied filters
    setDraftStatus(status)
    setDraftDesignation(designation)
    setDraftDepartment(department)
    setDraftLocation(location)
    setDraftExpMin(expMin)
    setDraftExpMax(expMax)
    setDrawerOpen(true)
  }

  const applyFilters = () => {
    setStatus(draftStatus)
    setDesignation(draftDesignation)
    setDepartment(draftDepartment)
    setLocation(draftLocation)
    setExpMin(draftExpMin)
    setExpMax(draftExpMax)
    setDrawerOpen(false)
  }

  const clearDrawerFilters = () => {
    setDraftStatus('all')
    setDraftDesignation('')
    setDraftDepartment('')
    setDraftLocation('')
    setDraftExpMin('')
    setDraftExpMax('')
  }

  const clearAllFilters = () => {
    setStatus('all')
    setDesignation('')
    setDepartment('')
    setLocation('')
    setExpMin('')
    setExpMax('')
  }

  const hasActiveFilters =
    status !== 'all' ||
    designation !== '' ||
    department !== '' ||
    location !== '' ||
    expMin !== '' ||
    expMax !== ''

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const rangeStart = (page - 1) * PAGE_SIZE + 1
  const rangeEnd = Math.min(page * PAGE_SIZE, total)

  return (
    <section aria-labelledby="employees-heading">
      <div className="mb-6 flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 id="employees-heading" className="text-2xl font-semibold text-gray-900">
            Employees
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Approved employees reviewed by HR.
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="outline"
            onClick={() => setBulkUploadOpen(true)}
            className="gap-2"
          >
            <Upload className="h-4 w-4" />
            Bulk Upload
          </Button>
          <Link href="/hr/employees/new">
            <Button className="bg-indigo-600 hover:bg-indigo-700 gap-2">
              <UserPlus className="h-4 w-4" />
              Add Employee
            </Button>
          </Link>
        </div>
      </div>

      {/* Search + Filter button row */}
      <div className="mb-4 flex items-center gap-2">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
          <Input
            placeholder="Search by name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
            aria-label="Search employees by name"
          />
        </div>

        <Button
          variant="outline"
          onClick={openDrawer}
          className="gap-2 shrink-0"
          aria-label="Open filters"
        >
          <SlidersHorizontal className="h-4 w-4" />
          Filters
        </Button>

        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={clearAllFilters}
            className="gap-1 text-indigo-600 hover:text-indigo-700 shrink-0"
          >
            <X className="h-3.5 w-3.5" />
            Clear filters
          </Button>
        )}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
        </div>
      ) : (
        <EmployeeTable employees={employees} onMutate={fetchEmployees} />
      )}

      {/* Pagination */}
      {!isLoading && total > 0 && (
        <div className="mt-4 flex items-center justify-between text-sm text-gray-500">
          <p>
            Showing {rangeStart}–{rangeEnd} of {total} employee{total !== 1 ? 's' : ''}
          </p>
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              aria-label="Previous page"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>

            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              let pageNum: number
              if (totalPages <= 5) {
                pageNum = i + 1
              } else if (page <= 3) {
                pageNum = i + 1
              } else if (page >= totalPages - 2) {
                pageNum = totalPages - 4 + i
              } else {
                pageNum = page - 2 + i
              }
              return (
                <Button
                  key={pageNum}
                  variant={pageNum === page ? 'default' : 'outline'}
                  size="sm"
                  className={pageNum === page ? 'bg-indigo-600 hover:bg-indigo-700' : ''}
                  onClick={() => setPage(pageNum)}
                  aria-label={`Page ${pageNum}`}
                  aria-current={pageNum === page ? 'page' : undefined}
                >
                  {pageNum}
                </Button>
              )
            })}

            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              aria-label="Next page"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      <BulkUploadModal
        open={bulkUploadOpen}
        onOpenChange={setBulkUploadOpen}
        onSuccess={fetchEmployees}
      />

      {/* Filter Drawer */}
      {drawerOpen && (
        <div className="fixed inset-0 z-40 flex">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/30"
            onClick={() => setDrawerOpen(false)}
            aria-hidden="true"
          />

          {/* Drawer panel — slides in from the right */}
          <div className="relative ml-auto z-50 flex h-full w-80 flex-col bg-white shadow-xl">
            {/* Drawer header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
              <h2 className="text-sm font-semibold text-gray-900">Filters</h2>
              <button
                onClick={() => setDrawerOpen(false)}
                className="rounded-md p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100"
                aria-label="Close filters"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Drawer body */}
            <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5">
              <div className="space-y-1.5">
                <Label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                  Status
                </Label>
                <Select value={draftStatus} onValueChange={setDraftStatus}>
                  <SelectTrigger>
                    <SelectValue placeholder="All Statuses" />
                  </SelectTrigger>
                  <SelectContent>
                    {STATUS_OPTIONS.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                  Department
                </Label>
                <Input
                  placeholder="e.g. Engineering"
                  value={draftDepartment}
                  onChange={(e) => setDraftDepartment(e.target.value)}
                />
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                  Location
                </Label>
                <Input
                  placeholder="e.g. New York"
                  value={draftLocation}
                  onChange={(e) => setDraftLocation(e.target.value)}
                />
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                  Designation
                </Label>
                <Input
                  placeholder="e.g. Software Engineer"
                  value={draftDesignation}
                  onChange={(e) => setDraftDesignation(e.target.value)}
                />
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                  Experience (years)
                </Label>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    placeholder="Min"
                    value={draftExpMin}
                    onChange={(e) => setDraftExpMin(e.target.value)}
                    min={0}
                    className="w-24"
                  />
                  <span className="text-gray-400 text-sm">–</span>
                  <Input
                    type="number"
                    placeholder="Max"
                    value={draftExpMax}
                    onChange={(e) => setDraftExpMax(e.target.value)}
                    min={0}
                    className="w-24"
                  />
                </div>
              </div>
            </div>

            {/* Drawer footer */}
            <div className="px-5 py-4 border-t border-gray-200 flex items-center gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={clearDrawerFilters}
              >
                Clear Filters
              </Button>
              <Button
                className="flex-1 bg-indigo-600 hover:bg-indigo-700"
                onClick={applyFilters}
              >
                Apply
              </Button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

/**
 * ConceptSearch
 * ────────────────────────────────────────────────────────────────────────────
 * Search survey data by concept (canonical field name) across multiple years.
 *
 * Flow:
 *   1. Load concept list (FieldMapping records from /profiling/query/concepts/)
 *   2. User selects a concept + years + optional filters
 *   3. Fetch matching surveys and concept value distribution
 *   4. Display results table + value breakdown
 */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Lightbulb, ChevronLeft, Search, X, RefreshCw, BarChart3 } from 'lucide-react'
import { getConcepts, getConceptValues, searchByConcept } from '../../api/profilingApi'
import { useToast } from '../../context/ToastContext'
import useDebounce from '../../hooks/useDebounce'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import Table, { Pagination } from '../../components/ui/Table'
import Button from '../../components/ui/Button'
import Badge from '../../components/ui/Badge'
import Spinner from '../../components/ui/Spinner'

const CURRENT_YEAR = new Date().getFullYear()
const YEAR_RANGE   = Array.from({ length: 8 }, (_, i) => CURRENT_YEAR - i)

const LEVEL_COLORS = {
  household: 'blue',
  family:    'purple',
  person:    'green',
}

const RESULT_COLUMNS = [
  {
    key: 'household_number',
    label: 'Household',
    render: (row) => `#${row.household?.household_number ?? row.household_number ?? '—'}`,
  },
  {
    key: 'survey_year',
    label: 'Year',
    width: '80px',
    render: (row) => <Badge color="blue">{row.survey_year}</Badge>,
  },
  {
    key: 'status',
    label: 'Status',
    width: '110px',
    render: (row) => {
      const c = { DRAFT: 'gray', SUBMITTED: 'yellow', VERIFIED: 'green', REVISION: 'orange' }
      return <Badge color={c[row.status] ?? 'gray'}>{row.status}</Badge>
    },
  },
  {
    key: 'canonical_value',
    label: 'Value',
    render: (row) => row.canonical_value ?? row.matched_value ?? '—',
  },
]

export default function ConceptSearch() {
  const navigate = useNavigate()
  const toast    = useToast()

  // Concept list
  const [concepts,        setConcepts]        = useState([])
  const [conceptSearch,   setConceptSearch]   = useState('')
  const [loadingConcepts, setLoadingConcepts] = useState(false)

  // Selected filters
  const [selectedConcept, setSelectedConcept] = useState(null)
  const [selectedYears,   setSelectedYears]   = useState([CURRENT_YEAR])
  const [selectedValue,   setSelectedValue]   = useState('')
  const [purok,           setPurok]           = useState('')

  // Value distribution
  const [valueDist,   setValueDist]   = useState([])
  const [loadingDist, setLoadingDist] = useState(false)

  // Search results
  const [results,     setResults]     = useState([])
  const [count,       setCount]       = useState(0)
  const [page,        setPage]        = useState(1)
  const [loadingRes,  setLoadingRes]  = useState(false)

  const debouncedConceptSearch = useDebounce(conceptSearch, 300)

  // Load concept list
  useEffect(() => {
    setLoadingConcepts(true)
    getConcepts({
      search: debouncedConceptSearch || undefined,
      page_size: 50,
    })
      .then(({ data }) => setConcepts(data.results ?? []))
      .catch(() => {})
      .finally(() => setLoadingConcepts(false))
  }, [debouncedConceptSearch])

  // Load value distribution when concept + years change
  useEffect(() => {
    if (!selectedConcept) { setValueDist([]); return }
    setLoadingDist(true)
    const yearMin = Math.min(...selectedYears)
    const yearMax = Math.max(...selectedYears)
    getConceptValues({
      canonical_name: selectedConcept.canonical_name,
      year_min: yearMin,
      year_max: yearMax,
      page_size: 30,
    })
      .then(({ data }) => setValueDist(data.results ?? data ?? []))
      .catch(() => {})
      .finally(() => setLoadingDist(false))
  }, [selectedConcept, selectedYears])

  const handleSearch = useCallback(async (p = 1) => {
    if (!selectedConcept || selectedYears.length === 0) return
    setLoadingRes(true)
    try {
      const { data } = await searchByConcept({
        concept:          selectedConcept.canonical_name,
        canonical_value:  selectedValue   || undefined,
        year_min:         Math.min(...selectedYears),
        year_max:         Math.max(...selectedYears),
        purok:            purok || undefined,
        page:             p,
        page_size:        20,
      })
      setResults(data.results ?? [])
      setCount(data.count ?? 0)
      setPage(p)
    } catch (err) {
      toast(err.response?.data?.detail ?? 'Search failed', 'error')
    } finally {
      setLoadingRes(false)
    }
  }, [selectedConcept, selectedYears, selectedValue, purok, toast])

  const toggleYear = (year) =>
    setSelectedYears((prev) =>
      prev.includes(year) ? prev.filter((y) => y !== year) : [...prev, year]
    )

  const maxDist  = Math.max(...valueDist.map((d) => d.count ?? 0), 1)

  return (
    <div className="max-w-5xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/profiling')}
          className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ChevronLeft size={18} />
        </button>
        <div className="flex items-center gap-3">
          <div className="p-2 bg-amber-50 rounded-lg">
            <Lightbulb size={20} className="text-amber-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Concept Search</h1>
            <p className="text-sm text-gray-500">Search survey data by canonical concept across years</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* ── Left panel: concept selector + years ── */}
        <div className="lg:col-span-1 space-y-4">

          {/* Concept list */}
          <Card>
            <CardHeader title="Select Concept" />
            <CardBody>
              <div className="relative mb-3">
                <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  value={conceptSearch}
                  onChange={(e) => setConceptSearch(e.target.value)}
                  placeholder="Filter concepts…"
                  className="w-full pl-8 pr-3 py-1.5 text-sm rounded-lg border border-gray-300
                    focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>

              {loadingConcepts ? (
                <div className="flex justify-center py-4"><Spinner /></div>
              ) : (
                <div className="space-y-1 max-h-72 overflow-y-auto">
                  {concepts.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => {
                        setSelectedConcept(c)
                        setSelectedValue('')
                        setResults([])
                      }}
                      className={`w-full flex items-start gap-2 px-3 py-2 rounded-lg text-left
                        transition-colors text-sm
                        ${selectedConcept?.id === c.id
                          ? 'bg-amber-50 border border-amber-200'
                          : 'hover:bg-gray-50 border border-transparent'}`}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-gray-900 truncate">{c.canonical_name}</p>
                        <p className="text-xs text-gray-500 truncate">{c.description ?? c.data_type}</p>
                      </div>
                      <Badge color={LEVEL_COLORS[c.level] ?? 'gray'}>{c.level}</Badge>
                    </button>
                  ))}
                  {concepts.length === 0 && (
                    <p className="text-sm text-gray-400 text-center py-4">No concepts found</p>
                  )}
                </div>
              )}
            </CardBody>
          </Card>

          {/* Year selector */}
          <Card>
            <CardHeader title="Survey Years" />
            <CardBody>
              <div className="flex flex-wrap gap-2">
                {YEAR_RANGE.map((y) => (
                  <label key={y} className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      className="w-4 h-4 accent-amber-500 rounded"
                      checked={selectedYears.includes(y)}
                      onChange={() => toggleYear(y)}
                    />
                    <span className="text-sm text-gray-700">{y}</span>
                  </label>
                ))}
              </div>
              <p className="text-xs text-gray-400 mt-2">
                {selectedYears.length} year(s) selected:
                {' '}{[...selectedYears].sort().join(', ')}
              </p>
            </CardBody>
          </Card>

          {/* Purok filter */}
          <Card>
            <CardHeader title="Optional Filters" />
            <CardBody>
              <div className="space-y-1">
                <label className="block text-xs font-medium text-gray-600">Purok #</label>
                <input
                  type="number"
                  value={purok}
                  onChange={(e) => setPurok(e.target.value)}
                  placeholder="Any"
                  className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm
                    focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>
            </CardBody>
          </Card>

        </div>

        {/* ── Right panel: value distribution + results ── */}
        <div className="lg:col-span-2 space-y-4">

          {!selectedConcept && (
            <div className="flex flex-col items-center gap-2 py-20 text-gray-400">
              <Lightbulb size={40} />
              <p className="text-sm">Select a concept from the left panel to begin.</p>
            </div>
          )}

          {/* Concept info */}
          {selectedConcept && (
            <Card>
              <CardBody>
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-amber-50 rounded-lg shrink-0">
                    <Lightbulb size={16} className="text-amber-600" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-semibold text-gray-900">{selectedConcept.canonical_name}</h3>
                      <Badge color={LEVEL_COLORS[selectedConcept.level] ?? 'gray'}>
                        {selectedConcept.level}
                      </Badge>
                      <Badge color="gray">{selectedConcept.data_type}</Badge>
                    </div>
                    <p className="text-sm text-gray-500 mt-0.5">
                      {selectedConcept.description ?? 'No description available'}
                    </p>
                    {selectedConcept.years_covered?.length > 0 && (
                      <p className="text-xs text-gray-400 mt-1">
                        Years covered: {selectedConcept.years_covered.sort().join(', ')}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => { setSelectedConcept(null); setResults([]) }}
                    className="p-1 text-gray-400 hover:text-gray-600 rounded"
                  >
                    <X size={14} />
                  </button>
                </div>
              </CardBody>
            </Card>
          )}

          {/* Value distribution bar chart */}
          {selectedConcept && (
            <Card>
              <CardHeader
                title="Value Distribution"
                subtitle={`Across selected years · ${valueDist.reduce((n, d) => n + (d.count ?? 0), 0).toLocaleString()} records`}
                actions={
                  loadingDist && <Spinner size="sm" />
                }
              />
              <CardBody>
                {valueDist.length === 0 && !loadingDist && (
                  <p className="text-sm text-gray-400">No distribution data for selected years.</p>
                )}
                <div className="space-y-2">
                  {valueDist.map((d) => {
                    const pct = Math.round(((d.count ?? 0) / maxDist) * 100)
                    return (
                      <button
                        key={d.canonical_value ?? d.value}
                        className={`w-full flex items-center gap-3 text-sm text-left
                          hover:bg-gray-50 p-1 rounded-lg transition-colors
                          ${selectedValue === (d.canonical_value ?? d.value) ? 'ring-1 ring-amber-400' : ''}`}
                        onClick={() => {
                          const val = d.canonical_value ?? d.value
                          setSelectedValue((prev) => prev === val ? '' : val)
                        }}
                      >
                        <span className="w-36 shrink-0 font-medium text-gray-700 truncate">
                          {d.canonical_value ?? d.value ?? '(blank)'}
                        </span>
                        <div className="flex-1 h-4 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-amber-400 rounded-full transition-all"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className="w-12 text-right text-gray-500 shrink-0">
                          {(d.count ?? 0).toLocaleString()}
                        </span>
                      </button>
                    )
                  })}
                </div>
                {selectedValue && (
                  <div className="mt-3 flex items-center gap-2 text-xs text-amber-700">
                    <BarChart3 size={13} />
                    Filtering results by value: <strong>{selectedValue}</strong>
                    <button onClick={() => setSelectedValue('')} className="text-gray-400 hover:text-gray-600">
                      <X size={12} />
                    </button>
                  </div>
                )}
              </CardBody>
            </Card>
          )}

          {/* Search button + results */}
          {selectedConcept && (
            <>
              <div className="flex items-center gap-3">
                <Button
                  onClick={() => handleSearch(1)}
                  disabled={loadingRes || selectedYears.length === 0}
                  className="gap-2"
                >
                  <Search size={15} />
                  {loadingRes ? 'Searching…' : 'Find Matching Surveys'}
                </Button>
                {results.length > 0 && (
                  <Button
                    variant="ghost"
                    onClick={() => { setResults([]); setCount(0) }}
                    className="gap-2 text-sm"
                  >
                    <RefreshCw size={13} />
                    Clear
                  </Button>
                )}
                {loadingRes && <Spinner size="sm" />}
              </div>

              {results.length > 0 && (
                <Card>
                  <CardHeader
                    title={`${count.toLocaleString()} matching survey(s)`}
                    subtitle={selectedValue ? `Value filter: "${selectedValue}"` : undefined}
                  />
                  <Table
                    columns={RESULT_COLUMNS}
                    data={results}
                    loading={loadingRes}
                    emptyMessage="No matching surveys found."
                  />
                  {count > 20 && (
                    <div className="px-6 py-3 border-t border-gray-100">
                      <Pagination count={count} page={page} onPageChange={handleSearch} />
                    </div>
                  )}
                </Card>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

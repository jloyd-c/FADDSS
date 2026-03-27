import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Home, Plus, Search, ChevronRight, Filter, FileBarChart2,
  Lightbulb, GitCompare, RefreshCw,
} from 'lucide-react'
import { getHouseholds } from '../../api/profilingApi'
import { useToast } from '../../context/ToastContext'
import useDebounce from '../../hooks/useDebounce'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import Table, { Pagination } from '../../components/ui/Table'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'

const STATUS_COLORS = {
  ACTIVE:     'green',
  VACANT:     'yellow',
  ABANDONED:  'orange',
  DEMOLISHED: 'red',
}

const STATUS_OPTIONS = [
  { value: '',           label: 'All Statuses' },
  { value: 'ACTIVE',     label: 'Active' },
  { value: 'VACANT',     label: 'Vacant' },
  { value: 'ABANDONED',  label: 'Abandoned' },
  { value: 'DEMOLISHED', label: 'Demolished' },
]

const HAS_SURVEYS_OPTIONS = [
  { value: '',     label: 'All Households' },
  { value: 'true', label: 'Has Surveys' },
  { value: 'false', label: 'No Surveys Yet' },
]

const COLUMNS = [
  { key: 'household_number', label: 'Household #', width: '140px' },
  { key: 'address',          label: 'Address' },
  {
    key: 'purok',
    label: 'Purok',
    width: '100px',
    render: (row) => row.purok?.name ?? row.purok?.number ?? '—',
  },
  {
    key: 'status',
    label: 'Status',
    width: '110px',
    render: (row) => (
      <Badge color={STATUS_COLORS[row.status] ?? 'gray'}>{row.status}</Badge>
    ),
  },
  {
    key: 'surveys_count',
    label: 'Surveys',
    width: '80px',
    render: (row) => (
      <span className="font-medium text-blue-600">{row.surveys_count ?? 0}</span>
    ),
  },
  {
    key: 'actions',
    label: '',
    width: '40px',
    render: () => (
      <ChevronRight size={16} className="text-gray-400" />
    ),
  },
]

export default function ProfilingPage() {
  const navigate    = useNavigate()
  const toast       = useToast()
  const [params, setParams] = useSearchParams()

  const [rows,    setRows]    = useState([])
  const [count,   setCount]   = useState(0)
  const [loading, setLoading] = useState(false)
  const [page,    setPage]    = useState(Number(params.get('page') ?? 1))

  const [search,     setSearch]     = useState(params.get('search') ?? '')
  const [status,     setStatus]     = useState(params.get('status') ?? '')
  const [hasSurveys, setHasSurveys] = useState(params.get('has_surveys') ?? '')

  const debouncedSearch = useDebounce(search, 350)

  const load = useCallback(async (p = 1) => {
    setLoading(true)
    try {
      const { data } = await getHouseholds({
        page: p,
        search:      debouncedSearch || undefined,
        status:      status          || undefined,
        has_surveys: hasSurveys      || undefined,
        page_size: 20,
      })
      setRows(data.results ?? [])
      setCount(data.count  ?? 0)
      setPage(p)

      // Sync URL params
      const next = new URLSearchParams()
      if (p > 1)          next.set('page', p)
      if (debouncedSearch) next.set('search', debouncedSearch)
      if (status)          next.set('status', status)
      if (hasSurveys)      next.set('has_surveys', hasSurveys)
      setParams(next, { replace: true })
    } catch (err) {
      toast(err.response?.data?.detail ?? 'Failed to load households', 'error')
    } finally {
      setLoading(false)
    }
  }, [debouncedSearch, status, hasSurveys, setParams, toast])

  useEffect(() => { load(1) }, [load])

  return (
    <div className="space-y-6">

      {/* ── Page header ── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-50 rounded-lg">
            <Home size={20} className="text-blue-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Household Profiling</h1>
            <p className="text-sm text-gray-500">{count.toLocaleString()} households</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            className="gap-2 text-sm"
            onClick={() => navigate('/profiling/concepts')}
          >
            <Lightbulb size={15} />
            Concepts
          </Button>
          <Button
            variant="ghost"
            className="gap-2 text-sm"
            onClick={() => navigate('/profiling/comparison')}
          >
            <GitCompare size={15} />
            Compare
          </Button>
          <Button
            variant="ghost"
            className="gap-2 text-sm"
            onClick={() => navigate('/profiling/reports')}
          >
            <FileBarChart2 size={15} />
            Reports
          </Button>
          <Button
            className="gap-2"
            onClick={() => navigate('/profiling/wizard')}
          >
            <Plus size={16} />
            New Survey
          </Button>
        </div>
      </div>

      {/* ── Quick-nav cards ── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'New Survey',  icon: Plus,          color: 'bg-blue-600',   path: '/profiling/wizard' },
          { label: 'Compare',     icon: GitCompare,    color: 'bg-purple-600', path: '/profiling/comparison' },
          { label: 'Concepts',    icon: Lightbulb,     color: 'bg-amber-500',  path: '/profiling/concepts' },
          { label: 'Reports',     icon: FileBarChart2, color: 'bg-green-600',  path: '/profiling/reports' },
        ].map(({ label, icon: Icon, color, path }) => (
          <button
            key={label}
            onClick={() => navigate(path)}
            className="flex items-center gap-3 p-3 bg-white rounded-xl border border-gray-200
              shadow-sm hover:shadow-md transition-shadow text-left"
          >
            <div className={`p-2 ${color} rounded-lg`}>
              <Icon size={16} className="text-white" />
            </div>
            <span className="text-sm font-medium text-gray-700">{label}</span>
          </button>
        ))}
      </div>

      {/* ── Filters ── */}
      <Card>
        <CardBody>
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by household number or address…"
                className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-gray-300
                  focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              />
            </div>
            <Select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              options={STATUS_OPTIONS}
              className="sm:w-44"
            />
            <Select
              value={hasSurveys}
              onChange={(e) => setHasSurveys(e.target.value)}
              options={HAS_SURVEYS_OPTIONS}
              className="sm:w-52"
            />
            <Button
              variant="ghost"
              onClick={() => load(1)}
              className="shrink-0"
              title="Refresh"
            >
              <RefreshCw size={15} />
            </Button>
          </div>
        </CardBody>
      </Card>

      {/* ── Table ── */}
      <Card>
        <CardHeader
          title="Households"
          subtitle="Click a row to view surveys or start a new survey"
        />
        <Table
          columns={COLUMNS}
          data={rows}
          loading={loading}
          emptyMessage="No households found. Adjust filters or create a new survey."
          onRowClick={(row) => navigate(`/profiling/wizard?household=${row.id}`)}
        />
        {count > 20 && (
          <div className="px-6 py-3 border-t border-gray-100">
            <Pagination count={count} page={page} onPageChange={load} />
          </div>
        )}
      </Card>
    </div>
  )
}

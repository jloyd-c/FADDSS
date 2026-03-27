/**
 * HouseholdComparison
 * ────────────────────────────────────────────────────────────────────────────
 * Side-by-side view of two survey years for the same household.
 * Green = improvement, Red = decline, Yellow = changed (neutral).
 */

import { useState, useEffect } from 'react'
import { GitCompare, Search, ChevronLeft, AlertCircle, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { getHouseholds, getHouseholdSurveys, compareSurveys } from '../../api/profilingApi'
import { useToast } from '../../context/ToastContext'
import useDebounce from '../../hooks/useDebounce'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import Badge from '../../components/ui/Badge'
import Spinner from '../../components/ui/Spinner'

// Fields typically considered "improvements" when they go up vs. down
const POSITIVE_UP_FIELDS = new Set([
  'monthly_income', 'income_bracket', 'water_source', 'toilet_type',
  'educational_attainment', 'employment_status',
])
const POSITIVE_DOWN_FIELDS = new Set(['num_informal_settlers', 'num_out_of_school'])

function diffDirection(fieldName, oldVal, newVal) {
  if (oldVal === newVal) return 'same'
  if (POSITIVE_UP_FIELDS.has(fieldName)) return 'improved'
  if (POSITIVE_DOWN_FIELDS.has(fieldName)) return 'declined'
  return 'changed'
}

const DIRECTION_STYLES = {
  same:     { badge: 'gray',   icon: Minus,       bg: '' },
  improved: { badge: 'green',  icon: TrendingUp,  bg: 'bg-green-50' },
  declined: { badge: 'red',    icon: TrendingDown, bg: 'bg-red-50' },
  changed:  { badge: 'yellow', icon: Minus,       bg: 'bg-yellow-50' },
}

// ── Diff row ──────────────────────────────────────────────────────────────────

function DiffRow({ label, oldVal, newVal }) {
  const dir    = diffDirection(label, oldVal, newVal)
  const { badge, icon: Icon, bg } = DIRECTION_STYLES[dir]
  const changed = dir !== 'same'

  return (
    <div className={`grid grid-cols-3 gap-2 px-4 py-2.5 text-sm rounded-lg ${changed ? bg : ''}`}>
      <div className="text-gray-600 font-medium truncate capitalize">{label.replace(/_/g, ' ')}</div>
      <div className={`truncate ${changed ? 'text-gray-500 line-through' : 'text-gray-800'}`}>
        {oldVal ?? <span className="text-gray-300 italic">—</span>}
      </div>
      <div className="flex items-center gap-1.5">
        {changed && <Icon size={13} className={badge === 'green' ? 'text-green-600' : badge === 'red' ? 'text-red-500' : 'text-yellow-600'} />}
        <span className={`font-medium ${changed ? (badge === 'green' ? 'text-green-700' : badge === 'red' ? 'text-red-600' : 'text-yellow-700') : 'text-gray-800'}`}>
          {newVal ?? <span className="text-gray-300 italic">—</span>}
        </span>
      </div>
    </div>
  )
}

// ── Change legend ─────────────────────────────────────────────────────────────

function Legend() {
  return (
    <div className="flex flex-wrap gap-3 text-xs">
      {[
        { color: 'bg-green-100 text-green-700', label: 'Improvement' },
        { color: 'bg-red-100 text-red-700',     label: 'Decline' },
        { color: 'bg-yellow-100 text-yellow-700', label: 'Changed' },
      ].map(({ color, label }) => (
        <span key={label} className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-medium ${color}`}>
          {label}
        </span>
      ))}
    </div>
  )
}

// ── Person diff table ─────────────────────────────────────────────────────────

function PersonDiff({ personA, personB }) {
  const keys = new Set([
    ...Object.keys(personA?.diff_fields ?? {}),
    'gender', 'civil_status', 'educational_attainment', 'role',
  ])

  return (
    <div className="rounded-lg border border-gray-100 overflow-hidden">
      <div className="bg-gray-50 px-4 py-2 grid grid-cols-3 gap-2 text-xs font-semibold text-gray-500">
        <span>Field</span>
        <span>{personA?.survey_year ?? 'Survey A'}</span>
        <span>{personB?.survey_year ?? 'Survey B'}</span>
      </div>
      {[...keys].map((k) => (
        <DiffRow
          key={k}
          label={k}
          oldVal={personA?.[k] ?? personA?.diff_fields?.[k]?.a}
          newVal={personB?.[k] ?? personB?.diff_fields?.[k]?.b}
        />
      ))}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function HouseholdComparison() {
  const navigate = useNavigate()
  const toast    = useToast()

  // Household search
  const [search,     setSearch]     = useState('')
  const [searchRes,  setSearchRes]  = useState([])
  const [searching,  setSearching]  = useState(false)
  const [household,  setHousehold]  = useState(null)

  // Survey selection
  const [surveys,  setSurveys]  = useState([])
  const [surveyA,  setSurveyA]  = useState('')
  const [surveyB,  setSurveyB]  = useState('')

  // Comparison result
  const [result,   setResult]   = useState(null)
  const [loading,  setLoading]  = useState(false)

  const debouncedSearch = useDebounce(search, 350)

  useEffect(() => {
    if (!debouncedSearch) { setSearchRes([]); return }
    setSearching(true)
    getHouseholds({ search: debouncedSearch, page_size: 8 })
      .then(({ data }) => setSearchRes(data.results ?? []))
      .catch(() => {})
      .finally(() => setSearching(false))
  }, [debouncedSearch])

  const selectHousehold = async (hh) => {
    setHousehold(hh)
    setSearch('')
    setSearchRes([])
    setResult(null)
    setSurveyA('')
    setSurveyB('')
    try {
      const { data } = await getHouseholdSurveys(hh.id, { page_size: 50 })
      setSurveys(data.results ?? [])
    } catch {
      toast('Failed to load surveys for this household', 'error')
    }
  }

  const handleCompare = async () => {
    if (!surveyA || !surveyB || surveyA === surveyB) return
    setLoading(true)
    setResult(null)
    try {
      const { data } = await compareSurveys(surveyA, surveyB)
      setResult(data)
    } catch (err) {
      toast(err.response?.data?.detail ?? 'Comparison failed', 'error')
    } finally {
      setLoading(false)
    }
  }

  const surveyOptions = surveys.map((s) => ({
    value: s.id,
    label: `${s.survey_year} — ${s.status}`,
  }))

  return (
    <div className="max-w-4xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/profiling')}
          className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ChevronLeft size={18} />
        </button>
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-50 rounded-lg">
            <GitCompare size={20} className="text-purple-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Survey Comparison</h1>
            <p className="text-sm text-gray-500">Side-by-side view of household changes across years</p>
          </div>
        </div>
      </div>

      {/* Household selector */}
      <Card>
        <CardHeader title="Select Household" />
        <CardBody>
          {household ? (
            <div className="flex items-center gap-3">
              <div className="flex-1 p-3 bg-purple-50 border border-purple-200 rounded-xl text-sm">
                <p className="font-semibold text-purple-900">#{household.household_number}</p>
                <p className="text-purple-700">{household.address}</p>
              </div>
              <Button
                variant="secondary"
                onClick={() => { setHousehold(null); setSurveys([]); setResult(null) }}
              >
                Change
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="relative">
                <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search household by number or address…"
                  className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-gray-300
                    focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>
              {searching && <p className="text-sm text-gray-400">Searching…</p>}
              {searchRes.length > 0 && (
                <div className="border border-gray-200 rounded-xl overflow-hidden divide-y divide-gray-100">
                  {searchRes.map((hh) => (
                    <button
                      key={hh.id}
                      className="w-full flex items-center gap-3 px-4 py-3 hover:bg-purple-50 transition-colors text-left"
                      onClick={() => selectHousehold(hh)}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900">#{hh.household_number}</p>
                        <p className="text-xs text-gray-500 truncate">{hh.address}</p>
                      </div>
                      <Badge color="gray">{hh.surveys_count ?? 0} surveys</Badge>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </CardBody>
      </Card>

      {/* Survey year selector */}
      {household && surveys.length > 0 && (
        <Card>
          <CardHeader title="Select Two Surveys to Compare" />
          <CardBody>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="block text-sm font-medium text-gray-700">Survey A (Baseline)</label>
                <select
                  value={surveyA}
                  onChange={(e) => setSurveyA(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm
                    focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                >
                  <option value="">— Select —</option>
                  {surveyOptions.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-1">
                <label className="block text-sm font-medium text-gray-700">Survey B (Comparison)</label>
                <select
                  value={surveyB}
                  onChange={(e) => setSurveyB(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm
                    focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                >
                  <option value="">— Select —</option>
                  {surveyOptions
                    .filter((o) => o.value !== surveyA)
                    .map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                </select>
              </div>
            </div>
            <div className="mt-4 flex items-center gap-3">
              <Button
                onClick={handleCompare}
                disabled={!surveyA || !surveyB || loading}
                className="gap-2"
              >
                <GitCompare size={15} />
                {loading ? 'Comparing…' : 'Compare Surveys'}
              </Button>
              {loading && <Spinner size="sm" />}
            </div>
          </CardBody>
        </Card>
      )}

      {household && surveys.length === 0 && (
        <div className="flex flex-col items-center gap-2 py-12 text-gray-400">
          <AlertCircle size={36} />
          <p className="text-sm">This household has no surveys yet.</p>
          <Button onClick={() => navigate(`/profiling/wizard?household=${household.id}`)}>
            Create First Survey
          </Button>
        </div>
      )}

      {/* Comparison result */}
      {result && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-gray-900">Comparison Results</h2>
            <Legend />
          </div>

          {result.normalized_data_warning && (
            <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-xl text-sm text-amber-800">
              <AlertCircle size={15} className="mt-0.5 shrink-0" />
              Normalized data is not available for one or both surveys. Comparison may be incomplete.
            </div>
          )}

          {/* Household-level diff */}
          {result.household_level && Object.keys(result.household_level).length > 0 && (
            <Card>
              <CardHeader title="Household-Level Changes" />
              <div className="overflow-hidden">
                <div className="bg-gray-50 px-4 py-2 grid grid-cols-3 gap-2 text-xs font-semibold text-gray-500">
                  <span>Field</span>
                  <span>Survey A ({result.survey_a?.survey_year})</span>
                  <span>Survey B ({result.survey_b?.survey_year})</span>
                </div>
                {Object.entries(result.household_level).map(([key, diff]) => (
                  <DiffRow
                    key={key}
                    label={key}
                    oldVal={diff.a ?? diff.old}
                    newVal={diff.b ?? diff.new}
                  />
                ))}
              </div>
            </Card>
          )}

          {/* Families diff */}
          {result.families?.map((fam, i) => (
            <Card key={i}>
              <CardHeader
                title={`Family ${fam.family_number ?? i + 1}`}
                subtitle={
                  fam.status === 'only_in_a' ? 'Removed in Survey B' :
                  fam.status === 'only_in_b' ? 'New in Survey B' : 'Matched'
                }
              />
              <CardBody>
                {fam.status === 'only_in_a' && (
                  <p className="text-sm text-red-500">This family was not found in Survey B.</p>
                )}
                {fam.status === 'only_in_b' && (
                  <p className="text-sm text-green-600">This family is new in Survey B.</p>
                )}
                {fam.persons?.map((person, j) => (
                  <div key={j} className="mb-3">
                    <p className="text-xs font-semibold text-gray-500 mb-1 flex items-center gap-2">
                      Person: {person.name ?? `Member ${j + 1}`}
                      {person.status === 'only_in_a' && <Badge color="red">Removed</Badge>}
                      {person.status === 'only_in_b' && <Badge color="green">New</Badge>}
                    </p>
                    {person.diff_fields && Object.keys(person.diff_fields).length > 0 && (
                      <PersonDiff personA={person.diff_fields} personB={person.diff_fields_b} />
                    )}
                  </div>
                ))}
              </CardBody>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

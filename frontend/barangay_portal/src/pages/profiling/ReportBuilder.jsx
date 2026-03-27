/**
 * ReportBuilder
 * ────────────────────────────────────────────────────────────────────────────
 * Select entity type → configure filters → choose format → generate & download.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  FileBarChart2, ChevronLeft, Download, FileSpreadsheet,
  FileText, CheckCircle, AlertCircle, RefreshCw,
} from 'lucide-react'
import { generateReport } from '../../api/profilingApi'
import { useToast } from '../../context/ToastContext'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'

const CURRENT_YEAR = new Date().getFullYear()

// ── Entity configs ────────────────────────────────────────────────────────────

const ENTITY_TYPES = [
  {
    value:       'household',
    label:       'Households',
    description: 'All household records with address, status, and purok',
    icon:        '🏠',
  },
  {
    value:       'survey',
    label:       'Surveys',
    description: 'Household survey records with year, status, and encoded data',
    icon:        '📋',
  },
  {
    value:       'family',
    label:       'Families',
    description: 'Family records with income bracket and survey linkage',
    icon:        '👨‍👩‍👧',
  },
  {
    value:       'person',
    label:       'Persons',
    description: 'Individual persons — demographics, sectors, education',
    icon:        '👤',
  },
  {
    value:       'program',
    label:       'Programs Availed',
    description: 'Government programs and assistance records',
    icon:        '🎁',
  },
]

const FORMATS = [
  { value: 'csv',   label: 'CSV',   icon: FileText,        desc: 'Compatible with Excel, Google Sheets' },
  { value: 'excel', label: 'Excel', icon: FileSpreadsheet, desc: 'Native .xlsx workbook' },
]

const SURVEY_STATUSES = [
  { value: '',          label: 'All Statuses' },
  { value: 'DRAFT',     label: 'Draft' },
  { value: 'SUBMITTED', label: 'Submitted' },
  { value: 'VERIFIED',  label: 'Verified' },
  { value: 'REVISION',  label: 'Revision' },
]

const INCOME_BRACKETS = [
  { value: '',          label: 'All Brackets' },
  { value: 'NO_INCOME', label: 'No Income' },
  { value: 'BELOW_5K',  label: 'Below ₱5,000' },
  { value: '5K_10K',    label: '₱5,000 – ₱10,000' },
  { value: '10K_20K',   label: '₱10,000 – ₱20,000' },
  { value: '20K_30K',   label: '₱20,000 – ₱30,000' },
  { value: '30K_50K',   label: '₱30,000 – ₱50,000' },
  { value: 'ABOVE_50K', label: 'Above ₱50,000' },
]

const GENDERS = [
  { value: '',       label: 'All Genders' },
  { value: 'MALE',   label: 'Male' },
  { value: 'FEMALE', label: 'Female' },
  { value: 'OTHER',  label: 'Other' },
]

const SECTOR_OPTIONS = [
  { value: '',            label: 'Any / None' },
  { value: 'PWD',         label: 'PWD' },
  { value: 'SENIOR',      label: 'Senior Citizen' },
  { value: '4PS',         label: '4Ps' },
  { value: 'SOLO_PARENT', label: 'Solo Parent' },
  { value: 'INDIGENOUS',  label: 'Indigenous People' },
]

// ── Filter panels per entity ──────────────────────────────────────────────────

function HouseholdFilters({ filters, onChange }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div className="space-y-1">
        <label className="block text-sm font-medium text-gray-700">Purok #</label>
        <input type="number" value={filters.purok ?? ''} placeholder="Any"
          onChange={(e) => onChange({ purok: e.target.value || undefined })}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm
            focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
      </div>
      <Select label="Status"
        value={filters.status ?? ''}
        onChange={(e) => onChange({ status: e.target.value || undefined })}
        options={SURVEY_STATUSES.slice(0, 2).concat([
          { value: 'ACTIVE',     label: 'Active' },
          { value: 'VACANT',     label: 'Vacant' },
          { value: 'ABANDONED',  label: 'Abandoned' },
          { value: 'DEMOLISHED', label: 'Demolished' },
        ])}
      />
    </div>
  )
}

function SurveyFilters({ filters, onChange }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <Input label="Year From" type="number" value={filters.year_min ?? ''}
        placeholder={String(CURRENT_YEAR - 3)}
        onChange={(e) => onChange({ year_min: e.target.value || undefined })} />
      <Input label="Year To" type="number" value={filters.year_max ?? ''}
        placeholder={String(CURRENT_YEAR)}
        onChange={(e) => onChange({ year_max: e.target.value || undefined })} />
      <Select label="Status" value={filters.status ?? ''}
        onChange={(e) => onChange({ status: e.target.value || undefined })}
        options={SURVEY_STATUSES} />
    </div>
  )
}

function FamilyFilters({ filters, onChange }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <Input label="Survey Year" type="number" value={filters.survey_year ?? ''}
        placeholder={String(CURRENT_YEAR)}
        onChange={(e) => onChange({ survey_year: e.target.value || undefined })} />
      <div className="space-y-1">
        <label className="block text-sm font-medium text-gray-700">Purok #</label>
        <input type="number" value={filters.purok ?? ''} placeholder="Any"
          onChange={(e) => onChange({ purok: e.target.value || undefined })}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm
            focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
      </div>
      <Select label="Income Bracket" value={filters.income_bracket ?? ''}
        onChange={(e) => onChange({ income_bracket: e.target.value || undefined })}
        options={INCOME_BRACKETS} />
    </div>
  )
}

function PersonFilters({ filters, onChange }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <Input label="Survey Year" type="number" value={filters.survey_year ?? ''}
        placeholder={String(CURRENT_YEAR)}
        onChange={(e) => onChange({ survey_year: e.target.value || undefined })} />
      <Select label="Gender" value={filters.gender ?? ''}
        onChange={(e) => onChange({ gender: e.target.value || undefined })}
        options={GENDERS} />
      <Select label="Sector" value={filters.sector ?? ''}
        onChange={(e) => onChange({ sector: e.target.value || undefined })}
        options={SECTOR_OPTIONS} />
      <Input label="Age Min" type="number" value={filters.age_min ?? ''} placeholder="0"
        onChange={(e) => onChange({ age_min: e.target.value || undefined })} />
      <Input label="Age Max" type="number" value={filters.age_max ?? ''} placeholder="120"
        onChange={(e) => onChange({ age_max: e.target.value || undefined })} />
      <div className="space-y-1">
        <label className="block text-sm font-medium text-gray-700">Purok #</label>
        <input type="number" value={filters.purok ?? ''} placeholder="Any"
          onChange={(e) => onChange({ purok: e.target.value || undefined })}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm
            focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
      </div>
    </div>
  )
}

function ProgramFilters({ filters, onChange }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <Input label="Survey Year" type="number" value={filters.survey_year ?? ''}
        placeholder={String(CURRENT_YEAR)}
        onChange={(e) => onChange({ survey_year: e.target.value || undefined })} />
      <Input label="Date From" type="date" value={filters.date_from ?? ''}
        onChange={(e) => onChange({ date_from: e.target.value || undefined })} />
      <Input label="Date To" type="date" value={filters.date_to ?? ''}
        onChange={(e) => onChange({ date_to: e.target.value || undefined })} />
    </div>
  )
}

const FILTER_COMPONENTS = {
  household: HouseholdFilters,
  survey:    SurveyFilters,
  family:    FamilyFilters,
  person:    PersonFilters,
  program:   ProgramFilters,
}

// ── Download helper ───────────────────────────────────────────────────────────

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a   = document.createElement('a')
  a.href     = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

// ── Main component ────────────────────────────────────────────────────────────

export default function ReportBuilder() {
  const navigate = useNavigate()
  const toast    = useToast()

  const [entityType,  setEntityType]  = useState('')
  const [filters,     setFilters]     = useState({})
  const [format,      setFormat]      = useState('csv')
  const [generating,  setGenerating]  = useState(false)
  const [lastReport,  setLastReport]  = useState(null) // { filename, size, ts }

  const patchFilters = (patch) => setFilters((f) => ({ ...f, ...patch }))

  const handleEntityChange = (val) => {
    setEntityType(val)
    setFilters({})
    setLastReport(null)
  }

  const handleGenerate = async () => {
    if (!entityType) return
    setGenerating(true)
    try {
      const { data: blob, headers } = await generateReport({
        entity_type: entityType,
        filters:     filters,
        format:      format,
      })

      // Derive filename from Content-Disposition or fallback
      const cd       = headers['content-disposition'] ?? ''
      const match    = cd.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
      const filename = match?.[1]?.replace(/['"]/g, '') ??
        `${entityType}_report_${new Date().toISOString().slice(0, 10)}.${format === 'excel' ? 'xlsx' : 'csv'}`

      downloadBlob(blob, filename)

      const sizeKb = Math.round(blob.size / 1024)
      setLastReport({ filename, size: sizeKb, ts: new Date().toLocaleTimeString() })
      toast(`Report downloaded: ${filename}`, 'success')
    } catch (err) {
      // Blob error responses need to be parsed differently
      if (err.response?.data instanceof Blob) {
        const text = await err.response.data.text()
        try {
          const parsed = JSON.parse(text)
          toast(parsed?.detail ?? 'Report generation failed', 'error')
        } catch {
          toast('Report generation failed', 'error')
        }
      } else {
        toast(err.response?.data?.detail ?? 'Report generation failed', 'error')
      }
    } finally {
      setGenerating(false)
    }
  }

  const FilterComponent = entityType ? FILTER_COMPONENTS[entityType] : null
  const activeFiltersCount = Object.values(filters).filter(Boolean).length

  return (
    <div className="max-w-3xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/profiling')}
          className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ChevronLeft size={18} />
        </button>
        <div className="flex items-center gap-3">
          <div className="p-2 bg-green-50 rounded-lg">
            <FileBarChart2 size={20} className="text-green-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Report Builder</h1>
            <p className="text-sm text-gray-500">Generate and download data exports</p>
          </div>
        </div>
      </div>

      {/* Step 1 — Entity type */}
      <Card>
        <CardHeader title="1. Select Data Type" />
        <CardBody>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {ENTITY_TYPES.map((e) => (
              <button
                key={e.value}
                onClick={() => handleEntityChange(e.value)}
                className={`flex items-start gap-3 p-3 rounded-xl border text-left transition-all
                  ${entityType === e.value
                    ? 'border-blue-500 bg-blue-50 ring-1 ring-blue-300'
                    : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'}`}
              >
                <span className="text-xl shrink-0 mt-0.5">{e.icon}</span>
                <div>
                  <p className={`text-sm font-medium ${entityType === e.value ? 'text-blue-800' : 'text-gray-800'}`}>
                    {e.label}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{e.description}</p>
                </div>
              </button>
            ))}
          </div>
        </CardBody>
      </Card>

      {/* Step 2 — Filters */}
      {FilterComponent && (
        <Card>
          <CardHeader
            title="2. Apply Filters"
            subtitle={`${activeFiltersCount} filter(s) active`}
            actions={
              activeFiltersCount > 0 && (
                <button
                  onClick={() => setFilters({})}
                  className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1"
                >
                  <RefreshCw size={11} /> Reset
                </button>
              )
            }
          />
          <CardBody>
            <FilterComponent filters={filters} onChange={patchFilters} />
            <p className="text-xs text-gray-400 mt-3">
              Leave fields empty to include all records. Stricter filters produce smaller, faster exports.
            </p>
          </CardBody>
        </Card>
      )}

      {/* Step 3 — Format */}
      {entityType && (
        <Card>
          <CardHeader title="3. Choose Format" />
          <CardBody>
            <div className="flex gap-3">
              {FORMATS.map((f) => {
                const Icon = f.icon
                return (
                  <button
                    key={f.value}
                    onClick={() => setFormat(f.value)}
                    className={`flex-1 flex items-center gap-3 p-4 rounded-xl border transition-all
                      ${format === f.value
                        ? 'border-green-500 bg-green-50 ring-1 ring-green-300'
                        : 'border-gray-200 hover:border-gray-300'}`}
                  >
                    <Icon size={20} className={format === f.value ? 'text-green-600' : 'text-gray-400'} />
                    <div className="text-left">
                      <p className={`text-sm font-medium ${format === f.value ? 'text-green-800' : 'text-gray-800'}`}>
                        {f.label}
                      </p>
                      <p className="text-xs text-gray-500">{f.desc}</p>
                    </div>
                  </button>
                )
              })}
            </div>
          </CardBody>
        </Card>
      )}

      {/* Generate button */}
      {entityType && (
        <div className="space-y-3">
          <Button
            className="w-full justify-center py-3 gap-2 text-base"
            onClick={handleGenerate}
            disabled={generating}
          >
            {generating ? (
              <>
                <RefreshCw size={16} className="animate-spin" />
                Generating…
              </>
            ) : (
              <>
                <Download size={16} />
                Generate & Download {format.toUpperCase()}
              </>
            )}
          </Button>

          {lastReport && (
            <div className="flex items-start gap-3 p-3 bg-green-50 border border-green-200 rounded-xl">
              <CheckCircle size={16} className="text-green-600 shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="font-medium text-green-800">{lastReport.filename}</p>
                <p className="text-green-700 text-xs">
                  {lastReport.size} KB · Downloaded at {lastReport.ts}
                </p>
              </div>
            </div>
          )}

          <div className="flex items-start gap-2 p-3 bg-blue-50 border border-blue-100 rounded-xl text-xs text-blue-700">
            <AlertCircle size={13} className="shrink-0 mt-0.5" />
            <span>
              Large exports may take a few seconds. The file will download automatically when ready.
              CSV uses UTF-8 BOM encoding for proper display of Filipino characters in Excel.
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

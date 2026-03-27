/**
 * SurveyWizard  — 6-step household survey creation flow
 * ─────────────────────────────────────────────────────
 * Step 1 — Select / create Household
 * Step 2 — Survey metadata + dynamic form data
 * Step 3 — Add Families
 * Step 4 — Add Persons per Family
 * Step 5 — Add Programs per Family
 * Step 6 — Review & Submit
 */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import {
  Home, FileText, Users, User, Gift, CheckCircle,
  ChevronLeft, ChevronRight, Plus, Trash2, Search,
  AlertCircle, Check,
} from 'lucide-react'
import {
  getHouseholds, getFormSchemas, getFormSchema, createSurvey, createHousehold,
} from '../../api/profilingApi'
import { useToast } from '../../context/ToastContext'
import useDebounce from '../../hooks/useDebounce'
import DynamicFormRenderer from '../../components/profiling/DynamicFormRenderer'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import Modal from '../../components/ui/Modal'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'

// ── Choice constants ──────────────────────────────────────────────────────────

const INCOME_BRACKETS = [
  { value: 'NO_INCOME',  label: 'No Income' },
  { value: 'BELOW_5K',   label: 'Below ₱5,000' },
  { value: '5K_10K',     label: '₱5,000 – ₱10,000' },
  { value: '10K_20K',    label: '₱10,000 – ₱20,000' },
  { value: '20K_30K',    label: '₱20,000 – ₱30,000' },
  { value: '30K_50K',    label: '₱30,000 – ₱50,000' },
  { value: 'ABOVE_50K',  label: 'Above ₱50,000' },
]

const GENDERS = [
  { value: 'MALE',   label: 'Male' },
  { value: 'FEMALE', label: 'Female' },
  { value: 'OTHER',  label: 'Other' },
]

const CIVIL_STATUSES = [
  { value: 'SINGLE',    label: 'Single' },
  { value: 'MARRIED',   label: 'Married' },
  { value: 'WIDOWED',   label: 'Widowed' },
  { value: 'SEPARATED', label: 'Separated' },
  { value: 'ANNULLED',  label: 'Annulled' },
  { value: 'LIVE_IN',   label: 'Live-in' },
]

const PERSON_ROLES = [
  { value: 'HEAD',         label: 'Head' },
  { value: 'SPOUSE',       label: 'Spouse / Partner' },
  { value: 'CHILD',        label: 'Child' },
  { value: 'PARENT',       label: 'Parent of Head' },
  { value: 'SIBLING',      label: 'Sibling' },
  { value: 'RELATIVE',     label: 'Other Relative' },
  { value: 'NON_RELATIVE', label: 'Non-Relative' },
]

const EDUCATIONAL_ATTAINMENTS = [
  { value: 'NO_FORMAL',    label: 'No Formal Education' },
  { value: 'KINDER',       label: 'Kindergarten' },
  { value: 'ELEM',         label: 'Elementary (Ongoing)' },
  { value: 'ELEM_GRAD',    label: 'Elementary Graduate' },
  { value: 'JHS',          label: 'Junior High School (Ongoing)' },
  { value: 'JHS_GRAD',     label: 'Junior High School Graduate' },
  { value: 'SHS',          label: 'Senior High School (Ongoing)' },
  { value: 'SHS_GRAD',     label: 'Senior High School Graduate' },
  { value: 'VOCATIONAL',   label: 'Vocational / TESDA' },
  { value: 'COLLEGE',      label: 'College (Ongoing)' },
  { value: 'COLLEGE_GRAD', label: 'College Graduate' },
  { value: 'POST_GRAD',    label: 'Post-Graduate' },
]

const SECTOR_OPTIONS = [
  { value: 'PWD',         label: 'PWD (Person with Disability)' },
  { value: 'SENIOR',      label: 'Senior Citizen (60+)' },
  { value: '4PS',         label: '4Ps Beneficiary' },
  { value: 'SOLO_PARENT', label: 'Solo Parent' },
  { value: 'INDIGENOUS',  label: 'Indigenous People' },
  { value: 'LACTATING',   label: 'Lactating Mother' },
  { value: 'PREGNANT',    label: 'Pregnant' },
]

const PROGRAM_TYPES = [
  { value: 'FINANCIAL',    label: 'Financial Assistance' },
  { value: 'EDUCATIONAL',  label: 'Educational Assistance' },
  { value: 'MEDICAL',      label: 'Medical Assistance' },
  { value: 'LIVELIHOOD',   label: 'Livelihood Program' },
  { value: '4PS',          label: '4Ps (Pantawid Pamilyang)' },
  { value: 'PHILHEALTH',   label: 'PhilHealth' },
  { value: 'SSS',          label: 'SSS' },
  { value: 'GSIS',         label: 'GSIS' },
  { value: 'OTHER',        label: 'Other' },
]

const HOUSEHOLD_STATUSES = [
  { value: 'ACTIVE',     label: 'Active' },
  { value: 'VACANT',     label: 'Vacant' },
  { value: 'ABANDONED',  label: 'Abandoned' },
  { value: 'DEMOLISHED', label: 'Demolished' },
]

// ── Step indicator ────────────────────────────────────────────────────────────

const STEPS = [
  { n: 1, label: 'Household', icon: Home },
  { n: 2, label: 'Survey',    icon: FileText },
  { n: 3, label: 'Families',  icon: Users },
  { n: 4, label: 'Persons',   icon: User },
  { n: 5, label: 'Programs',  icon: Gift },
  { n: 6, label: 'Review',    icon: CheckCircle },
]

function StepIndicator({ currentStep }) {
  return (
    <div className="flex items-center gap-0 overflow-x-auto pb-1">
      {STEPS.map(({ n, label, icon: Icon }, i) => {
        const done    = n < currentStep
        const active  = n === currentStep
        const pending = n > currentStep
        return (
          <div key={n} className="flex items-center shrink-0">
            <div className="flex flex-col items-center gap-1">
              <div
                className={`w-9 h-9 rounded-full flex items-center justify-center transition-colors
                  ${done   ? 'bg-green-500 text-white'
                  : active ? 'bg-blue-600 text-white ring-2 ring-blue-200'
                  :          'bg-gray-100 text-gray-400'}`}
              >
                {done ? <Check size={16} /> : <Icon size={16} />}
              </div>
              <span
                className={`text-xs font-medium transition-colors
                  ${active ? 'text-blue-600' : done ? 'text-green-600' : 'text-gray-400'}`}
              >
                {label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div
                className={`w-12 h-0.5 mx-1 mb-5 transition-colors
                  ${n < currentStep ? 'bg-green-400' : 'bg-gray-200'}`}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

// ── Step 1 — Household ────────────────────────────────────────────────────────

function Step1Household({ data, onChange }) {
  const [search,   setSearch]   = useState('')
  const [results,  setResults]  = useState([])
  const [loading,  setLoading]  = useState(false)
  const [showNew,  setShowNew]  = useState(false)
  const [newForm,  setNewForm]  = useState({ household_number: '', address: '', status: 'ACTIVE' })

  const debouncedSearch = useDebounce(search, 350)

  useEffect(() => {
    if (!debouncedSearch) { setResults([]); return }
    setLoading(true)
    getHouseholds({ search: debouncedSearch, page_size: 10 })
      .then(({ data: d }) => setResults(d.results ?? []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [debouncedSearch])

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">Select Household</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          Search for an existing household or create a new one.
        </p>
      </div>

      {data.household && (
        <div className="flex items-start gap-3 p-3 bg-blue-50 border border-blue-200 rounded-xl">
          <Home size={16} className="text-blue-600 mt-0.5 shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-blue-900">
              #{data.household.household_number}
            </p>
            <p className="text-xs text-blue-700">{data.household.address}</p>
          </div>
          <button
            onClick={() => onChange({ household: null })}
            className="text-xs text-blue-600 hover:text-blue-800 font-medium"
          >
            Change
          </button>
        </div>
      )}

      {!data.household && (
        <>
          <div className="relative">
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

          {loading && (
            <p className="text-sm text-gray-400 text-center py-2">Searching…</p>
          )}

          {results.length > 0 && (
            <div className="border border-gray-200 rounded-xl overflow-hidden divide-y divide-gray-100">
              {results.map((hh) => (
                <button
                  key={hh.id}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-blue-50 transition-colors text-left"
                  onClick={() => { onChange({ household: hh }); setSearch(''); setResults([]) }}
                >
                  <Home size={15} className="text-gray-400 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      #{hh.household_number}
                    </p>
                    <p className="text-xs text-gray-500 truncate">{hh.address}</p>
                  </div>
                  <Badge color="gray">{hh.status}</Badge>
                  <ChevronRight size={14} className="text-gray-300 shrink-0" />
                </button>
              ))}
            </div>
          )}

          {search && !loading && results.length === 0 && (
            <p className="text-sm text-gray-400 text-center py-2">No households match "{search}"</p>
          )}

          <div className="border-t border-gray-100 pt-4">
            <button
              onClick={() => setShowNew(true)}
              className="flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-800"
            >
              <Plus size={15} />
              Register a new household
            </button>
          </div>
        </>
      )}

      {/* New household modal */}
      <Modal
        isOpen={showNew}
        onClose={() => setShowNew(false)}
        title="Register New Household"
        size="md"
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setShowNew(false)}>Cancel</Button>
            <Button
              onClick={() => {
                if (!newForm.household_number || !newForm.address) return
                onChange({ household: { ...newForm, id: null, _isNew: true } })
                setShowNew(false)
              }}
            >
              Use This Household
            </Button>
          </div>
        }
      >
        <div className="space-y-4">
          <Input
            label="Household Number"
            value={newForm.household_number}
            onChange={(e) => setNewForm(f => ({ ...f, household_number: e.target.value }))}
            placeholder="e.g. 2024-001"
            required
          />
          <Input
            label="Address / Street"
            value={newForm.address}
            onChange={(e) => setNewForm(f => ({ ...f, address: e.target.value }))}
            placeholder="Full address"
            required
          />
          <Select
            label="Status"
            value={newForm.status}
            onChange={(e) => setNewForm(f => ({ ...f, status: e.target.value }))}
            options={HOUSEHOLD_STATUSES}
          />
        </div>
      </Modal>
    </div>
  )
}

// ── Step 2 — Survey Metadata ──────────────────────────────────────────────────

function Step2Survey({ data, onChange }) {
  const [schemas,        setSchemas]       = useState([])
  const [loadingSchema,  setLoadingSchema] = useState(false)
  const [selectedSchema, setSelectedSchema] = useState(data.formSchema ?? null)

  const {
    register, control, formState: { errors }, getValues, trigger,
  } = useForm({
    defaultValues: data.surveyData ?? {},
  })

  // Expose validation + save fns to parent via onChange when step loads
  useEffect(() => {
    onChange({
      _step2Validate: async () => {
        const ok = await trigger()
        if (ok) onChange({ surveyData: getValues() })
        return ok
      },
      _step2Save: () => onChange({ surveyData: getValues() }),
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trigger, getValues])

  useEffect(() => {
    getFormSchemas({ page_size: 100 })
      .then(({ data: d }) => setSchemas(d.results ?? []))
      .catch(() => {})
  }, [])

  const handleSchemaChange = async (id) => {
    if (!id) { setSelectedSchema(null); onChange({ formSchema: null }); return }
    setLoadingSchema(true)
    try {
      const { data: s } = await getFormSchema(id)
      setSelectedSchema(s)
      onChange({ formSchema: s })
    } catch {
      //
    } finally {
      setLoadingSchema(false)
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">Survey Details</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          Select the survey year and form schema, then fill in the household-level data.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Input
          label="Survey Year"
          type="number"
          defaultValue={data.survey_year ?? new Date().getFullYear()}
          min={2000}
          max={2100}
          onChange={(e) => onChange({ survey_year: Number(e.target.value) })}
        />
        <Select
          label="Form Schema"
          value={data.formSchema?.id ?? ''}
          onChange={(e) => handleSchemaChange(e.target.value)}
          placeholder="— Select schema —"
          options={schemas.map((s) => ({
            value: s.id,
            label: `${s.name} (v${s.version ?? 1})`,
          }))}
        />
      </div>

      {loadingSchema && (
        <p className="text-sm text-gray-400">Loading schema fields…</p>
      )}

      {selectedSchema?.schema && (
        <div className="border border-gray-200 rounded-xl p-4 space-y-2">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
            Household-Level Fields
          </p>
          <DynamicFormRenderer
            schema={selectedSchema.schema}
            register={register}
            control={control}
            errors={errors}
            level="household"
          />
        </div>
      )}
    </div>
  )
}

// ── Step 3 — Families ─────────────────────────────────────────────────────────

function Step3Families({ data, onChange }) {
  const [showAdd, setShowAdd]   = useState(false)
  const [form,    setForm]      = useState({ monthly_income_bracket: '' })

  const addFamily = () => {
    if (!form.monthly_income_bracket) return
    onChange({
      families: [
        ...data.families,
        {
          _id:    crypto.randomUUID(),
          monthly_income_bracket: form.monthly_income_bracket,
          data:     {},
          persons:  [],
          programs: [],
        },
      ],
    })
    setForm({ monthly_income_bracket: '' })
    setShowAdd(false)
  }

  const removeFamily = (id) =>
    onChange({ families: data.families.filter((f) => f._id !== id) })

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Families</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            Add each family unit in the household.
          </p>
        </div>
        <Button className="gap-2" onClick={() => setShowAdd(true)}>
          <Plus size={15} />
          Add Family
        </Button>
      </div>

      {data.families.length === 0 && (
        <div className="flex flex-col items-center gap-2 py-12 text-gray-400">
          <Users size={36} />
          <p className="text-sm">No families added yet. Add at least one family.</p>
        </div>
      )}

      <div className="space-y-2">
        {data.families.map((fam, i) => (
          <div
            key={fam._id}
            className="flex items-center gap-3 p-3 bg-white border border-gray-200 rounded-xl"
          >
            <div className="w-8 h-8 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-sm font-bold shrink-0">
              {i + 1}
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">Family {i + 1}</p>
              <p className="text-xs text-gray-500">
                Income: {INCOME_BRACKETS.find((b) => b.value === fam.monthly_income_bracket)?.label ?? fam.monthly_income_bracket}
                {' · '}
                {fam.persons.length} person(s)
                {fam.programs.length > 0 && ` · ${fam.programs.length} program(s)`}
              </p>
            </div>
            <button
              onClick={() => removeFamily(fam._id)}
              className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>

      <Modal
        isOpen={showAdd}
        onClose={() => setShowAdd(false)}
        title="Add Family"
        size="sm"
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setShowAdd(false)}>Cancel</Button>
            <Button onClick={addFamily} disabled={!form.monthly_income_bracket}>Add Family</Button>
          </div>
        }
      >
        <Select
          label="Monthly Income Bracket"
          value={form.monthly_income_bracket}
          onChange={(e) => setForm({ monthly_income_bracket: e.target.value })}
          placeholder="— Select bracket —"
          options={INCOME_BRACKETS}
        />
      </Modal>
    </div>
  )
}

// ── Step 4 — Persons ──────────────────────────────────────────────────────────

const EMPTY_PERSON = {
  first_name: '', last_name: '', middle_name: '',
  date_of_birth: '', gender: '', civil_status: '',
  role: '', educational_attainment: '', occupation: '',
  age_at_survey: '', is_registered_voter: false, sectors: [],
}

function PersonModal({ isOpen, onClose, onSave, initial }) {
  const [form, setForm] = useState(initial ?? EMPTY_PERSON)
  const upd = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const toggleSector = (val) =>
    setForm((f) => ({
      ...f,
      sectors: f.sectors.includes(val)
        ? f.sectors.filter((s) => s !== val)
        : [...f.sectors, val],
    }))

  const handleSave = () => {
    if (!form.first_name || !form.last_name || !form.gender || !form.role) return
    onSave(form)
    onClose()
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={initial ? 'Edit Person' : 'Add Person'}
      size="xl"
      footer={
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSave}>Save Person</Button>
        </div>
      }
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Input label="Last Name *"    value={form.last_name}    onChange={upd('last_name')} />
        <Input label="First Name *"   value={form.first_name}   onChange={upd('first_name')} />
        <Input label="Middle Name"    value={form.middle_name}  onChange={upd('middle_name')} />
        <Input label="Date of Birth"  type="date" value={form.date_of_birth} onChange={upd('date_of_birth')} />
        <Select label="Gender *"     value={form.gender}     onChange={upd('gender')}     options={GENDERS} placeholder="— Select —" />
        <Select label="Civil Status" value={form.civil_status} onChange={upd('civil_status')} options={CIVIL_STATUSES} placeholder="— Select —" />
        <Select label="Role in Family *" value={form.role} onChange={upd('role')} options={PERSON_ROLES} placeholder="— Select —" />
        <Select label="Educational Attainment" value={form.educational_attainment} onChange={upd('educational_attainment')} options={EDUCATIONAL_ATTAINMENTS} placeholder="— Select —" />
        <Input label="Occupation" value={form.occupation} onChange={upd('occupation')} />
        <Input label="Age at Survey" type="number" value={form.age_at_survey} onChange={upd('age_at_survey')} placeholder="Auto-computed if blank" />

        <div className="sm:col-span-2 space-y-2">
          <label className="block text-sm font-medium text-gray-700">Sectors</label>
          <div className="flex flex-wrap gap-x-4 gap-y-2">
            {SECTOR_OPTIONS.map((s) => (
              <label key={s.value} className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  className="w-4 h-4 accent-blue-600 rounded"
                  checked={form.sectors.includes(s.value)}
                  onChange={() => toggleSector(s.value)}
                />
                <span className="text-sm text-gray-700">{s.label}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="sm:col-span-2">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              className="w-4 h-4 accent-blue-600 rounded"
              checked={form.is_registered_voter}
              onChange={(e) => setForm((f) => ({ ...f, is_registered_voter: e.target.checked }))}
            />
            <span className="text-sm font-medium text-gray-700">Registered Voter</span>
          </label>
        </div>
      </div>
    </Modal>
  )
}

function Step4Persons({ data, onChange }) {
  const [activeFam,   setActiveFam]   = useState(data.families[0]?._id ?? null)
  const [showModal,   setShowModal]   = useState(false)
  const [editIdx,     setEditIdx]     = useState(null)

  const family = data.families.find((f) => f._id === activeFam)

  const updateFamily = (upd) =>
    onChange({
      families: data.families.map((f) => f._id === activeFam ? { ...f, ...upd } : f),
    })

  const handleSavePerson = (person) => {
    const persons = editIdx !== null
      ? family.persons.map((p, i) => (i === editIdx ? person : p))
      : [...family.persons, person]
    updateFamily({ persons })
    setEditIdx(null)
  }

  const removePerson = (idx) =>
    updateFamily({ persons: family.persons.filter((_, i) => i !== idx) })

  if (data.families.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 py-12 text-gray-400">
        <AlertCircle size={36} />
        <p className="text-sm">Go back to Step 3 and add at least one family first.</p>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">Persons per Family</h2>
        <p className="text-sm text-gray-500 mt-0.5">Add all household members for each family.</p>
      </div>

      {/* Family tabs */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {data.families.map((fam, i) => (
          <button
            key={fam._id}
            onClick={() => setActiveFam(fam._id)}
            className={`shrink-0 px-4 py-2 rounded-lg text-sm font-medium transition-colors
              ${activeFam === fam._id
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
          >
            Family {i + 1}
            <span className="ml-1.5 text-xs opacity-75">({fam.persons.length})</span>
          </button>
        ))}
      </div>

      {family && (
        <>
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-gray-700">
              {family.persons.length} person(s) in this family
            </p>
            <Button className="gap-2" onClick={() => { setEditIdx(null); setShowModal(true) }}>
              <Plus size={15} />
              Add Person
            </Button>
          </div>

          <div className="space-y-2">
            {family.persons.map((p, idx) => (
              <div
                key={idx}
                className="flex items-center gap-3 p-3 bg-white border border-gray-200 rounded-xl"
              >
                <div className="w-8 h-8 bg-purple-100 text-purple-700 rounded-full flex items-center justify-center text-xs font-bold shrink-0">
                  {idx + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {p.last_name}, {p.first_name} {p.middle_name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {p.role} · {p.gender}
                    {p.date_of_birth && ` · DOB: ${p.date_of_birth}`}
                    {p.sectors?.length > 0 && ` · ${p.sectors.join(', ')}`}
                  </p>
                </div>
                <button
                  onClick={() => { setEditIdx(idx); setShowModal(true) }}
                  className="p-1.5 text-gray-400 hover:text-blue-500 hover:bg-blue-50 rounded-lg transition-colors"
                >
                  <FileText size={13} />
                </button>
                <button
                  onClick={() => removePerson(idx)}
                  className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            ))}
          </div>

          {family.persons.length === 0 && (
            <div className="flex flex-col items-center gap-2 py-8 text-gray-400 border-2 border-dashed border-gray-200 rounded-xl">
              <User size={28} />
              <p className="text-sm">No persons added to this family yet.</p>
            </div>
          )}
        </>
      )}

      <PersonModal
        isOpen={showModal}
        onClose={() => { setShowModal(false); setEditIdx(null) }}
        onSave={handleSavePerson}
        initial={editIdx !== null ? family?.persons[editIdx] : null}
      />
    </div>
  )
}

// ── Step 5 — Programs ─────────────────────────────────────────────────────────

const EMPTY_PROGRAM = {
  program_type: '', date_availed: '', amount: '', notes: '', beneficiary_index: 0,
}

function ProgramModal({ isOpen, onClose, onSave, persons, initial }) {
  const [form, setForm] = useState(initial ?? EMPTY_PROGRAM)
  const upd = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={initial ? 'Edit Program' : 'Add Program'}
      size="md"
      footer={
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button onClick={() => { onSave(form); onClose() }} disabled={!form.program_type}>
            Save Program
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        <Select
          label="Program Type *"
          value={form.program_type}
          onChange={upd('program_type')}
          placeholder="— Select program —"
          options={PROGRAM_TYPES}
        />
        <Input
          label="Date Availed"
          type="date"
          value={form.date_availed}
          onChange={upd('date_availed')}
        />
        <Input
          label="Amount (₱)"
          type="number"
          value={form.amount}
          onChange={upd('amount')}
          placeholder="Leave blank if not applicable"
        />
        <Select
          label="Beneficiary (Person)"
          value={form.beneficiary_index}
          onChange={(e) => setForm((f) => ({ ...f, beneficiary_index: Number(e.target.value) }))}
          options={persons.map((p, i) => ({
            value: i,
            label: `${i + 1}. ${p.last_name}, ${p.first_name}`,
          }))}
          placeholder="— None / household-level —"
        />
        <div className="space-y-1">
          <label className="block text-sm font-medium text-gray-700">Notes</label>
          <textarea
            rows={2}
            value={form.notes}
            onChange={upd('notes')}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm resize-none
              focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
        </div>
      </div>
    </Modal>
  )
}

function Step5Programs({ data, onChange }) {
  const [activeFam,  setActiveFam]  = useState(data.families[0]?._id ?? null)
  const [showModal,  setShowModal]  = useState(false)
  const [editIdx,    setEditIdx]    = useState(null)

  const family = data.families.find((f) => f._id === activeFam)

  const updateFamily = (upd) =>
    onChange({
      families: data.families.map((f) => f._id === activeFam ? { ...f, ...upd } : f),
    })

  const handleSaveProgram = (prog) => {
    const programs = editIdx !== null
      ? family.programs.map((p, i) => (i === editIdx ? prog : p))
      : [...family.programs, prog]
    updateFamily({ programs })
    setEditIdx(null)
  }

  const removeProgram = (idx) =>
    updateFamily({ programs: family.programs.filter((_, i) => i !== idx) })

  if (data.families.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 py-12 text-gray-400">
        <AlertCircle size={36} />
        <p className="text-sm">Go back to Step 3 and add at least one family first.</p>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">Programs Availed</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          Record government programs and assistance availed by each family.
          This step is optional.
        </p>
      </div>

      {/* Family tabs */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {data.families.map((fam, i) => (
          <button
            key={fam._id}
            onClick={() => setActiveFam(fam._id)}
            className={`shrink-0 px-4 py-2 rounded-lg text-sm font-medium transition-colors
              ${activeFam === fam._id
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
          >
            Family {i + 1}
            <span className="ml-1.5 text-xs opacity-75">({fam.programs.length})</span>
          </button>
        ))}
      </div>

      {family && (
        <>
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-gray-700">
              {family.programs.length} program(s) for this family
            </p>
            <Button className="gap-2" onClick={() => { setEditIdx(null); setShowModal(true) }}>
              <Plus size={15} />
              Add Program
            </Button>
          </div>

          <div className="space-y-2">
            {family.programs.map((prog, idx) => (
              <div
                key={idx}
                className="flex items-center gap-3 p-3 bg-white border border-gray-200 rounded-xl"
              >
                <div className="w-8 h-8 bg-green-100 text-green-700 rounded-full flex items-center justify-center shrink-0">
                  <Gift size={14} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900">
                    {PROGRAM_TYPES.find((t) => t.value === prog.program_type)?.label ?? prog.program_type}
                  </p>
                  <p className="text-xs text-gray-500">
                    {prog.date_availed && `Date: ${prog.date_availed}`}
                    {prog.amount && ` · ₱${Number(prog.amount).toLocaleString()}`}
                    {prog.beneficiary_index != null && family.persons[prog.beneficiary_index] &&
                      ` · ${family.persons[prog.beneficiary_index].first_name}`}
                  </p>
                </div>
                <button
                  onClick={() => { setEditIdx(idx); setShowModal(true) }}
                  className="p-1.5 text-gray-400 hover:text-blue-500 hover:bg-blue-50 rounded-lg transition-colors"
                >
                  <FileText size={13} />
                </button>
                <button
                  onClick={() => removeProgram(idx)}
                  className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            ))}
          </div>

          {family.programs.length === 0 && (
            <div className="flex flex-col items-center gap-2 py-8 text-gray-400 border-2 border-dashed border-gray-200 rounded-xl">
              <Gift size={28} />
              <p className="text-sm">No programs recorded. Add one or skip to Review.</p>
            </div>
          )}
        </>
      )}

      <ProgramModal
        isOpen={showModal}
        onClose={() => { setShowModal(false); setEditIdx(null) }}
        onSave={handleSaveProgram}
        persons={family?.persons ?? []}
        initial={editIdx !== null ? family?.programs[editIdx] : null}
      />
    </div>
  )
}

// ── Step 6 — Review & Submit ──────────────────────────────────────────────────

function Step6Review({ data }) {
  const totalPersons  = data.families.reduce((n, f) => n + f.persons.length,  0)
  const totalPrograms = data.families.reduce((n, f) => n + f.programs.length, 0)

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">Review & Submit</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          Verify everything looks correct before submitting.
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Households',  value: data.household ? 1 : 0,  color: 'text-blue-600' },
          { label: 'Families',    value: data.families.length,    color: 'text-purple-600' },
          { label: 'Persons',     value: totalPersons,            color: 'text-indigo-600' },
          { label: 'Programs',    value: totalPrograms,           color: 'text-green-600' },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-white border border-gray-200 rounded-xl p-3 text-center">
            <p className={`text-2xl font-bold ${color}`}>{value}</p>
            <p className="text-xs text-gray-500 mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      {/* Household */}
      <Card>
        <CardHeader title="Household" />
        <CardBody>
          {data.household ? (
            <div className="text-sm space-y-1">
              <p><span className="font-medium text-gray-600">Number:</span> #{data.household.household_number}</p>
              <p><span className="font-medium text-gray-600">Address:</span> {data.household.address}</p>
              <p><span className="font-medium text-gray-600">Status:</span> {data.household.status}</p>
            </div>
          ) : (
            <p className="text-sm text-red-500">No household selected — go back to Step 1.</p>
          )}
        </CardBody>
      </Card>

      {/* Survey */}
      <Card>
        <CardHeader title="Survey Metadata" />
        <CardBody>
          <div className="text-sm space-y-1">
            <p><span className="font-medium text-gray-600">Year:</span> {data.survey_year}</p>
            <p><span className="font-medium text-gray-600">Schema:</span> {data.formSchema?.name ?? '(none)'}</p>
            {Object.keys(data.surveyData ?? {}).length > 0 && (
              <div className="mt-2 pt-2 border-t border-gray-100">
                <p className="font-medium text-gray-600 mb-1">Survey Data:</p>
                {Object.entries(data.surveyData).map(([k, v]) => (
                  <p key={k} className="text-gray-700">
                    <span className="text-gray-500">{k}:</span>{' '}
                    {Array.isArray(v) ? v.join(', ') : String(v)}
                  </p>
                ))}
              </div>
            )}
          </div>
        </CardBody>
      </Card>

      {/* Families */}
      {data.families.map((fam, i) => (
        <Card key={fam._id}>
          <CardHeader title={`Family ${i + 1}`} subtitle={
            INCOME_BRACKETS.find((b) => b.value === fam.monthly_income_bracket)?.label
          } />
          <CardBody>
            {fam.persons.length === 0 ? (
              <p className="text-sm text-amber-600">
                Warning: No persons added to this family.
              </p>
            ) : (
              <div className="space-y-1">
                {fam.persons.map((p, j) => (
                  <div key={j} className="flex items-center gap-2 text-sm">
                    <span className="text-gray-400 text-xs w-5">{j + 1}.</span>
                    <span className="font-medium text-gray-800">
                      {p.last_name}, {p.first_name}
                    </span>
                    <Badge color="gray">{p.role}</Badge>
                    <Badge color="blue">{p.gender}</Badge>
                    {p.sectors?.map((s) => (
                      <Badge key={s} color="purple">{s}</Badge>
                    ))}
                  </div>
                ))}
              </div>
            )}
            {fam.programs.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-100">
                <p className="text-xs font-semibold text-gray-500 mb-1">Programs:</p>
                {fam.programs.map((prog, j) => (
                  <p key={j} className="text-sm text-gray-700">
                    {PROGRAM_TYPES.find((t) => t.value === prog.program_type)?.label ?? prog.program_type}
                    {prog.date_availed && ` — ${prog.date_availed}`}
                    {prog.amount && ` — ₱${Number(prog.amount).toLocaleString()}`}
                  </p>
                ))}
              </div>
            )}
          </CardBody>
        </Card>
      ))}

      {(!data.household || data.families.length === 0) && (
        <p className="text-sm text-red-500 text-center">
          Please complete required steps: Household (Step 1) and at least one Family (Step 3).
        </p>
      )}
    </div>
  )
}

// ── Main Wizard ───────────────────────────────────────────────────────────────

const INITIAL_DATA = {
  household:      null,
  formSchema:     null,
  survey_year:    new Date().getFullYear(),
  surveyData:     {},
  families:       [],
  _step2Validate: null,
  _step2Save:     null,
}

export default function SurveyWizard() {
  const navigate    = useNavigate()
  const toast       = useToast()
  const [searchParams] = useSearchParams()

  const [step,       setStep]       = useState(1)
  const [wizardData, setWizardData] = useState(INITIAL_DATA)
  const [submitting, setSubmitting] = useState(false)

  const patchData = useCallback((patch) =>
    setWizardData((d) => ({ ...d, ...patch })), [])

  const canAdvance = () => {
    if (step === 1) return !!wizardData.household
    if (step === 3) return wizardData.families.length > 0
    return true
  }

  const handleBack = () => {
    // Save Step 2 form values before unmounting so they're restored when returning
    if (step === 2 && wizardData._step2Save) wizardData._step2Save()
    setStep((s) => Math.max(s - 1, 1))
  }

  const handleNext = async () => {
    if (step === 2 && wizardData._step2Validate) {
      const ok = await wizardData._step2Validate()
      if (!ok) return
    }
    setStep((s) => Math.min(s + 1, 6))
  }

  const handleSubmit = async () => {
    if (!wizardData.household || wizardData.families.length === 0) return

    setSubmitting(true)
    try {
      // If the household was just registered in the wizard (no id yet), create it first.
      let householdId = wizardData.household.id
      if (!householdId) {
        const { data: created } = await createHousehold({
          household_number: wizardData.household.household_number,
          address:          wizardData.household.address,
          status:           wizardData.household.status || 'ACTIVE',
        })
        householdId = created.id
      }

      const payload = {
        household_id:   householdId,
        form_schema_id: wizardData.formSchema?.id,
        survey_year:    wizardData.survey_year,
        survey_data:    wizardData.surveyData ?? {},
        families_data:  wizardData.families.map((f) => ({
          monthly_income_bracket: f.monthly_income_bracket,
          data:     f.data ?? {},
          persons:  f.persons.map((p) => ({
            ...p,
            age_at_survey: p.age_at_survey ? Number(p.age_at_survey) : null,
          })),
          programs: f.programs.map((prog) => ({
            program_type:      prog.program_type,
            program_name:      prog.program_name || '',
            date_availed:      prog.date_availed || null,
            amount:            prog.amount ? Number(prog.amount) : null,
            reference_no:      prog.reference_no || '',
            description:       prog.description || prog.notes || '',
            beneficiary_index: prog.beneficiary_index ?? null,
          })),
        })),
      }

      await createSurvey(payload)
      toast('Survey submitted successfully!', 'success')
      navigate('/profiling')
    } catch (err) {
      const detail = err.response?.data?.detail
        ?? err.response?.data?.non_field_errors?.[0]
        ?? JSON.stringify(err.response?.data)
        ?? 'Failed to submit survey'
      toast(detail, 'error')
    } finally {
      setSubmitting(false)
    }
  }

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
        <div>
          <h1 className="text-xl font-bold text-gray-900">New Survey Wizard</h1>
          <p className="text-sm text-gray-500">Step {step} of 6</p>
        </div>
      </div>

      {/* Step indicator */}
      <StepIndicator currentStep={step} />

      {/* Step content */}
      <Card>
        <CardBody className="p-6">
          {step === 1 && <Step1Household data={wizardData} onChange={patchData} />}
          {step === 2 && <Step2Survey    data={wizardData} onChange={patchData} />}
          {step === 3 && <Step3Families  data={wizardData} onChange={patchData} />}
          {step === 4 && <Step4Persons   data={wizardData} onChange={patchData} />}
          {step === 5 && <Step5Programs  data={wizardData} onChange={patchData} />}
          {step === 6 && (
            <Step6Review data={wizardData} />
          )}
        </CardBody>
      </Card>

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <Button
          variant="secondary"
          onClick={handleBack}
          disabled={step === 1}
          className="gap-2"
        >
          <ChevronLeft size={15} />
          Back
        </Button>
        {step < 6 ? (
          <Button
            onClick={handleNext}
            disabled={!canAdvance()}
            className="gap-2"
          >
            {step === 5 ? 'Review' : 'Next'}
            <ChevronRight size={15} />
          </Button>
        ) : (
          <Button
            onClick={handleSubmit}
            disabled={submitting || !wizardData.household || wizardData.families.length === 0}
            className="gap-2"
          >
            {submitting ? 'Submitting…' : 'Submit Survey'}
          </Button>
        )}
      </div>
    </div>
  )
}

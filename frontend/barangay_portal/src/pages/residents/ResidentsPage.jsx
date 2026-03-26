import { useState, useEffect, useCallback } from 'react'
import { Plus, UserCheck, Search } from 'lucide-react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { getResidents, createResident, getPuroks } from '../../api/residentsApi'
import { Card } from '../../components/ui/Card'
import Table, { Pagination } from '../../components/ui/Table'
import Modal from '../../components/ui/Modal'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import Badge from '../../components/ui/Badge'
import { useToast } from '../../context/ToastContext'
import { formatDate } from '../../utils/formatters'

const GENDER_OPTIONS = [
  { value: 'MALE', label: 'Male' },
  { value: 'FEMALE', label: 'Female' },
  { value: 'OTHER', label: 'Other' },
]

const CIVIL_STATUS_OPTIONS = [
  { value: 'SINGLE', label: 'Single' },
  { value: 'MARRIED', label: 'Married' },
  { value: 'WIDOWED', label: 'Widowed' },
  { value: 'SEPARATED', label: 'Separated' },
  { value: 'ANNULLED', label: 'Annulled' },
]

const STATUS_OPTIONS = [
  { value: 'ACTIVE', label: 'Active' },
  { value: 'INACTIVE', label: 'Inactive' },
  { value: 'DECEASED', label: 'Deceased' },
  { value: 'TRANSFERRED', label: 'Transferred' },
]

const STATUS_COLORS = { ACTIVE: 'green', INACTIVE: 'gray', DECEASED: 'red', TRANSFERRED: 'yellow' }

const EMPTY_FORM = {
  first_name: '', middle_name: '', last_name: '',
  date_of_birth: '', gender: '', civil_status: '',
  contact_number: '', email: '', purok: '', address: '', status: 'ACTIVE',
}

export default function ResidentsPage() {
  const toast = useToast()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const [rows, setRows] = useState([])
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [puroks, setPuroks] = useState([])
  const [search, setSearch] = useState('')
  const [filterPurok, setFilterPurok] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [showCreate, setShowCreate] = useState(searchParams.get('create') === '1')
  const [form, setForm] = useState(EMPTY_FORM)
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  const load = useCallback(async (p = 1) => {
    setLoading(true)
    try {
      const params = { page: p }
      if (search) params.search = search
      if (filterPurok) params.purok = filterPurok
      if (filterStatus) params.status = filterStatus
      const { data } = await getResidents(params)
      setRows(data.results)
      setCount(data.count)
      setPage(p)
    } catch {
      toast('Failed to load residents.', 'error')
    } finally {
      setLoading(false)
    }
  }, [search, filterPurok, filterStatus, toast])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    getPuroks().then(({ data }) => setPuroks(data.results || data)).catch(() => {})
  }, [])

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((p) => ({ ...p, [name]: value }))
    setErrors((p) => ({ ...p, [name]: undefined }))
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    setSaving(true)
    setErrors({})
    try {
      const payload = { ...form }
      if (!payload.purok) delete payload.purok
      const { data } = await createResident(payload)
      setForm(EMPTY_FORM)
      setShowCreate(false)
      setSearchParams({})
      load()
      toast(`Resident record created (${data.resident_id}).`, 'success')
    } catch (err) {
      const d = err.response?.data || {}
      if (typeof d === 'object') setErrors(d)
      toast(d.non_field_errors?.[0] || d.detail || 'Failed to create resident.', 'error')
    } finally {
      setSaving(false)
    }
  }

  const columns = [
    {
      key: 'name',
      label: 'Name',
      render: (row) => (
        <div>
          <p className="font-medium text-gray-900">
            {[row.last_name, row.first_name].filter(Boolean).join(', ') || '—'}
          </p>
          <p className="text-xs text-gray-400">{row.resident_id}</p>
        </div>
      ),
    },
    {
      key: 'purok',
      label: 'Purok',
      render: (row) => row.purok_number ? <Badge color="blue">Purok {row.purok_number}</Badge> : <span className="text-gray-400 text-sm">—</span>,
    },
    {
      key: 'contact',
      label: 'Contact',
      render: (row) => (
        <div className="text-sm">
          {row.contact_number && <p className="text-gray-700">{row.contact_number}</p>}
          {row.email && <p className="text-gray-400 text-xs">{row.email}</p>}
          {!row.contact_number && !row.email && <span className="text-gray-400">—</span>}
        </div>
      ),
    },
    {
      key: 'has_account',
      label: 'Portal',
      render: (row) => (
        <Badge color={row.has_account ? 'green' : 'gray'}>
          {row.has_account ? 'Has Account' : 'No Account'}
        </Badge>
      ),
    },
    {
      key: 'status',
      label: 'Status',
      render: (row) => <Badge color={STATUS_COLORS[row.status] || 'gray'}>{row.status}</Badge>,
    },
    {
      key: 'created_at',
      label: 'Registered',
      render: (row) => <span className="text-gray-500 text-sm">{formatDate(row.created_at)}</span>,
    },
  ]

  const purokOptions = puroks.map((p) => ({ value: p.id, label: p.name || `Purok ${p.number}` }))

  return (
    <div className="space-y-5 w-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <UserCheck size={20} className="text-blue-600" /> Residents
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">{count} resident{count !== 1 ? 's' : ''}</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors shadow-sm"
        >
          <Plus size={16} /> Add Resident
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search name or ID…"
            className="pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg bg-white outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 w-56"
          />
        </div>
        <Select
          value={filterPurok}
          onChange={(e) => setFilterPurok(e.target.value)}
          placeholder="All Puroks"
          options={purokOptions}
          className="w-40"
        />
        <Select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          placeholder="All Status"
          options={STATUS_OPTIONS}
          className="w-36"
        />
      </div>

      <Card>
        <Table
          columns={columns}
          data={rows}
          loading={loading}
          emptyMessage="No residents found."
          onRowClick={(row) => navigate(`/residents/${row.id}`)}
        />
        <Pagination count={count} page={page} onPageChange={load} />
      </Card>

      {/* Create Modal */}
      <Modal
        isOpen={showCreate}
        onClose={() => { setShowCreate(false); setErrors({}); setSearchParams({}) }}
        title="Add Resident Record"
        size="lg"
        footer={
          <>
            <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm rounded-lg border border-gray-200 hover:bg-gray-50">Cancel</button>
            <button form="create-resident-form" type="submit" disabled={saving}
              className="px-4 py-2 text-sm font-semibold rounded-lg bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-60">
              {saving ? 'Saving…' : 'Save Resident'}
            </button>
          </>
        }
      >
        <form id="create-resident-form" onSubmit={handleCreate} className="space-y-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Personal Information</p>
            <div className="grid grid-cols-3 gap-3">
              <Input label="First Name" name="first_name" value={form.first_name} onChange={handleChange} required error={errors.first_name?.[0]} />
              <Input label="Middle Name" name="middle_name" value={form.middle_name} onChange={handleChange} error={errors.middle_name?.[0]} />
              <Input label="Last Name" name="last_name" value={form.last_name} onChange={handleChange} required error={errors.last_name?.[0]} />
            </div>
            <div className="grid grid-cols-3 gap-3 mt-3">
              <Input label="Date of Birth" type="date" name="date_of_birth" value={form.date_of_birth} onChange={handleChange} error={errors.date_of_birth?.[0]} />
              <Select label="Gender" name="gender" value={form.gender} onChange={handleChange} placeholder="Select" options={GENDER_OPTIONS} error={errors.gender?.[0]} />
              <Select label="Civil Status" name="civil_status" value={form.civil_status} onChange={handleChange} placeholder="Select" options={CIVIL_STATUS_OPTIONS} error={errors.civil_status?.[0]} />
            </div>
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Contact</p>
            <div className="grid grid-cols-2 gap-3">
              <Input label="Phone Number" name="contact_number" value={form.contact_number} onChange={handleChange} placeholder="09XXXXXXXXX" error={errors.contact_number?.[0]} />
              <Input label="Email" type="email" name="email" value={form.email} onChange={handleChange} error={errors.email?.[0]} />
            </div>
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Address</p>
            <div className="grid grid-cols-2 gap-3">
              <Select label="Purok" name="purok" value={form.purok} onChange={handleChange} placeholder="Select purok" options={purokOptions} error={errors.purok?.[0]} />
              <Select label="Status" name="status" value={form.status} onChange={handleChange} options={STATUS_OPTIONS} error={errors.status?.[0]} />
            </div>
            <div className="mt-3">
              <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
              <textarea
                name="address"
                value={form.address}
                onChange={handleChange}
                rows={2}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm resize-none outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Street, Barangay…"
              />
            </div>
          </div>
        </form>
      </Modal>
    </div>
  )
}

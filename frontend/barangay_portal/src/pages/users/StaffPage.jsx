import { useState, useEffect, useCallback } from 'react'
import { Plus, Trash2, Users } from 'lucide-react'
import { getStaff, createStaff, deleteStaff } from '../../api/usersApi'
import { getPuroks } from '../../api/residentsApi'
import { Card } from '../../components/ui/Card'
import Table, { Pagination } from '../../components/ui/Table'
import Modal from '../../components/ui/Modal'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import Badge from '../../components/ui/Badge'
import { useToast } from '../../context/ToastContext'
import { formatDate } from '../../utils/formatters'

const DEPARTMENTS = [
  { value: 'HEALTH', label: 'Health Services' },
  { value: 'SOCIAL', label: 'Social Services' },
  { value: 'RECORDS', label: 'Records Management' },
  { value: 'SECURITY', label: 'Security & Peace Order' },
  { value: 'ENVIRONMENT', label: 'Environment & Sanitation' },
  { value: 'LIVELIHOOD', label: 'Livelihood & Employment' },
  { value: 'GENERAL', label: 'General Services' },
]

const EMPTY_FORM = {
  first_name: '', last_name: '', email: '', username: '', phone: '',
  department: '', work_start: '08:00:00', work_end: '17:00:00',
  allow_weekend: false, allow_after_hours: false, perm_generate_reports: false,
  purok_permissions: [],
}

export default function StaffPage() {
  const toast = useToast()
  const [rows, setRows] = useState([])
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [puroks, setPuroks] = useState([])
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)
  const [createdCredentials, setCreatedCredentials] = useState(null)

  const load = useCallback(async (p = 1) => {
    setLoading(true)
    try {
      const { data } = await getStaff({ page: p })
      setRows(data.results)
      setCount(data.count)
      setPage(p)
    } catch {
      toast('Failed to load staff.', 'error')
    } finally {
      setLoading(false)
    }
  }, [toast])

  useEffect(() => {
    load()
    getPuroks().then(({ data }) => setPuroks(data.results || data)).catch(() => {})
  }, [load])

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm((p) => ({ ...p, [name]: type === 'checkbox' ? checked : value }))
    setErrors((p) => ({ ...p, [name]: undefined }))
  }

  const togglePurok = (purokId) => {
    setForm((p) => {
      const exists = p.purok_permissions.find((pp) => pp.purok === purokId)
      if (exists) {
        return { ...p, purok_permissions: p.purok_permissions.filter((pp) => pp.purok !== purokId) }
      }
      return {
        ...p,
        purok_permissions: [
          ...p.purok_permissions,
          { purok: purokId, can_view: true, can_create: true, can_edit: true, can_delete: false, can_export: false },
        ],
      }
    })
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    setSaving(true)
    setErrors({})
    try {
      const { data } = await createStaff(form)
      setCreatedCredentials({ email: data.email, temp_password: data.temp_password })
      setForm(EMPTY_FORM)
      setShowCreate(false)
      load()
      toast('Staff account created successfully.', 'success')
    } catch (err) {
      const d = err.response?.data || {}
      if (typeof d === 'object') setErrors(d)
      toast(d.non_field_errors?.[0] || d.detail || 'Failed to create staff.', 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (staff) => {
    if (!window.confirm(`Delete staff account for ${staff.email}?`)) return
    try {
      await deleteStaff(staff.id)
      toast('Staff deleted.', 'success')
      load(page)
    } catch {
      toast('Failed to delete staff.', 'error')
    }
  }

  const columns = [
    {
      key: 'name',
      label: 'Name',
      render: (row) => (
        <div>
          <p className="font-medium text-gray-900">
            {`${row.first_name || ''} ${row.last_name || ''}`.trim() || '—'}
          </p>
          <p className="text-xs text-gray-400">{row.username || row.email}</p>
        </div>
      ),
    },
    { key: 'email', label: 'Email' },
    {
      key: 'department',
      label: 'Department',
      render: (row) => (
        <span className="text-sm text-gray-600">
          {row.staff_profile?.department_display || '—'}
        </span>
      ),
    },
    {
      key: 'puroks',
      label: 'Puroks',
      render: (row) => (
        <div className="flex flex-wrap gap-1">
          {(row.purok_permissions || []).length === 0
            ? <span className="text-gray-400 text-sm">None</span>
            : (row.purok_permissions || []).map((pp) => (
              <Badge key={pp.id} color="blue">Purok {pp.purok_number}</Badge>
            ))
          }
        </div>
      ),
    },
    {
      key: 'status',
      label: 'Status',
      render: (row) => <Badge color={row.is_active ? 'green' : 'gray'}>{row.is_active ? 'Active' : 'Inactive'}</Badge>,
    },
    {
      key: 'date_joined',
      label: 'Created',
      render: (row) => <span className="text-gray-500 text-sm">{formatDate(row.date_joined)}</span>,
    },
    {
      key: 'actions',
      label: '',
      width: '56px',
      render: (row) => (
        <button
          onClick={(e) => { e.stopPropagation(); handleDelete(row) }}
          className="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
        >
          <Trash2 size={16} />
        </button>
      ),
    },
  ]

  return (
    <div className="space-y-5 w-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Users size={20} className="text-blue-600" /> Staff Accounts
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">{count} staff member{count !== 1 ? 's' : ''}</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors shadow-sm"
        >
          <Plus size={16} /> Create Staff
        </button>
      </div>

      <Card>
        <Table columns={columns} data={rows} loading={loading} emptyMessage="No staff accounts found." />
        <Pagination count={count} page={page} onPageChange={load} />
      </Card>

      {/* Create Modal */}
      <Modal
        isOpen={showCreate}
        onClose={() => { setShowCreate(false); setErrors({}) }}
        title="Create Staff Account"
        size="lg"
        footer={
          <>
            <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm rounded-lg border border-gray-200 hover:bg-gray-50">Cancel</button>
            <button form="create-staff-form" type="submit" disabled={saving}
              className="px-4 py-2 text-sm font-semibold rounded-lg bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-60">
              {saving ? 'Creating…' : 'Create Account'}
            </button>
          </>
        }
      >
        <form id="create-staff-form" onSubmit={handleCreate} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Input label="First Name" name="first_name" value={form.first_name} onChange={handleChange} required error={errors.first_name?.[0]} />
            <Input label="Last Name" name="last_name" value={form.last_name} onChange={handleChange} required error={errors.last_name?.[0]} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input label="Email" type="email" name="email" value={form.email} onChange={handleChange} required error={errors.email?.[0]} />
            <Input label="Phone" name="phone" value={form.phone} onChange={handleChange} placeholder="09XXXXXXXXX" error={errors.phone?.[0]} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input label="Username" name="username" value={form.username} onChange={handleChange} hint="Optional" error={errors.username?.[0]} />
            <Select label="Department" name="department" value={form.department} onChange={handleChange}
              placeholder="Select department" options={DEPARTMENTS} error={errors.department?.[0]} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input label="Work Start" type="time" name="work_start" value={form.work_start.slice(0, 5)} onChange={(e) => setForm(p => ({ ...p, work_start: e.target.value + ':00' }))} />
            <Input label="Work End" type="time" name="work_end" value={form.work_end.slice(0, 5)} onChange={(e) => setForm(p => ({ ...p, work_end: e.target.value + ':00' }))} />
          </div>

          {/* Purok assignments */}
          {puroks.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-gray-700">Assigned Puroks</p>
              <div className="grid grid-cols-2 gap-2 p-3 bg-gray-50 rounded-lg">
                {puroks.map((p) => {
                  const assigned = form.purok_permissions.some((pp) => pp.purok === p.id)
                  return (
                    <label key={p.id} className="flex items-center gap-2.5 cursor-pointer">
                      <input type="checkbox" checked={assigned} onChange={() => togglePurok(p.id)}
                        className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                      <span className="text-sm text-gray-700">{p.name || `Purok ${p.number}`}</span>
                    </label>
                  )
                })}
              </div>
              {puroks.length === 0 && <p className="text-xs text-gray-400">No puroks found. Create puroks first.</p>}
            </div>
          )}

          <div className="flex flex-wrap gap-4">
            {[
              { name: 'allow_weekend', label: 'Allow weekend access' },
              { name: 'allow_after_hours', label: 'Allow after-hours access' },
              { name: 'perm_generate_reports', label: 'Can generate reports' },
            ].map(({ name, label }) => (
              <label key={name} className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" name={name} checked={form[name]} onChange={handleChange}
                  className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                <span className="text-sm text-gray-700">{label}</span>
              </label>
            ))}
          </div>
        </form>
      </Modal>

      {/* Credentials modal */}
      <Modal
        isOpen={!!createdCredentials}
        onClose={() => setCreatedCredentials(null)}
        title="Staff Account Created"
        size="sm"
        footer={<button onClick={() => setCreatedCredentials(null)} className="px-4 py-2 text-sm font-semibold rounded-lg bg-blue-600 text-white hover:bg-blue-700">Done</button>}
      >
        <div className="space-y-3">
          <p className="text-sm text-gray-600">Share these credentials with the new staff member.</p>
          <div className="bg-slate-900 rounded-lg p-4 space-y-2 font-mono text-sm">
            <div className="flex justify-between">
              <span className="text-slate-400">Email:</span>
              <span className="text-green-400">{createdCredentials?.email}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Temp Password:</span>
              <span className="text-yellow-400 font-bold">{createdCredentials?.temp_password}</span>
            </div>
          </div>
          <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded px-3 py-2">
            ⚠ Staff must change this password on first login.
          </p>
        </div>
      </Modal>
    </div>
  )
}

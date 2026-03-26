import { useState, useEffect, useCallback } from 'react'
import { Plus, Trash2, ToggleLeft, ToggleRight, Shield, Search } from 'lucide-react'
import useDebounce from '../../hooks/useDebounce'
import { getAdmins, createAdmin, updateAdmin, deleteAdmin } from '../../api/usersApi'
import { Card } from '../../components/ui/Card'
import Table, { Pagination } from '../../components/ui/Table'
import Modal from '../../components/ui/Modal'
import Input from '../../components/ui/Input'
import Badge from '../../components/ui/Badge'
import { useToast } from '../../context/ToastContext'
import { formatDate } from '../../utils/formatters'

const EMPTY_FORM = {
  first_name: '', last_name: '', email: '', username: '',
  require_2fa: false,
  perm_manage_residents: true,
  perm_manage_staff: false,
  perm_view_reports: true,
  perm_delete_users: false,
  perm_change_system_settings: false,
}

function PermCheckbox({ label, name, checked, onChange }) {
  return (
    <label className="flex items-center gap-2.5 cursor-pointer group">
      <input
        type="checkbox"
        name={name}
        checked={checked}
        onChange={onChange}
        className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
      />
      <span className="text-sm text-gray-700 group-hover:text-gray-900">{label}</span>
    </label>
  )
}

export default function AdminsPage() {
  const toast = useToast()
  const [rows, setRows] = useState([])
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)
  const [createdCredentials, setCreatedCredentials] = useState(null)
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebounce(search, 350)

  const load = useCallback(async (p = 1) => {
    setLoading(true)
    try {
      const params = { page: p }
      if (debouncedSearch) params.search = debouncedSearch
      const { data } = await getAdmins(params)
      setRows(data.results)
      setCount(data.count)
      setPage(p)
    } catch {
      toast('Failed to load admins.', 'error')
    } finally {
      setLoading(false)
    }
  }, [debouncedSearch, toast])

  useEffect(() => { load() }, [load])

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm((p) => ({ ...p, [name]: type === 'checkbox' ? checked : value }))
    setErrors((p) => ({ ...p, [name]: undefined }))
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    setSaving(true)
    setErrors({})
    try {
      const { data } = await createAdmin(form)
      setCreatedCredentials({ email: data.email, username: data.username, temp_password: data.temp_password })
      setForm(EMPTY_FORM)
      setShowCreate(false)
      load()
      toast('Admin account created successfully.', 'success')
    } catch (err) {
      const d = err.response?.data || {}
      if (typeof d === 'object') setErrors(d)
      toast(d.non_field_errors?.[0] || d.detail || 'Failed to create admin.', 'error')
    } finally {
      setSaving(false)
    }
  }

  const toggleActive = async (admin) => {
    try {
      await updateAdmin(admin.id, { is_active: !admin.is_active })
      toast(`Admin ${admin.is_active ? 'deactivated' : 'activated'}.`, 'success')
      load(page)
    } catch {
      toast('Failed to update admin.', 'error')
    }
  }

  const handleDelete = async (admin) => {
    if (!window.confirm(`Delete admin account for ${admin.email}? This cannot be undone.`)) return
    try {
      await deleteAdmin(admin.id)
      toast('Admin deleted.', 'success')
      load(page)
    } catch (err) {
      toast(err.response?.data?.error || 'Failed to delete admin.', 'error')
    }
  }

  const columns = [
    {
      key: 'name',
      label: 'Name',
      render: (row) => (
        <div>
          <p className="font-medium text-gray-900">
            {row.first_name || row.last_name ? `${row.first_name} ${row.last_name}`.trim() : '—'}
          </p>
          <p className="text-xs text-gray-400">{row.username || '—'}</p>
        </div>
      ),
    },
    { key: 'email', label: 'Email' },
    {
      key: 'status',
      label: 'Status',
      render: (row) => (
        <Badge color={row.is_active ? 'green' : 'gray'}>
          {row.is_active ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
    {
      key: 'perms',
      label: 'Permissions',
      render: (row) => (
        <div className="flex flex-wrap gap-1">
          {row.perm_manage_residents && <Badge color="blue">Residents</Badge>}
          {row.perm_manage_staff && <Badge color="purple">Staff</Badge>}
          {row.perm_view_reports && <Badge color="gray">Reports</Badge>}
        </div>
      ),
    },
    {
      key: 'date_joined',
      label: 'Created',
      render: (row) => <span className="text-gray-500 text-sm">{formatDate(row.date_joined)}</span>,
    },
    {
      key: 'actions',
      label: '',
      width: '80px',
      render: (row) => (
        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={() => toggleActive(row)}
            title={row.is_active ? 'Deactivate' : 'Activate'}
            className="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
          >
            {row.is_active ? <ToggleRight size={18} /> : <ToggleLeft size={18} />}
          </button>
          <button
            onClick={() => handleDelete(row)}
            title="Delete"
            className="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
          >
            <Trash2 size={16} />
          </button>
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-5 w-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Shield size={20} className="text-blue-600" /> Admin Accounts
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">{count} admin{count !== 1 ? 's' : ''} total</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors shadow-sm"
        >
          <Plus size={16} /> Create Admin
        </button>
      </div>

      <div className="relative w-56">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search name or email…"
          className="pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg bg-white outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 w-full"
        />
      </div>

      <Card>
        <Table columns={columns} data={rows} loading={loading} emptyMessage="No admin accounts found." />
        <Pagination count={count} page={page} onPageChange={load} />
      </Card>

      {/* Create Modal */}
      <Modal
        isOpen={showCreate}
        onClose={() => { setShowCreate(false); setErrors({}) }}
        title="Create Admin Account"
        size="md"
        footer={
          <>
            <button
              onClick={() => setShowCreate(false)}
              className="px-4 py-2 text-sm rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              form="create-admin-form"
              type="submit"
              disabled={saving}
              className="px-4 py-2 text-sm font-semibold rounded-lg bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-60 transition-colors"
            >
              {saving ? 'Creating…' : 'Create Account'}
            </button>
          </>
        }
      >
        <form id="create-admin-form" onSubmit={handleCreate} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Input label="First Name" name="first_name" value={form.first_name} onChange={handleChange} required error={errors.first_name?.[0]} />
            <Input label="Last Name" name="last_name" value={form.last_name} onChange={handleChange} required error={errors.last_name?.[0]} />
          </div>
          <Input label="Email" type="email" name="email" value={form.email} onChange={handleChange} required error={errors.email?.[0]} />
          <Input label="Username" name="username" value={form.username} onChange={handleChange} hint="Optional — auto-assigned if blank" error={errors.username?.[0]} />

          <div className="space-y-2 pt-1">
            <p className="text-sm font-medium text-gray-700">Permissions</p>
            <div className="grid grid-cols-2 gap-2 p-3 bg-gray-50 rounded-lg">
              <PermCheckbox label="Manage Residents" name="perm_manage_residents" checked={form.perm_manage_residents} onChange={handleChange} />
              <PermCheckbox label="Manage Staff" name="perm_manage_staff" checked={form.perm_manage_staff} onChange={handleChange} />
              <PermCheckbox label="View Reports" name="perm_view_reports" checked={form.perm_view_reports} onChange={handleChange} />
              <PermCheckbox label="Delete Users" name="perm_delete_users" checked={form.perm_delete_users} onChange={handleChange} />
              <PermCheckbox label="System Settings" name="perm_change_system_settings" checked={form.perm_change_system_settings} onChange={handleChange} />
            </div>
          </div>

          <PermCheckbox label="Require 2FA setup on first login" name="require_2fa" checked={form.require_2fa} onChange={handleChange} />
        </form>
      </Modal>

      {/* Credentials modal */}
      <Modal
        isOpen={!!createdCredentials}
        onClose={() => setCreatedCredentials(null)}
        title="Account Created — Save Credentials"
        size="sm"
        footer={
          <button
            onClick={() => setCreatedCredentials(null)}
            className="px-4 py-2 text-sm font-semibold rounded-lg bg-blue-600 text-white hover:bg-blue-700"
          >
            Done
          </button>
        }
      >
        <div className="space-y-3">
          <p className="text-sm text-gray-600">Share these credentials with the new admin. The password is shown once only.</p>
          <div className="bg-slate-900 rounded-lg p-4 space-y-2 font-mono text-sm">
            <div className="flex justify-between">
              <span className="text-slate-400">Email:</span>
              <span className="text-green-400">{createdCredentials?.email}</span>
            </div>
            {createdCredentials?.username && (
              <div className="flex justify-between">
                <span className="text-slate-400">Username:</span>
                <span className="text-green-400">{createdCredentials.username}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-slate-400">Temp Password:</span>
              <span className="text-yellow-400 font-bold">{createdCredentials?.temp_password}</span>
            </div>
          </div>
          <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded px-3 py-2">
            ⚠ The admin must change this password on first login.
          </p>
        </div>
      </Modal>
    </div>
  )
}

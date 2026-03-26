import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, UserPlus, Edit2, Save, X } from 'lucide-react'
import { getResident, updateResident, createResidentAccount, getSuggestedUsername } from '../../api/residentsApi'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import Badge from '../../components/ui/Badge'
import Modal from '../../components/ui/Modal'
import Spinner from '../../components/ui/Spinner'
import { useToast } from '../../context/ToastContext'
import { formatDate } from '../../utils/formatters'

const STATUS_COLORS = { ACTIVE: 'green', INACTIVE: 'gray', DECEASED: 'red', TRANSFERRED: 'yellow' }
const STATUS_OPTIONS = [
  { value: 'ACTIVE', label: 'Active' },
  { value: 'INACTIVE', label: 'Inactive' },
  { value: 'DECEASED', label: 'Deceased' },
  { value: 'TRANSFERRED', label: 'Transferred' },
]

function InfoRow({ label, value }) {
  return (
    <div>
      <p className="text-xs text-gray-400 uppercase tracking-wide">{label}</p>
      <p className="text-sm font-medium text-gray-800 mt-0.5">{value || '—'}</p>
    </div>
  )
}

export default function ResidentDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const toast = useToast()

  const [resident, setResident] = useState(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [editForm, setEditForm] = useState({})
  const [saving, setSaving] = useState(false)

  const [showCreateAccount, setShowCreateAccount] = useState(false)
  const [accountForm, setAccountForm] = useState({ username: '' })
  const [creatingAccount, setCreatingAccount] = useState(false)
  const [createdCredentials, setCreatedCredentials] = useState(null)

  const load = async () => {
    try {
      const { data } = await getResident(id)
      setResident(data)
      setEditForm(data)
    } catch {
      toast('Failed to load resident.', 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [id])

  const openCreateAccount = async () => {
    setShowCreateAccount(true)
    try {
      const { data } = await getSuggestedUsername(id)
      setAccountForm({ username: data.username })
    } catch {
      setAccountForm({ username: '' })
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const { data } = await updateResident(id, editForm)
      setResident(data)
      setEditing(false)
      toast('Resident updated.', 'success')
    } catch (err) {
      toast(err.response?.data?.detail || 'Failed to update resident.', 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleCreateAccount = async (e) => {
    e.preventDefault()
    setCreatingAccount(true)
    try {
      const { data } = await createResidentAccount(id, { username: accountForm.username || undefined })
      setCreatedCredentials(data)
      setShowCreateAccount(false)
      load()
      toast('Portal account created.', 'success')
    } catch (err) {
      toast(err.response?.data?.non_field_errors?.[0] || err.response?.data?.detail || 'Failed to create account.', 'error')
    } finally {
      setCreatingAccount(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="lg" />
      </div>
    )
  }

  if (!resident) return null

  const fullName = [resident.first_name, resident.middle_name, resident.last_name].filter(Boolean).join(' ')

  return (
    <div className="space-y-5 w-full">
      {/* Back + Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/residents')}
          className="p-2 rounded-lg hover:bg-gray-100 text-gray-500 transition-colors"
        >
          <ArrowLeft size={18} />
        </button>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-gray-900">{fullName || 'Unnamed Resident'}</h1>
          <p className="text-sm text-gray-400">{resident.resident_id}</p>
        </div>
        <Badge color={STATUS_COLORS[resident.status] || 'gray'}>{resident.status}</Badge>
        {!resident.has_account && (
          <button
            onClick={openCreateAccount}
            className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors shadow-sm"
          >
            <UserPlus size={15} /> Create Portal Account
          </button>
        )}
        {resident.has_account && (
          <Badge color="green" className="px-3 py-1">Has Portal Account</Badge>
        )}
        {!editing ? (
          <button
            onClick={() => setEditing(true)}
            className="flex items-center gap-2 border border-gray-200 hover:bg-gray-50 text-gray-700 text-sm font-medium px-4 py-2 rounded-lg transition-colors"
          >
            <Edit2 size={14} /> Edit
          </button>
        ) : (
          <div className="flex gap-2">
            <button
              onClick={() => { setEditing(false); setEditForm(resident) }}
              className="flex items-center gap-1.5 border border-gray-200 hover:bg-gray-50 text-gray-700 text-sm px-3 py-2 rounded-lg transition-colors"
            >
              <X size={14} /> Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-3 py-2 rounded-lg transition-colors disabled:opacity-60"
            >
              <Save size={14} /> {saving ? 'Saving…' : 'Save'}
            </button>
          </div>
        )}
      </div>

      {/* Personal Info */}
      <Card>
        <CardHeader title="Personal Information" />
        <CardBody>
          {editing ? (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <Input label="First Name" value={editForm.first_name || ''} onChange={(e) => setEditForm(p => ({ ...p, first_name: e.target.value }))} />
                <Input label="Middle Name" value={editForm.middle_name || ''} onChange={(e) => setEditForm(p => ({ ...p, middle_name: e.target.value }))} />
                <Input label="Last Name" value={editForm.last_name || ''} onChange={(e) => setEditForm(p => ({ ...p, last_name: e.target.value }))} />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <Input label="Date of Birth" type="date" value={editForm.date_of_birth || ''} onChange={(e) => setEditForm(p => ({ ...p, date_of_birth: e.target.value }))} />
                <Select label="Gender" value={editForm.gender || ''} onChange={(e) => setEditForm(p => ({ ...p, gender: e.target.value }))}
                  placeholder="Select" options={[{ value: 'MALE', label: 'Male' }, { value: 'FEMALE', label: 'Female' }, { value: 'OTHER', label: 'Other' }]} />
                <Select label="Status" value={editForm.status || ''} onChange={(e) => setEditForm(p => ({ ...p, status: e.target.value }))}
                  options={STATUS_OPTIONS} />
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-y-4 gap-x-6">
              <InfoRow label="First Name" value={resident.first_name} />
              <InfoRow label="Middle Name" value={resident.middle_name} />
              <InfoRow label="Last Name" value={resident.last_name} />
              <InfoRow label="Date of Birth" value={resident.date_of_birth ? formatDate(resident.date_of_birth) : null} />
              <InfoRow label="Gender" value={resident.gender} />
              <InfoRow label="Civil Status" value={resident.civil_status} />
            </div>
          )}
        </CardBody>
      </Card>

      {/* Contact */}
      <Card>
        <CardHeader title="Contact & Address" />
        <CardBody>
          {editing ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <Input label="Phone" value={editForm.contact_number || ''} onChange={(e) => setEditForm(p => ({ ...p, contact_number: e.target.value }))} />
                <Input label="Email" type="email" value={editForm.email || ''} onChange={(e) => setEditForm(p => ({ ...p, email: e.target.value }))} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
                <textarea
                  value={editForm.address || ''}
                  onChange={(e) => setEditForm(p => ({ ...p, address: e.target.value }))}
                  rows={2}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm resize-none outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-y-4 gap-x-6">
              <InfoRow label="Phone" value={resident.contact_number} />
              <InfoRow label="Email" value={resident.email} />
              <InfoRow label="Purok" value={resident.purok_number ? `Purok ${resident.purok_number}` : null} />
              <div className="col-span-3">
                <InfoRow label="Address" value={resident.address} />
              </div>
            </div>
          )}
        </CardBody>
      </Card>

      {/* Record Info */}
      <Card>
        <CardHeader title="Record Information" />
        <CardBody>
          <div className="grid grid-cols-3 gap-y-4 gap-x-6">
            <InfoRow label="Resident ID" value={resident.resident_id} />
            <InfoRow label="Registered" value={formatDate(resident.created_at)} />
            <InfoRow label="Last Updated" value={formatDate(resident.updated_at)} />
            <InfoRow label="Portal Account" value={resident.has_account ? 'Yes' : 'No'} />
          </div>
        </CardBody>
      </Card>

      {/* Create Portal Account Modal */}
      <Modal
        isOpen={showCreateAccount}
        onClose={() => setShowCreateAccount(false)}
        title="Create Portal Account"
        size="sm"
        footer={
          <>
            <button onClick={() => setShowCreateAccount(false)} className="px-4 py-2 text-sm rounded-lg border border-gray-200 hover:bg-gray-50">Cancel</button>
            <button form="create-account-form" type="submit" disabled={creatingAccount}
              className="px-4 py-2 text-sm font-semibold rounded-lg bg-green-600 hover:bg-green-700 text-white disabled:opacity-60">
              {creatingAccount ? 'Creating…' : 'Create Account'}
            </button>
          </>
        }
      >
        <form id="create-account-form" onSubmit={handleCreateAccount} className="space-y-4">
          <div className="bg-gray-50 rounded-lg p-3 text-sm space-y-1">
            <p className="text-gray-700 font-medium">{fullName}</p>
            <p className="text-gray-400">{resident.email}</p>
          </div>
          <Input
            label="Username"
            value={accountForm.username}
            onChange={(e) => setAccountForm({ username: e.target.value })}
            hint="Leave blank to use the suggested username above"
          />
          <p className="text-xs text-gray-500">
            A temporary password will be generated. The resident must change it on first login.
          </p>
        </form>
      </Modal>

      {/* Credentials modal */}
      <Modal
        isOpen={!!createdCredentials}
        onClose={() => setCreatedCredentials(null)}
        title="Portal Account Created"
        size="sm"
        footer={
          <button onClick={() => setCreatedCredentials(null)} className="px-4 py-2 text-sm font-semibold rounded-lg bg-blue-600 text-white hover:bg-blue-700">Done</button>
        }
      >
        <div className="space-y-3">
          <p className="text-sm text-gray-600">Print or write down these credentials for the resident.</p>
          <div className="bg-slate-900 rounded-lg p-4 space-y-2 font-mono text-sm">
            <div className="flex justify-between">
              <span className="text-slate-400">Name:</span>
              <span className="text-white">{createdCredentials?.resident_name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Username:</span>
              <span className="text-green-400">{createdCredentials?.username}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Email:</span>
              <span className="text-green-400">{createdCredentials?.email}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Password:</span>
              <span className="text-yellow-400 font-bold">{createdCredentials?.temp_password}</span>
            </div>
          </div>
          <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded px-3 py-2">
            ⚠ Resident must change this password on first login.
          </p>
        </div>
      </Modal>
    </div>
  )
}

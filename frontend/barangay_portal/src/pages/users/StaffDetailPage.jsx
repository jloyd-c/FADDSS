import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Save, ToggleLeft, ToggleRight, User,
  Clock, Building2, ShieldCheck,
} from 'lucide-react'
import { getStaffMember, updateStaff } from '../../api/usersApi'
import { getPuroks } from '../../api/residentsApi'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import Select from '../../components/ui/Select'
import Input from '../../components/ui/Input'
import Spinner from '../../components/ui/Spinner'
import { useToast } from '../../context/ToastContext'
import { formatDate } from '../../utils/formatters'

const DEPARTMENTS = [
  { value: 'HEALTH',       label: 'Health Services' },
  { value: 'SOCIAL',       label: 'Social Services' },
  { value: 'RECORDS',      label: 'Records Management' },
  { value: 'SECURITY',     label: 'Security & Peace Order' },
  { value: 'ENVIRONMENT',  label: 'Environment & Sanitation' },
  { value: 'LIVELIHOOD',   label: 'Livelihood & Employment' },
  { value: 'GENERAL',      label: 'General Services' },
]

const PERM_COLS = [
  { key: 'can_view',   label: 'View' },
  { key: 'can_create', label: 'Record' },
  { key: 'can_edit',   label: 'Edit' },
  { key: 'can_delete', label: 'Delete' },
  { key: 'can_export', label: 'Export' },
]

function Checkbox({ checked, onChange, disabled }) {
  return (
    <input
      type="checkbox"
      checked={checked}
      onChange={onChange}
      disabled={disabled}
      className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:opacity-40 cursor-pointer disabled:cursor-default"
    />
  )
}

export default function StaffDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const toast = useToast()

  const [staff, setStaff] = useState(null)
  const [puroks, setPuroks] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  // Editable state
  const [isActive, setIsActive] = useState(true)
  const [profile, setProfile] = useState({
    department: '', phone: '', work_start: '08:00', work_end: '17:00',
    allow_weekend: false, allow_after_hours: false, perm_generate_reports: false,
  })
  // purokPerms: { [purokId]: { can_view, can_create, can_edit, can_delete, can_export } }
  const [purokPerms, setPurokPerms] = useState({})

  useEffect(() => {
    Promise.all([
      getStaffMember(id),
      getPuroks({ page_size: 100 }),
    ]).then(([staffRes, purokRes]) => {
      const s = staffRes.data
      setStaff(s)
      setIsActive(s.is_active)

      const sp = s.staff_profile || {}
      setProfile({
        department:           sp.department || '',
        phone:                sp.phone || '',
        work_start:           (sp.work_start || '08:00:00').slice(0, 5),
        work_end:             (sp.work_end   || '17:00:00').slice(0, 5),
        allow_weekend:        sp.allow_weekend || false,
        allow_after_hours:    sp.allow_after_hours || false,
        perm_generate_reports: sp.perm_generate_reports || false,
      })

      // Build purokPerms map from existing assignments
      const permsMap = {}
      ;(s.purok_permissions || []).forEach((pp) => {
        permsMap[pp.purok] = {
          can_view:   pp.can_view,
          can_create: pp.can_create,
          can_edit:   pp.can_edit,
          can_delete: pp.can_delete,
          can_export: pp.can_export,
        }
      })
      setPurokPerms(permsMap)

      const allPuroks = purokRes.data.results || purokRes.data
      setPuroks(allPuroks)
    }).catch(() => {
      toast('Failed to load staff details.', 'error')
    }).finally(() => setLoading(false))
  }, [id])

  const togglePurok = (purokId) => {
    setPurokPerms((prev) => {
      if (prev[purokId]) {
        const next = { ...prev }
        delete next[purokId]
        return next
      }
      return { ...prev, [purokId]: { can_view: true, can_create: false, can_edit: false, can_delete: false, can_export: false } }
    })
  }

  const togglePermCol = (purokId, col) => {
    setPurokPerms((prev) => ({
      ...prev,
      [purokId]: { ...prev[purokId], [col]: !prev[purokId][col] },
    }))
  }

  // Toggle an entire column across all currently-assigned puroks
  const toggleAllInCol = (col) => {
    const assignedIds = Object.keys(purokPerms)
    if (assignedIds.length === 0) return
    const allOn = assignedIds.every((pid) => purokPerms[pid][col])
    setPurokPerms((prev) => {
      const next = { ...prev }
      assignedIds.forEach((pid) => {
        next[pid] = { ...next[pid], [col]: !allOn }
      })
      return next
    })
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const purokPermissionsPayload = Object.entries(purokPerms).map(([purokId, perms]) => ({
        purok: Number(purokId),
        ...perms,
      }))

      await updateStaff(id, {
        is_active:   isActive,
        department:  profile.department,
        phone:       profile.phone,
        work_start:  profile.work_start + ':00',
        work_end:    profile.work_end   + ':00',
        allow_weekend:        profile.allow_weekend,
        allow_after_hours:    profile.allow_after_hours,
        perm_generate_reports: profile.perm_generate_reports,
        purok_permissions:    purokPermissionsPayload,
      })

      toast('Staff updated successfully.', 'success')
      // Refresh
      const { data } = await getStaffMember(id)
      setStaff(data)
    } catch (err) {
      toast(err.response?.data?.detail || 'Failed to update staff.', 'error')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64"><Spinner size="lg" /></div>
  }
  if (!staff) return null

  const fullName = [staff.first_name, staff.last_name].filter(Boolean).join(' ') || staff.email
  const assignedCount = Object.keys(purokPerms).length

  return (
    <div className="space-y-5 w-full">
      {/* Header */}
      <div className="flex items-center gap-3 flex-wrap">
        <button
          onClick={() => navigate('/users/staff')}
          className="p-2 rounded-lg hover:bg-gray-100 text-gray-500 transition-colors"
        >
          <ArrowLeft size={18} />
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-bold text-gray-900 truncate">{fullName}</h1>
          <p className="text-sm text-gray-400">{staff.email}</p>
        </div>

        {/* Active toggle */}
        <button
          onClick={() => setIsActive((v) => !v)}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors
            ${isActive
              ? 'border-green-200 bg-green-50 text-green-700 hover:bg-green-100'
              : 'border-gray-200 bg-gray-50 text-gray-500 hover:bg-gray-100'}`}
          title={isActive ? 'Click to deactivate' : 'Click to activate'}
        >
          {isActive ? <ToggleRight size={18} /> : <ToggleLeft size={18} />}
          {isActive ? 'Active' : 'Inactive'}
        </button>

        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60
            text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors shadow-sm"
        >
          <Save size={15} />
          {saving ? 'Saving…' : 'Save Changes'}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left column */}
        <div className="lg:col-span-1 space-y-5">
          {/* Staff Info */}
          <Card>
            <CardHeader title={<span className="flex items-center gap-2"><User size={15} />Staff Info</span>} />
            <CardBody>
              <div className="space-y-3 text-sm">
                <div>
                  <p className="text-xs text-gray-400 uppercase tracking-wide">Username</p>
                  <p className="font-medium text-gray-800 mt-0.5">{staff.username || '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 uppercase tracking-wide">Department</p>
                  <p className="font-medium text-gray-800 mt-0.5">{staff.staff_profile?.department_display || '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 uppercase tracking-wide">Created</p>
                  <p className="font-medium text-gray-800 mt-0.5">{formatDate(staff.date_joined)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 uppercase tracking-wide">Created By</p>
                  <p className="font-medium text-gray-800 mt-0.5">{staff.created_by_email || '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 uppercase tracking-wide">Password</p>
                  <Badge color={staff.must_change_password ? 'yellow' : 'green'}>
                    {staff.must_change_password ? 'Must change' : 'Set'}
                  </Badge>
                </div>
              </div>
            </CardBody>
          </Card>

          {/* Schedule & Settings */}
          <Card>
            <CardHeader title={<span className="flex items-center gap-2"><Clock size={15} />Schedule & Access</span>} />
            <CardBody>
              <div className="space-y-4">
                <Select
                  label="Department"
                  value={profile.department}
                  onChange={(e) => setProfile((p) => ({ ...p, department: e.target.value }))}
                  options={DEPARTMENTS}
                  placeholder="Select department"
                />
                <Input
                  label="Phone"
                  value={profile.phone}
                  onChange={(e) => setProfile((p) => ({ ...p, phone: e.target.value }))}
                  placeholder="09XXXXXXXXX"
                />
                <div className="grid grid-cols-2 gap-3">
                  <Input
                    label="Work Start"
                    type="time"
                    value={profile.work_start}
                    onChange={(e) => setProfile((p) => ({ ...p, work_start: e.target.value }))}
                  />
                  <Input
                    label="Work End"
                    type="time"
                    value={profile.work_end}
                    onChange={(e) => setProfile((p) => ({ ...p, work_end: e.target.value }))}
                  />
                </div>

                <div className="space-y-2 pt-1">
                  {[
                    { key: 'allow_weekend',        label: 'Allow weekend access' },
                    { key: 'allow_after_hours',     label: 'Allow after-hours access' },
                    { key: 'perm_generate_reports', label: 'Can generate reports' },
                  ].map(({ key, label }) => (
                    <label key={key} className="flex items-center gap-2.5 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={profile[key]}
                        onChange={(e) => setProfile((p) => ({ ...p, [key]: e.target.checked }))}
                        className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="text-sm text-gray-700">{label}</span>
                    </label>
                  ))}
                </div>
              </div>
            </CardBody>
          </Card>
        </div>

        {/* Right column — Purok Permissions */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader
              title={
                <span className="flex items-center gap-2">
                  <ShieldCheck size={15} /> Purok Permissions
                  <span className="ml-1 text-xs font-normal text-gray-400">
                    {assignedCount} of {puroks.length} assigned
                  </span>
                </span>
              }
            />
            <CardBody>
              {puroks.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-6">
                  No puroks found. Create puroks first.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100">
                        <th className="text-left py-2 pr-4 font-medium text-gray-500 text-xs uppercase tracking-wide w-36">
                          Purok
                        </th>
                        <th className="text-center py-2 px-2 font-medium text-gray-500 text-xs uppercase tracking-wide w-16">
                          Assigned
                        </th>
                        {PERM_COLS.map((col) => (
                          <th key={col.key} className="text-center py-2 px-2 w-16">
                            <button
                              onClick={() => toggleAllInCol(col.key)}
                              className="text-xs font-medium text-gray-500 uppercase tracking-wide hover:text-blue-600 transition-colors"
                              title={`Toggle all ${col.label}`}
                            >
                              {col.label}
                            </button>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {puroks.map((purok, i) => {
                        const assigned = !!purokPerms[purok.id]
                        const perms = purokPerms[purok.id] || {}
                        return (
                          <tr
                            key={purok.id}
                            className={`border-b border-gray-50 transition-colors
                              ${i % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}
                              ${assigned ? '' : 'opacity-50'}`}
                          >
                            <td className="py-2.5 pr-4">
                              <span className="font-medium text-gray-800">
                                {purok.name || `Purok ${purok.number}`}
                              </span>
                            </td>
                            {/* Assigned toggle */}
                            <td className="py-2.5 px-2 text-center">
                              <Checkbox
                                checked={assigned}
                                onChange={() => togglePurok(purok.id)}
                              />
                            </td>
                            {/* Per-permission checkboxes */}
                            {PERM_COLS.map((col) => (
                              <td key={col.key} className="py-2.5 px-2 text-center">
                                <Checkbox
                                  checked={assigned && !!perms[col.key]}
                                  onChange={() => assigned && togglePermCol(purok.id, col.key)}
                                  disabled={!assigned}
                                />
                              </td>
                            ))}
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>

                  <p className="text-xs text-gray-400 mt-3">
                    Click column headers to toggle that permission for all assigned puroks.
                    Check "Assigned" to grant access to a purok.
                  </p>
                </div>
              )}
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  )
}

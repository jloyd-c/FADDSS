import { useEffect, useState } from 'react'
import { Users, UserCheck, MapPin, Shield, TrendingUp } from 'lucide-react'
import useAuthStore from '../store/authStore'
import { getAdmins, getStaff } from '../api/usersApi'
import { getResidents, getPuroks } from '../api/residentsApi'
import { Card, CardBody } from '../components/ui/Card'
import Badge from '../components/ui/Badge'

const ROLE_BADGE = {
  SUPER_ADMIN: { label: 'Super Admin', color: 'red' },
  ADMIN: { label: 'Admin', color: 'blue' },
  STAFF: { label: 'Staff', color: 'green' },
}

function StatCard({ icon: Icon, label, value, color, loading }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
    orange: 'bg-orange-50 text-orange-600',
  }
  return (
    <Card>
      <CardBody className="flex items-center gap-4">
        <div className={`p-3 rounded-xl ${colors[color]}`}>
          <Icon size={22} />
        </div>
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          {loading ? (
            <div className="h-7 w-12 bg-gray-100 rounded animate-pulse mt-1" />
          ) : (
            <p className="text-2xl font-bold text-gray-900">{value ?? '—'}</p>
          )}
        </div>
      </CardBody>
    </Card>
  )
}

export default function DashboardPage() {
  const { user } = useAuthStore()
  const role = user?.role
  const roleInfo = ROLE_BADGE[role]

  const [stats, setStats] = useState({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetches = []

    if (role === 'SUPER_ADMIN') {
      fetches.push(
        getAdmins({ page_size: 1 }).then(({ data }) => ({ admins: data.count })).catch(() => ({})),
        getStaff({ page_size: 1 }).then(({ data }) => ({ staff: data.count })).catch(() => ({})),
        getResidents({ page_size: 1 }).then(({ data }) => ({ residents: data.count })).catch(() => ({})),
        getPuroks({ page_size: 1 }).then(({ data }) => ({ puroks: data.count })).catch(() => ({})),
      )
    } else if (role === 'ADMIN') {
      if (user?.perm_manage_staff) {
        fetches.push(getStaff({ page_size: 1 }).then(({ data }) => ({ staff: data.count })).catch(() => ({})))
      }
      if (user?.perm_manage_residents) {
        fetches.push(getResidents({ page_size: 1 }).then(({ data }) => ({ residents: data.count })).catch(() => ({})))
      }
    } else if (role === 'STAFF') {
      fetches.push(
        getResidents({ page_size: 1 }).then(({ data }) => ({ residents: data.count })).catch(() => ({}))
      )
    }

    Promise.all(fetches).then((results) => {
      setStats(Object.assign({}, ...results))
      setLoading(false)
    })
  }, [role, user])

  const greeting = () => {
    const h = new Date().getHours()
    if (h < 12) return 'Good morning'
    if (h < 18) return 'Good afternoon'
    return 'Good evening'
  }

  return (
    <div className="space-y-6 w-full">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {greeting()}, {user?.first_name || user?.email?.split('@')[0]} 👋
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Here's what's happening in your barangay today.
          </p>
        </div>
        {roleInfo && <Badge color={roleInfo.color} className="text-sm px-3 py-1">{roleInfo.label}</Badge>}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {(role === 'SUPER_ADMIN' || role === 'ADMIN') && (
          <StatCard icon={UserCheck} label="Total Residents" value={stats.residents} color="blue" loading={loading} />
        )}
        {role === 'STAFF' && (
          <StatCard icon={UserCheck} label="Residents in Your Puroks" value={stats.residents} color="blue" loading={loading} />
        )}
        {(role === 'SUPER_ADMIN' || (role === 'ADMIN' && user?.perm_manage_staff)) && (
          <StatCard icon={Users} label="Staff Members" value={stats.staff} color="green" loading={loading} />
        )}
        {role === 'SUPER_ADMIN' && (
          <>
            <StatCard icon={Shield} label="Admin Accounts" value={stats.admins} color="purple" loading={loading} />
            <StatCard icon={MapPin} label="Puroks" value={stats.puroks} color="orange" loading={loading} />
          </>
        )}
      </div>

      {/* Quick actions */}
      <Card>
        <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
          <TrendingUp size={16} className="text-blue-600" />
          <h3 className="text-sm font-semibold text-gray-900">Quick Actions</h3>
        </div>
        <CardBody className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {(role === 'SUPER_ADMIN' || role === 'ADMIN' || role === 'STAFF') && (
            <a
              href="/residents"
              className="flex flex-col items-start gap-1 p-4 rounded-xl border border-gray-200 hover:border-blue-300 hover:bg-blue-50/50 transition-colors group"
            >
              <UserCheck size={20} className="text-blue-600" />
              <span className="text-sm font-medium text-gray-700 group-hover:text-blue-700">View Residents</span>
              <span className="text-xs text-gray-400">Browse resident records</span>
            </a>
          )}
          {(role === 'SUPER_ADMIN' || (role === 'ADMIN' && user?.perm_manage_residents)) && (
            <a
              href="/residents?create=1"
              className="flex flex-col items-start gap-1 p-4 rounded-xl border border-gray-200 hover:border-green-300 hover:bg-green-50/50 transition-colors group"
            >
              <UserCheck size={20} className="text-green-600" />
              <span className="text-sm font-medium text-gray-700 group-hover:text-green-700">Add Resident</span>
              <span className="text-xs text-gray-400">Register a new resident</span>
            </a>
          )}
          {role === 'SUPER_ADMIN' && (
            <a
              href="/users/admins"
              className="flex flex-col items-start gap-1 p-4 rounded-xl border border-gray-200 hover:border-purple-300 hover:bg-purple-50/50 transition-colors group"
            >
              <Shield size={20} className="text-purple-600" />
              <span className="text-sm font-medium text-gray-700 group-hover:text-purple-700">Manage Admins</span>
              <span className="text-xs text-gray-400">Admin accounts</span>
            </a>
          )}
          {(role === 'SUPER_ADMIN' || (role === 'ADMIN' && user?.perm_manage_staff)) && (
            <a
              href="/users/staff"
              className="flex flex-col items-start gap-1 p-4 rounded-xl border border-gray-200 hover:border-teal-300 hover:bg-teal-50/50 transition-colors group"
            >
              <Users size={20} className="text-teal-600" />
              <span className="text-sm font-medium text-gray-700 group-hover:text-teal-700">Manage Staff</span>
              <span className="text-xs text-gray-400">Staff accounts & puroks</span>
            </a>
          )}
          {(role === 'SUPER_ADMIN' || role === 'ADMIN') && (
            <a
              href="/puroks"
              className="flex flex-col items-start gap-1 p-4 rounded-xl border border-gray-200 hover:border-orange-300 hover:bg-orange-50/50 transition-colors group"
            >
              <MapPin size={20} className="text-orange-600" />
              <span className="text-sm font-medium text-gray-700 group-hover:text-orange-700">View Puroks</span>
              <span className="text-xs text-gray-400">Purok zones</span>
            </a>
          )}
        </CardBody>
      </Card>
    </div>
  )
}

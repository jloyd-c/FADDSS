import { useState, useEffect } from 'react'
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, Users, UserCheck, MapPin, FileText,
  LogOut, Shield, UserCircle, Building2, KeyRound, Menu, X,
} from 'lucide-react'
import useAuthStore from '../../store/authStore'

const ROLE_LABELS = {
  SUPER_ADMIN: { label: 'Super Admin', color: 'bg-red-500' },
  ADMIN:       { label: 'Admin',       color: 'bg-blue-500' },
  STAFF:       { label: 'Staff',       color: 'bg-green-500' },
  RESIDENT:    { label: 'Resident',    color: 'bg-gray-400' },
}

function NavItem({ to, icon: Icon, label, end = false, onClick }) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onClick}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all
        ${isActive
          ? 'bg-blue-600 text-white shadow-sm shadow-blue-900/30'
          : 'text-slate-400 hover:bg-white/10 hover:text-white'
        }`
      }
    >
      <Icon size={17} className="shrink-0" />
      <span className="flex-1">{label}</span>
    </NavLink>
  )
}

function NavSection({ label }) {
  return (
    <p className="px-3 pt-4 pb-1 text-xs font-semibold uppercase tracking-widest text-slate-500 select-none">
      {label}
    </p>
  )
}

function SidebarContent({ user, role, roleInfo, onNavClick, onLogout }) {
  return (
    <>
      {/* Brand */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-white/10 shrink-0">
        <div className="flex items-center justify-center w-9 h-9 bg-blue-600 rounded-lg shrink-0">
          <Shield size={18} className="text-white" />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-bold text-white leading-tight">FADDSS</p>
          <p className="text-xs text-slate-400 truncate">Barangay Portal</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-3 overflow-y-auto space-y-0.5">
        <NavSection label="Overview" />
        <NavItem to="/dashboard" icon={LayoutDashboard} label="Dashboard" end onClick={onNavClick} />

        {role === 'SUPER_ADMIN' && (
          <>
            <NavSection label="User Management" />
            <NavItem to="/users/admins" icon={Shield}  label="Admins" onClick={onNavClick} />
            <NavItem to="/users/staff"  icon={Users}   label="Staff"  onClick={onNavClick} />
          </>
        )}

        {role === 'ADMIN' && user?.perm_manage_staff && (
          <>
            <NavSection label="User Management" />
            <NavItem to="/users/staff" icon={Users} label="Staff" onClick={onNavClick} />
          </>
        )}

        {(role === 'SUPER_ADMIN' || role === 'ADMIN' || role === 'STAFF') && (
          <>
            <NavSection label="Records" />
            <NavItem to="/residents" icon={UserCheck} label="Residents" onClick={onNavClick} />
          </>
        )}

        {(role === 'SUPER_ADMIN' || role === 'ADMIN') && (
          <NavItem to="/puroks" icon={MapPin} label="Puroks" onClick={onNavClick} />
        )}

        {role === 'SUPER_ADMIN' && (
          <>
            <NavSection label="System" />
            <NavItem to="/audit" icon={FileText} label="Audit Logs" onClick={onNavClick} />
          </>
        )}

        <NavSection label="Account" />
        <NavItem to="/profile"         icon={UserCircle} label="My Profile"       onClick={onNavClick} />
        <NavItem to="/change-password" icon={KeyRound}   label="Change Password"  onClick={onNavClick} />
      </nav>

      {/* User footer */}
      <div className="px-3 py-3 border-t border-white/10 shrink-0">
        <div className="flex items-center gap-2.5 px-2 py-2 rounded-lg">
          <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center shrink-0">
            <span className="text-xs font-bold text-white">
              {(user?.first_name?.[0] || user?.email?.[0] || '?').toUpperCase()}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-white truncate">
              {user?.full_name || user?.email}
            </p>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className={`w-1.5 h-1.5 rounded-full ${roleInfo.color}`} />
              <p className="text-xs text-slate-400">{roleInfo.label}</p>
            </div>
          </div>
        </div>
        <button
          onClick={onLogout}
          className="mt-1 w-full flex items-center gap-2 px-2 py-2 rounded-lg text-xs text-slate-400
            hover:bg-red-500/10 hover:text-red-400 transition-colors"
        >
          <LogOut size={14} />
          Sign out
        </button>
      </div>
    </>
  )
}

export default function MainLayout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()
  const role = user?.role
  const roleInfo = ROLE_LABELS[role] || ROLE_LABELS.STAFF
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Close sidebar on route change (mobile)
  useEffect(() => {
    setSidebarOpen(false)
  }, [location.pathname])

  // Close on resize to desktop
  useEffect(() => {
    const onResize = () => { if (window.innerWidth >= 1024) setSidebarOpen(false) }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen bg-slate-100 overflow-hidden">

      {/* ── Mobile backdrop ────────────────────────────────────────── */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ── Sidebar ────────────────────────────────────────────────── */}
      {/* Desktop: always visible | Mobile: slide-in overlay */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-50 w-64 bg-slate-900 flex flex-col
          transition-transform duration-300 ease-in-out
          lg:relative lg:translate-x-0 lg:z-auto lg:w-60
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {/* Mobile close button */}
        <button
          onClick={() => setSidebarOpen(false)}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 lg:hidden"
        >
          <X size={18} />
        </button>

        <SidebarContent
          user={user}
          role={role}
          roleInfo={roleInfo}
          onNavClick={() => setSidebarOpen(false)}
          onLogout={handleLogout}
        />
      </aside>

      {/* ── Main content ───────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">

        {/* Top bar */}
        <header className="h-14 bg-white border-b border-slate-200 flex items-center px-4 gap-3 shrink-0">

          {/* Hamburger — hidden on desktop */}
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-700 transition-colors lg:hidden"
            aria-label="Open menu"
          >
            <Menu size={20} />
          </button>

          {/* Brand on mobile */}
          <div className="flex items-center gap-2 lg:hidden">
            <div className="w-6 h-6 bg-blue-600 rounded flex items-center justify-center">
              <Shield size={13} className="text-white" />
            </div>
            <span className="text-sm font-bold text-slate-800">FADDSS</span>
          </div>

          {/* Desktop breadcrumb */}
          <div className="hidden lg:flex items-center gap-1.5 text-sm text-slate-500">
            <Building2 size={15} className="text-blue-600" />
            <span className="text-blue-600 font-medium">Barangay Portal</span>
          </div>

          {/* Right side */}
          <div className="ml-auto flex items-center gap-2">
            {user?.must_change_password && (
              <div className="flex items-center gap-1.5 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-full px-2.5 py-1">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse shrink-0" />
                <span className="hidden sm:inline">Password change required</span>
                <span className="sm:hidden">Change password</span>
              </div>
            )}

            {/* Mobile user avatar */}
            <div className="flex items-center gap-2 lg:hidden">
              <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
                <span className="text-xs font-bold text-white">
                  {(user?.first_name?.[0] || user?.email?.[0] || '?').toUpperCase()}
                </span>
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

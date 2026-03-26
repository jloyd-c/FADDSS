import { Outlet } from 'react-router-dom'
import { Shield } from 'lucide-react'

export default function AuthLayout() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-2xl shadow-xl mb-4">
            <Shield size={32} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">FADDSS</h1>
          <p className="text-sm text-blue-300 mt-1">Barangay Records Management System</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-2xl border border-white/10 p-8">
          <Outlet />
        </div>

        <p className="text-center text-xs text-blue-400/60 mt-6">
          © {new Date().getFullYear()} Barangay Management System · Staff Access Only
        </p>
      </div>
    </div>
  )
}
